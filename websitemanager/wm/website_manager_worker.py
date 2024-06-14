
import glob, os, datetime, platform, shutil, tarfile
import wm.website_manager_utils as u
import wm.website_manager_dbutils as db
from wm.website_manager_utils import  Parameters, TimerElapsed, WebSiteData

BAN_OTHERS_RECURSIVE = "chmod -R o-rwx "
BAN_OTHERS_SINGLE = "chmod o-rwx "

def dumpwebsite(p : Parameters, d : WebSiteData):
    if d.save != 1:
        u.print_line()
        print(d.siteName, 'skipped due to column "save"')
        return
    dailydump = True
    backup(p, d, dailydump)

def get_archive_dir(params : Parameters, timestamp, altdir = 'none') -> str:
    logdir = params.get('logdir')
    u.ensure_dir(logdir)
    archiveDir = 'none'
    if u.isSnapshot(timestamp):
        if altdir != 'none':
            archiveDir = altdir
            u.is_dir_or_abort(archiveDir)
        else:
            archiveDir = params.get('snapshotdir')
            u.ensure_dir(archiveDir)
    else:
        archiveDir = params.get('sitedumpdir')
        u.ensure_dir(archiveDir)
    return archiveDir

def backup(params : Parameters, site : WebSiteData, sitedump : bool, altdir = "none"):
    """
    Arguments:
      params:     Parameters object with general settings
      data:       WebSiteData object containing the website data
      sitedump:   True - daily dump, False - timed snapshot
      altdir:     If entered, alternative target directory
    """
    timer = TimerElapsed()
    # Used Linux shell commands. Full path due to cron usage.
    scp = params.get('scp')
    mySqldump = params.get('sqldump')
    mySqldumpOptions = params.get('sqldumpoptions')
    
    # Current weekday time stamp wd0 ... wd6
    weekday = u.get_weekday()
    # year-month-day_hour-min
    time = u.get_time_tag()
    tag = time
    if sitedump:
        tag = weekday

    # Define directories:
    wwwRoot = params.get('wwwroot')                # web files' root directory
    remoteLocation = params.get('remotelocation')  # remote backup location
    wwwDir = wwwRoot + '/' + site.wwwSubdir        # website files' directory
    backupDir = get_archive_dir(params, tag, altdir) # backup archive target dir

    # Database and archive files
    sqlFile = site.siteName  + '.sql'
    dbPass = db.get_database_pw(site)
    zipArchive = site.siteName + '.' + tag + '.tar.gz'
    zipPath = backupDir + '/' + zipArchive

    # will a longterm backup be created?
    longtermZipArchive = 'none'
    useRemoteLocation = 'none'
    if sitedump:
        longtermZipArchive = get_longterm_archive(zipPath, site.siteName)
        useRemoteLocation = remoteLocation
    u.print_line()
    print('Script started:       ', u.get_current_time())
    print('Time tag:             ', tag)
    print('Save website:         ', site.siteName)
    print('Webpage directory:    ', wwwDir)
    print('Included database:    ', site.dbName)
    print('Backup directory:     ', backupDir)
    print('Gzip archive written: ', zipArchive)
    print('Remote backup path:   ', useRemoteLocation)
    print('Longterm archive:     ', longtermZipArchive)

    # Create the MySQL dump.
    # A global transaction identifier (GTID) is not necessary.
    temp = 'temp932524687'
    tempDir = backupDir + '/' + temp
    u.make_empty_dir(tempDir)
    sqlFilePath = tempDir + '/' + sqlFile
    sqlDumpCommand = (mySqldump + dbPass + ' -u' + site.dbUser + ' '
                      + mySqldumpOptions + ' ' + site.dbName + ' > ' + sqlFilePath)
    # Note: On Linux start a new shell to be able to redirect as root user!
    # sh -c "command > file"
    if platform.system() != 'Windows':
        sqlDumpCommand = ('sh -c "' + sqlDumpCommand + '"')
    u.RUNNER.do(sqlDumpCommand)
    if not os.path.exists(sqlFilePath):
        u.abort(sqlFilePath + ' does not exist')
    timer.show_elapsed('SQL dump time elapsed')

    # rename archive as longterm archive if applicable
    if longtermZipArchive != 'none':
        longtermArchivePath = backupDir + '/' + longtermZipArchive
        print('Replacing:', zipPath, longtermArchivePath)
        os.replace(zipPath, longtermArchivePath)

    # Open gz archive to be written, add webfiles and add SQL dump.
    with tarfile.open(zipPath, "w:gz", compresslevel=5) as tar:
        tar.add(wwwDir, arcname="www")
        tar.add(tempDir, arcname="database")
    timer.show_elapsed('Tarfile time elapsed')
    u.delete_dir(tempDir)

    if os.path.exists(zipPath):
        if params.get('wwwbanothers') == 'true':
           u.RUNNER.do(BAN_OTHERS_SINGLE + zipPath)
        print('Gzip archive written: ', zipPath)
        # no log on bulk backup
        if not sitedump:
            logFile = params.get('logdir') + '/' + site.siteName + '.txt'
            u.append_logfile(logFile, tag + ' saved: ')
    else:
        u.abort('Gzip archive missing: ', zipPath)

    if useRemoteLocation != 'none':
        remote_upload(zipArchive, longtermZipArchive, backupDir, scp, useRemoteLocation)

    timer.show_total_elapsed('Backup time elapsed')
    print('Finished:             ', u.get_current_time())

# Will a long-term backup archive be saved? If yes, the oldest
# daily archive will be renamed instead of overwritten. Each month
# the following will be saved: At the 8th, the archive of the 1st
# is renamed as monthly backup. At the 15th and the 23rd, the archives
# of the 8th and the 16th are saved as (roughly) weekly backups.
# At the 1st, the archive between the 22th and the 25th of the previous
# month is saved as a further (roughly) weekly backup. The exact date 
# depends on the number of days of the previous month.
# There will be at most 12 monthly backups and 3 'weekly' backups.
# The oldest of these archives will be cyclically overwritten.
def get_longterm_archive(zipPath, siteName) -> str:
    # Is there already an 8 days old archive?
    if not os.path.exists(zipPath):
        return 'none'
    d = datetime.datetime.now()
    monthTag = 'm' + d.strftime("%m")
    day = d.strftime("%d")
    switcher = {
        '08': monthTag,
        '15': 'w1',
        '23': 'w2',
        '01': 'w3',
    }
    newTag = switcher.get(day, 'none')
    if newTag != 'none':
        return siteName + '.' + newTag + '.tar.gz'
    return 'none'

# Save to remote host if configured.
# SSL key must be present. For Hetzner see
# https://docs.hetzner.com/de/robot/storage-box/backup-space-ssh-keys/
def remote_upload(zipArchive, longtermZipArchive, backupDir, scp, remoteLocation):
    print('Upload:               ', zipArchive)
    print('Upload started:       ', u.get_current_time())
    zipPath = backupDir + '/' + zipArchive
    scpCommand = (scp + ' -p ' + zipPath + ' ' 
                  + remoteLocation + '/' + zipArchive)
    u.RUNNER.do(scpCommand)
    if longtermZipArchive == 'none':
      return
    print('Upload:               ', longtermZipArchive)
    print('Upload started:       ', u.get_current_time())
    scpCommand = (scp + ' -p ' + backupDir + '/' + longtermZipArchive
                  + ' ' + remoteLocation + '/' + longtermZipArchive)
    u.RUNNER.do(scpCommand)
    return

# Check whether database and user exist and, if not, add them.
def prepare_database(params : Parameters, site : WebSiteData):
    """
    Arguments:
      params:     Parameters object with general settings
      data:       WebSiteData object containing the website data
    """
    u.print_line()
    print('Treated webpage:', site.siteName)
    print('Associated web directory:', params.get('wwwroot') + '/' + site.wwwSubdir)
    print('Checked database:', site.dbName)
    print('Database user:', site.dbUser)
    u.print_line()
    print('Check whether database already exists...')
    db.ensure_database_exists(params, site)

def get_archive_timestamp(params : Parameters, site : WebSiteData, altdir = 'none') -> str:
    """
    Show available backup archives. Query the timestamp of the archive to be restored.
    Arguments:
      params:    Parameters object with general settings
      site:      WebSiteData object containing the website data
      altdir:    If entered, alternative snapshot archive directory
    """
    # "root_dir=DIRECTORY_PATH" is not yet in glob with Python 3.8:
    cwd = os.getcwd()
    dumpDir = params.get('sitedumpdir') 
    os.chdir(dumpDir)
    sitedumps = glob.glob(site.siteName + '*tar.gz')
    datedDumps = u.get_dated_files(sitedumps)
    u.print_timestamps(datedDumps, site.siteName, 'Sitedumps in ' + dumpDir + ' :')

    snapshotDir = params.get('snapshotdir') 
    if altdir != 'none':
        snapshotDir = altdir
    os.chdir(snapshotDir)
    snapshots = glob.glob(site.siteName + '*tar.gz')
    os.chdir(cwd)
    u.print_timestamps(snapshots, site.siteName, 'Snapshots in ' + snapshotDir + ' :')
    
    print('Snapshot timestamps have format YYYY-MM-DD_hh-mm')
    print('Sitedump labels have format wd#, w# or m# where # is integer')
    print('Only enter the label without date and parens for a sitedump!')
    timestamp = input('Enter timestamp or label of "' + site.siteName 
                      + '" archive to be restored: ')
    if timestamp == '' or ' ' in timestamp or timestamp.isspace():
        print('Timestamp may not contain whitespace.')
        u.abort('invalid timestamp entered')
    print('Try restoring from archive', site.siteName + '.' + timestamp + '.tar.gz')
    return timestamp

def restore(params : Parameters, site : WebSiteData, timestamp, backupDir):
    """
    Arguments:
      params:     Parameters object with general settings
      site:       WebSiteData object containing the website data
      timestamp:  timestamp of the archive to be restored
      backupDir:  backup archive directory
    """
    # Used Linux shell commands.
    sql = params.get('sql')
    wwwUserGroup  = params.get('wwwusergroup') # 'none': do nothing
    # otherwise: change owner and expect user and group e.g. www-data:www-data"
    wwwbanothers = params.get('wwwbanothers') == 'true'
    
    # Set up the archive name and global root directories
    archive = backupDir + '/' + site.siteName + '.' + timestamp + '.tar.gz'
    wwwPath = params.get('wwwroot') + '/' + site.wwwSubdir
    u.print_line()
    print('Restored webpage:', site.siteName)
    print('Restored web directory:', wwwPath)
    print('Restored database:', site.dbName)
    print('Database user:', site.dbUser)
    
    # Look after backup archive
    print('Entered archive timestamp:', timestamp)
    print('Webpage to be restored from:', archive)
    u.print_line()
    if os.path.exists(archive):
        print('Archive file found...')
    else:
        u.abort('Error abort due to missing archive file...')

    # Setup an empty temp directory
    temp = 'temp932524687'
    tempDir = backupDir + '/' + temp
    u.make_empty_dir(tempDir)

    # Extract the files in the archive into the $Temp directory
    with tarfile.open(archive, 'r:gz') as tar:
        tar.extractall(path=tempDir)

    # Look for the www directory
    tempWwwPath = tempDir + '/www'
    print('Webfiles location:      ', tempWwwPath)
    u.is_dir_or_abort(tempWwwPath)

    # Search DbFile, the SQL dump file within the extracted files.
    tempDatabasePath = tempDir + '/database'
    print('Database dump location: ', tempDatabasePath)
    u.is_dir_or_abort(tempDatabasePath)
    workingDir = os.getcwd()
    os.chdir(tempDatabasePath)
    # SQL file has to begin with siteName and end with ".sql".
    sqlfiles = glob.glob('*.sql')
    numSqls = len(sqlfiles)
    if numSqls != 1:
        u.abort('Error abort due to unexpected (numSqls != 1) number of SQL files...')
    dbFile = tempDatabasePath + '/' + sqlfiles[0]
    print('Restoring database from:', dbFile)
    u.is_file_or_abort(dbFile)
    
    print('Check whether database already exists...')
    db.ensure_database_exists(params, site)
    
    sql1 = sql + ' -u ' + site.dbUser
    sql2 = site.dbName + ' < ' + dbFile

    # should database be restored
    print('Execute:')
    print(sql1 + ' -pXXXXX ' + sql2)
    restorecommand = (sql1 + db.get_database_pw(site) + ' ' + sql2)
    print('Overwriting database', site.dbName)
    u.query_continue()
    
    # now restore database
    exitcode = u.RUNNER.do(restorecommand)
    if exitcode == 0:
        print('...database', site.dbName, 'restored')
    else:
        u.abort('...database', site.dbName, 'restoration failed')
    # leave SQL directory to be able to clean up the temp directory
    os.chdir(workingDir)
    
    # should all webfiles be restored?
    print('Finally webdir', wwwPath, 'has to be restored!')
    print('The following is carried out:')
    print('Webdir replaced:', wwwPath)
    print('By this:', tempWwwPath)
    chowncommand = 'chown -R ' + wwwUserGroup + ' ' + wwwPath
    banotherscommand = BAN_OTHERS_RECURSIVE + wwwPath
    if wwwUserGroup != 'none':
        print(chowncommand)
        if wwwbanothers:
            print(banotherscommand)
    u.query_continue()
    
    # restore all webfiles
    u.delete_dir(wwwPath)
    shutil.move(tempWwwPath, wwwPath)
    if wwwUserGroup != 'none':
        u.RUNNER.do(chowncommand)
        if wwwbanothers:
            u.RUNNER.do(banotherscommand)
    # Remove temp directory
    u.delete_dir(tempDir)

    logFile = params.get('logdir') + '/' + site.siteName + '.txt'
    msg = timestamp + ' restored: '
    if not u.isSnapshot(timestamp):
        date = u.get_date_of_file(archive)
        msg = date + '(' + timestamp + ') restored: '
    u.append_logfile(logFile, msg)        

    print('...', site.siteName, 'restore', timestamp, 'complete.')

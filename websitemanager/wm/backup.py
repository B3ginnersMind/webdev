import os, datetime, platform, tarfile
import wm.utils as u
import wm.dbutils as db
import wm.timeutils as t
from wm.websites import WebSiteData
from wm.config import Parameters

BAN_OTHERS_RECURSIVE = "chmod -R o-rwx "
BAN_OTHERS_SINGLE = "chmod o-rwx "

def get_archive_dir(params : Parameters, timestamp: str, altdir: str = 'none') -> str:
    logdir = params.get('logdir')
    u.ensure_dir(logdir)
    archiveDir = 'none'
    if t.isSnapshot(timestamp):
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

def dumpwebsite(p : Parameters, d : WebSiteData):
    if d.save != "1":
        u.print_line()
        print(d.siteName, 'skipped due to column "save"')
        return
    dailydump = True
    backup(p, d, dailydump)

def backup(params : Parameters, site : WebSiteData, sitedump : bool, altdir: str = "none"):
    """
    Arguments:
      params:     Parameters object with general settings
      data:       WebSiteData object containing the website data
      sitedump:   True - daily dump, False - timed snapshot
      altdir:     If entered, alternative target directory
    """
    timer = t.TimerElapsed()
    # Used Linux shell commands. Full path due to cron usage.
    scp = params.get('scp')
    mySqldump = params.get('sqldump')
    mySqldumpOptions = params.get('sqldumpoptions')
    
    # Current weekday time stamp wd0 ... wd6
    weekday = t.get_weekday()
    # year-month-day_hour-min
    time = t.get_time_tag()
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
    print('Script started:       ', t.get_current_time())
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
    sqlDumpCommand = (mySqldump + ' -h ' + site.host + dbPass + ' -u' + site.dbUser + ' '
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
    print('Finished:             ', t.get_current_time())

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
def get_longterm_archive(zipPath: str, siteName: str) -> str:
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
def remote_upload(zipArchive: str, 
                  longtermZipArchive: str, 
                  backupDir: str, 
                  scp: str, 
                  remoteLocation: str):
    print('Upload:               ', zipArchive)
    print('Upload started:       ', t.get_current_time())
    zipPath = backupDir + '/' + zipArchive
    scpCommand = (scp + ' -p ' + zipPath + ' ' 
                  + remoteLocation + '/' + zipArchive)
    u.RUNNER.do(scpCommand)
    if longtermZipArchive == 'none':
      return
    print('Upload:               ', longtermZipArchive)
    print('Upload started:       ', t.get_current_time())
    scpCommand = (scp + ' -p ' + backupDir + '/' + longtermZipArchive
                  + ' ' + remoteLocation + '/' + longtermZipArchive)
    u.RUNNER.do(scpCommand)
    return

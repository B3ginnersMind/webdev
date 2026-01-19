
import readline # type: ignore for input() history support on Unix
import glob, os, shutil, tarfile, textwrap
import wm.utils as u
import wm.dbutils as db
from wm.websites import WebSiteData
from wm.config import Parameters
from wm.timeutils import get_dated_files, get_date_of_file, isSnapshot, print_timestamps

BAN_OTHERS_RECURSIVE = "chmod -R o-rwx "
BAN_OTHERS_SINGLE = "chmod o-rwx "

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
    if site.dbName == 'none' or site.dbUser == 'none':
        print('No database or database user to be prepared.')
        return
    print('Check whether database already exists...')
    db.ensure_database_exists(params, site)

def get_archive_timestamp(params : Parameters, site : WebSiteData, altdir: str = 'none') -> str:
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
    datedDumps = get_dated_files(sitedumps)
    print_timestamps(datedDumps, site.siteName, 'Sitedumps in ' + dumpDir + ' :')

    snapshotDir = params.get('snapshotdir') 
    if altdir != 'none':
        snapshotDir = altdir
    os.chdir(snapshotDir)
    snapshots = glob.glob(site.siteName + '*tar.gz')
    os.chdir(cwd)
    print_timestamps(snapshots, site.siteName, 'Snapshots in ' + snapshotDir + ' :')
    
    print('Snapshot timestamps have format YYYY-MM-DD_hh-mm or YYYY-MM-DD')
    print('Sitedump labels have format wd#, w# or m# where # is integer')
    print('Only enter the label without date and parens for a sitedump!')
    timestamp = input('Enter timestamp or label of "' + site.siteName 
                      + '" archive to be restored: ')
    if timestamp == '' or ' ' in timestamp or timestamp.isspace():
        print('Timestamp may not contain whitespace.')
        u.abort('invalid timestamp entered')
    print('Try restoring from archive', site.siteName + '.' + timestamp + '.tar.gz')
    return timestamp

def restore(params : Parameters, site : WebSiteData, timestamp: str, backupDir: str):
    """
    Arguments:
      params:     Parameters object with general settings
      site:       WebSiteData object containing the website data
      timestamp:  timestamp of the archive to be restored
      backupDir:  backup archive directory
    """
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

    # If database is not 'none', restore it
    restore_database(params, site, tempDir)
    
    # should all webfiles be restored?
    print('Webdir', wwwPath, 'has to be restored!')
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
    if not isSnapshot(timestamp):
        date = get_date_of_file(archive)
        msg = date + '(' + timestamp + ') restored: '
    u.append_logfile(logFile, msg)        

    print('...', site.siteName, 'restore', timestamp, 'complete.')


def restore_database(params : Parameters, site : WebSiteData, tempDir: str):
    if site.dbName == 'none':
        print('.... no database to be restored.')
        return
    # Used SQL command.
    sql = params.get('sql')
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
    
    if params.get('runasroot') == 'true':
        db.ensure_database_exists(params, site)

    # should database be restored?
    defaults_file, db_credential = db.get_db_defaults_file(params, site)
    print('Execute:')
    restorecommand = (sql + db_credential + ' -h ' + site.host 
                      + ' ' + site.dbName + ' < ' + dbFile)
    wrappedCmd = textwrap.fill(restorecommand, u.WRAP_LENGTH)
    u.print_line('-')
    print(wrappedCmd)
    u.print_line('-')
    print('Overwriting database', site.dbName)
    u.query_continue()

    # now restore database
    exitcode = u.RUNNER.do(restorecommand)
    os.remove(defaults_file)
    if exitcode == 0:
        print('...database', site.dbName, 'restored')
    else:
        u.abort('...database', site.dbName, 'restoration failed')
    # leave SQL directory to be able to clean up the temp directory
    os.chdir(workingDir)


import os, random, string, stat, subprocess
from wm.utils import abort, check_root_user, RUNNER
from wm.websites import WebSiteData
from wm.config import Parameters

def get_db_defaults_file(params : Parameters, site : WebSiteData) -> tuple[str, str]:
    """
    Create a temporary defaults file for mysql client with user and password.
    Returns the path to the defaults file and the database credential string
    to be used in mysql commands.
    """
    snapshotdir = params.get('snapshotdir')
    char_pool: str = string.ascii_letters + string.digits
    defaults_file = "/."
    for _ in range(15):
        defaults_file += random.choice(char_pool)
    defaults_file = snapshotdir + defaults_file
    lines: list[str] = []
    lines.append('[client]\n')
    lines.append('user=' + site.dbUser + '\n')
    lines.append('password=' + site.dbPassWord + '\n')
    with open(defaults_file, 'w') as df:
        df.writelines(lines)
    # Set file permission to read and write for user only
    os.chmod(defaults_file, stat.S_IRUSR | stat.S_IWUSR)
    db_credential: str = " --defaults-file=" + defaults_file
    return defaults_file, db_credential

# get the mysql main user password
def get_mysql_pw(params : Parameters):
    dbPass = ''
    if params.get('sqlmainpw') != 'none':
        dbPass = ' --defaults-file=' + params.get('sqlmainpw')
    return dbPass

# create the opening string to execute mysql commands with option -e
def get_mysql_open_string(params : Parameters):
    # mysql --defaults-file=MYFILE -uroot -s -N
    # --silent, -s: silent mode
    # --skip-column-names, -N: do not write column names in results 
    return (params.get('sql') + get_mysql_pw(params)
            + ' -u' + params.get('sqlmainuser') + ' -s -N ')

# Does the database exist and is accessible by the database user?
def database_exists(params : Parameters, site : WebSiteData):
    # Test the return code of the following command:
    # mysql --defaults-file=FILE --silent -e "quit" DATABASENAME
    defaults_file, db_cred  = get_db_defaults_file(params, site)
    testcommand = (params.get('sql') 
                   + db_cred
                   + ' --silent -e "quit" ' + site.dbName)
    print('Check whether database already exists and is accessible...')
    # To silence output add: stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    result = subprocess.run(testcommand, shell=True, stderr=subprocess.DEVNULL)
    exitcode = result.returncode
    os.remove(defaults_file)    
    if exitcode != 0:
        return False
    return True


# Does the database user exist?
def dbuser_exists(params : Parameters, site : WebSiteData):
    # mysql --defaults-file=/Backup/script/.mysqlpw -uroot
    #       -s -N -e "SELECT COUNT(*) FROM mysql.user WHERE user='testuser';"
    command = (get_mysql_open_string(params)
              + '-e "' 
              + 'SELECT COUNT(*) FROM mysql.user WHERE '
              + 'user=\'' + site.dbUser +  '\''
              + '"'
              )
    output = subprocess.run(command, shell=True, capture_output=True)
    if output.returncode != 0: 
        abort('command', command, 'failed')
    result = output.stdout.decode("utf-8")
    if result[0] == '1':
        print('User', site.dbUser, 'exists')
        return True
    print('User', site.dbUser, 'missing')
    return False

def add_dbuser(params : Parameters, site : WebSiteData):
    # create user testuser@localhost identified by 'TESTPASSWD';
    # alter user testuser@localhost identified with mysql_native_password;
    # alter user testuser@localhost identified by 'TESTPASSWD';
    # After setting mysql_native_password reset password since it may habe been deleted.
    # Note: A CMS might not be compatibel with caching_sha2_password.
    command = (get_mysql_open_string(params)
              + '-e "' 
              + 'create user ' + site.dbUser + '@localhost '
              + "identified by '" + site.dbPassWord + "';"
              + 'alter user '+ site.dbUser 
              +'@localhost identified with mysql_native_password;'
              + 'alter user '+ site.dbUser 
              + "@localhost identified by '" + site.dbPassWord + "';"
              + '"'
              )
    print('Add user', site.dbUser)
    RUNNER.do(command)

# Create database if it does not yet exist. Abort if no success.
def ensure_database_exists(params : Parameters, site : WebSiteData):
    if database_exists(params, site) == True:
        print('Database', site.dbName, 'already existing and accessible')
        return

    print('Database', site.dbName, 'not accessible by user', site.dbUser)
    check_root_user()
    # Guarantee that the database user exists and, if not, abort
    if dbuser_exists(params, site) != True:
        add_dbuser(params, site)
    # Now add the database
    # mysql --defaults-file=FILE -uMAINUSER
    # > create database DBNAME;
    # > grant all privileges on DBNAME.* to DBUSER@localhost;
    # > flush privileges;
    print('Creating database', site.dbName, '...')
    command = (get_mysql_open_string(params)
              + '-e "'
              + 'create database ' + site.dbName + ';'
              + 'grant all privileges on ' + site.dbName + '.* '
              + 'to ' + site.dbUser + '@localhost;'
              + 'flush privileges;"'
              )
    RUNNER.do(command)

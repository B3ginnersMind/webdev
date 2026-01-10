
import datetime, os, platform, shutil, stat, sys, textwrap
from enum import Enum
from pathlib import Path, WindowsPath

LINE_LENGTH = 70
WRAP_LENGTH = LINE_LENGTH - 2
RUNNER_OPTIONS = []                        # for production
#RUNNER_OPTIONS = ['verbose']              # only verbose
#RUNNER_OPTIONS = ['verbose', 'simulate']  # only print commands for debugging

class OsCommandRunner:
    def __init__(self, options = []):
      self.options = options
    def do(self, cmd):
        if 'verbose' in self.options:
            print_line('-')
            print(textwrap.fill(cmd, WRAP_LENGTH))
            print_line('-')
        if 'simulate' not in self.options:
            exitcode = os.system(cmd)
            if (exitcode != 0):
                abort('ERROR in command:', cmd)
            return exitcode
        return 0
RUNNER = OsCommandRunner(RUNNER_OPTIONS)

class Operation(Enum):
    UNKNOWN = 0
    BATCH_SAVEALL = -1
    SAVEALL = 1
    SNAPSHOT = 2
    REPLACE_AFTER_SNAPSHOT = 3
    REPLACE = 4
    DBEXIST = 5
    @staticmethod
    def min():
        return 1
    @staticmethod
    def max():
        return 5
    def isSaveall(self):
        return (self == Operation.BATCH_SAVEALL or self == Operation.SAVEALL)
    def isSnapshot(self):
        return (self == Operation.SNAPSHOT or self == Operation.REPLACE_AFTER_SNAPSHOT)
    def isReplace(self):
        return (self == Operation.REPLACE or self == Operation.REPLACE_AFTER_SNAPSHOT)

def abort(*msg):
    messageLine = '...'
    for m in msg: 
        messageLine += ' ' + m
    print(textwrap.fill(messageLine, WRAP_LENGTH))
    print('... aborting')
    if 'simulate' not in RUNNER_OPTIONS:
        sys.exit(1)

def check_root_user():
    if platform.system() != 'Windows' and os.getuid() != 0:
        abort('Please run as root.')

def query_continue():
    ch = input('Enter q to abort or other key to continue: ')
    if ch == 'q':
        quit()

def query_int(msg, min, max):
    try:
        num = int(input(msg + ': '))
        if num < min or num > max:
            abort('number out of range [' + str(min) + ',' + str(max) + ']')
    except ValueError:
        abort('not a number')
    return num

def print_line(char = '='):
    print(LINE_LENGTH * char)

def ensure_dir(dir):
    if os.path.isdir(dir):
        return
    if 'simulate' not in RUNNER_OPTIONS:
        os.makedirs(dir, 0o700)

def remove_readonly(func, path, _):
    """Remove write protection and continue delete process."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def delete_dir(dir, usePython=True):
    p = Path(dir)
    if p.is_file():
        abort('delete_dir:', dir, 'is a file instead of a directory')
    if not p.is_dir():
        return
    print('Removing', dir, 'directory...')
    # in Python 3.12 onexc added und onerror deprecated, may be removed in 3.14
    if usePython == True:
        shutil.rmtree(p, onerror=remove_readonly)
    elif platform.system() == 'Windows':
        RUNNER.do('rd /s /q ' + str(WindowsPath(dir)))
    else:
        RUNNER.do('rm -R ' + dir)

def make_empty_dir(dir):
    delete_dir(dir)
    if 'simulate' not in RUNNER_OPTIONS:
        os.makedirs(dir, 0o755)

def is_dir_or_abort(dir):
    if not os.path.isdir(dir):
        abort('Directory missing  ' + dir)

def is_file_or_abort(path):
    if not os.path.isfile(path):
        abort('File missing  ' + path)

def delete_file(file):
    if os.path.isfile(file):
        os.remove(file)

def get_weekday() -> str:
    d = datetime.datetime.now()
    return 'wd' + d.strftime("%w")

def get_time_tag() -> str:
    currently = datetime.datetime.now()
    return currently.strftime('%Y-%m-%d_%H-%M')

def get_date_tag() -> str:
    currently = datetime.datetime.now()
    return currently.strftime('%Y-%m-%d')

def get_current_time() -> str:
    currently = datetime.datetime.now()
    return currently.strftime('%d.%m.%Y %H:%M')

def get_date_of_file(file : str) -> str:
    ts = os.path.getmtime(file)
    t = datetime.datetime.fromtimestamp(ts)
    return t.strftime('%Y.%m.%d')

def get_dated_files(files : list) -> list:
    datedFiles = []
    for f in files:
        ts = os.path.getmtime(f)
        t = datetime.datetime.fromtimestamp(ts)
        date = t.strftime('%Y.%m.%d')
        datedFiles.append(date +'(' + f + ')')
    return datedFiles

def isSnapshot(timestamp) -> bool:
    """"
    Test whether timestamp is from snapshot or cron (saveAll) backup.
    "Cron" daily, weekly, monthly staggered backups won't contain '_' or '-'.
    """
    return ('_' in timestamp or '-' in timestamp)

def print_timestamps(archives : list, sitename : str, msg : str):
    line = []
    for a in archives:
        a = a.replace(sitename +'.', '')
        a = a.replace('.tar.gz', '')
        line.append(a)
    line.sort()
    print(msg + '\n', textwrap.fill('   '.join(line), WRAP_LENGTH), '\n')

def append_logfile(logFile, tag):
    print('action:', tag)
    comment = input('Add comment to action for logfile:  ')
    with open(logFile, 'a') as f:
        f.write(tag + comment + '\n')
    print('Comment added in:     ', logFile)

class TimerElapsed:
  def __init__(self):
    self.starttime = datetime.datetime.now()
    self.interimtime = self.starttime
  def show_elapsed(self, comment):
    now = datetime.datetime.now()
    # diff: timedelta Object
    diff = now - self.interimtime
    self.interimtime = now
    print('=> ' + comment + ' = ' + str(diff.total_seconds()) + ' sec')
  def show_total_elapsed(self, comment):
    #self.newtime = datetime.datetime.now()
    now = datetime.datetime.now()
    # diff: timedelta Object
    diff = now - self.starttime
    self.starttime = now
    print('=> ' + comment + ' = ' + str(diff.total_seconds()) + ' sec')

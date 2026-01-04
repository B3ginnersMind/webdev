
import csv, configparser, datetime, os, platform, shutil, stat, sys, textwrap
from enum import Enum
from dataclasses import dataclass, fields
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

class Parameters:
    def __init__(self, config_file: str):
        self.section = "wm_config"
        print('Reading:', config_file)
        print('Section:', self.section)
        self.config_file = config_file
        if not os.path.exists(config_file):
            abort('parameter table file "' + config_file + '"is missing')  
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.params = ['runasroot', 'scp', 'sql', 'sqldump', 'sqldumpoptions', 
                       'sqlmainuser', 'sqlmainpw', 'sitedumpdir', 'snapshotdir', 
                       'logdir', 'wwwroot', 'wwwusergroup', 'wwwbanothers', 
                       'remotelocation']
        self.checkParams()
    def show(self):
        print_line()
        print('content of parameter table "' + self.config_file + '":')
        maxParamLength = 0
        for p in self.params:
            maxParamLength = max(maxParamLength, len(p))
        indent = (maxParamLength + 3) * ' '
        for p in self.params:
            v = self.config.get(self.section, p)
            line = p.ljust(maxParamLength) + ' = ' + "'" + v + "'"
            wrappedLine = textwrap.fill(line, WRAP_LENGTH, subsequent_indent=indent)
            print(wrappedLine)
        print_line()
    def checkParams(self):
        missingParams = ''
        for p in self.params:
            if not self.config.has_option(self.section, p):
                missingParams += ' ' + p
        if missingParams != '':
           abort('missing parameters in "' + self.config_file 
                 + '": ' + missingParams)
    def get(self, param):
        if not self.config.has_option(self.section, param):
            abort('===> param', param, 'missing in index')
        return self.config.get(self.section, param)

@dataclass
class WebSiteData:
    siteName : str = "none"
    save : int = 0
    wwwSubdir : str = "none"
    dbName : str = "none"
    dbUser : str = "none"
    dbPassWord : str = "none"
    comment : str = "none"

    @classmethod
    def field_names(cls) -> list[str]:
        """Returns all attribute names as a string list."""
        return [f.name for f in fields(cls)]
    @classmethod
    def field_widths(cls) -> list[int]:
        """Returns length of all attribute names as an  list of ints."""
        return [len(f.name) for f in fields(cls)]
    def show(self):
        print("------- WebSiteData contents ---------")
        for name, value in self.__dict__.items():
            print(f"{name}: {value}")
        print("--------------------------------------")

class WebSiteTable:
    def __init__(self, tablePath):
        print('Reading:', tablePath)
        self.columns = WebSiteData.field_names()
        self.col2index = {c: i for i, c in enumerate(self.columns)}
        self.widths = WebSiteData.field_widths()
        # header line does not count as website
        self.numWebsites = -1
        self.header: list[str] = []
        self.site2index = {}
        self.table: list[list[str]] = []
        try:
            # module csv handles newline itself!
            with open(tablePath, 'r', encoding='utf-8', newline='') as csv_datei:
                print(f"Datei '{tablePath}' erfolgreich geöffnet.")
                reader = csv.reader(csv_datei, delimiter=' ')
                for line in reader:
                    # remove empty columns due to muliple blanks
                    line = list(filter(('').__ne__, line))
                    # skip empty and comment lines
                    if len(line) > 0 and line[0][0] != "#":
                        self.numWebsites += 1
                        if self.numWebsites >= 1:
                            if len(line) < len(self.columns):
                                abort("too few columns in line:", str(line))
                            self.table.append(line)
                            self.site2index[line[0]] = self.numWebsites - 1
                            print("line", line)
                        else:
                            self.header = line
                            self.checkheader()
                            print("\nheader", self.header, "\n")
        except FileNotFoundError:
            abort(f"FEHLER: Die Datei '{tablePath}' wurde nicht gefunden.")
        if self.numWebsites < 1:
            abort("no website data in table:", tablePath)
        for j in range(len(self.columns)):
            for i in range(self.numWebsites):
                self.widths[j] = max(self.widths[j], len(self.table[i][j]))
        print("site2index", self.site2index, "\n")
        print("table", self.table, "\n")
        print("param2index", self.col2index, "\n")
        self.test()
    def checkheader(self):
        if self.header != self.columns:
            abort("header columns do not match expected columns.")
    def test(self):
        sites = []
        for i in range(self.numWebsites):
            site = self.table[i][self.col2index['siteName']]
            if site in sites:
                abort("duplicate siteName in table:", site)
            sites.append(site)
    def showall(self):
        skipped = []
        self.show(skipped)
    def show(self, skippedCols = ['dbUser', 'dbPassWord']):
        print_line()
        headline = "    "
        skippedColIndices = [self.col2index[c] for c in skippedCols]
        for j in range(len(self.columns)):
            if j not in skippedColIndices:
                headline += self.columns[j].ljust(self.widths[j]) + "  "
        print(headline)
        for i in range(self.numWebsites):
            line = f"{i:2d}  "
            for j in range(len(self.columns)):
                if j not in skippedColIndices:
                    value = self.table[i][j]
                    line += value.ljust(self.widths[j]) + "  "
            print(line)
        print_line()

    def getNumWebsites(self):
        return self.numWebsites
    def hasSite(self, siteName):
        return siteName in self.site2index
    def getSite(self, siteName):
        return self.getData(self.site2index[siteName])
    def getData(self, row):
        data = {col: self.table[row][self.col2index[col]] for col in self.columns}
        # ** means: take each key-value pair as a named parameter.
        return WebSiteData(**data)


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

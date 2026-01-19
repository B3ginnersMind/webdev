
import datetime, os, textwrap
from wm.utils import WRAP_LENGTH

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

def get_date_of_file(file: str) -> str:
    ts = os.path.getmtime(file)
    t = datetime.datetime.fromtimestamp(ts)
    return t.strftime('%Y.%m.%d')

def get_dated_files(files: list[str]) -> list[str]:
    datedFiles: list[str] = []
    for f in files:
        ts = os.path.getmtime(f)
        t = datetime.datetime.fromtimestamp(ts)
        date = t.strftime('%Y.%m.%d')
        datedFiles.append(date +'(' + f + ')')
    return datedFiles

def isSnapshot(timestamp: str) -> bool:
    """"
    Test whether timestamp is from snapshot or cron (saveAll) backup.
    "Cron" daily, weekly, monthly staggered backups won't contain '_' or '-'.
    """
    return ('_' in timestamp or '-' in timestamp)

def print_timestamps(archives : list[str], sitename : str, msg : str):
    line: list[str] = []
    for a in archives:
        a = a.replace(sitename +'.', '')
        a = a.replace('.tar.gz', '')
        line.append(a)
    line.sort()
    print(msg + '\n', textwrap.fill('   '.join(line), WRAP_LENGTH), '\n')

class TimerElapsed:
  def __init__(self):
    self.starttime = datetime.datetime.now()
    self.interimtime = self.starttime
  def show_elapsed(self, comment: str):
    now = datetime.datetime.now()
    # diff: timedelta Object
    diff = now - self.interimtime
    self.interimtime = now
    print('=> ' + comment + ' = ' + str(diff.total_seconds()) + ' sec')
  def show_total_elapsed(self, comment: str):
    #self.newtime = datetime.datetime.now()
    now = datetime.datetime.now()
    # diff: timedelta Object
    diff = now - self.starttime
    self.starttime = now
    print('=> ' + comment + ' = ' + str(diff.total_seconds()) + ' sec')

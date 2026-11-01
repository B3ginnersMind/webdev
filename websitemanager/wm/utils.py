import os, platform, shutil, stat, sys, textwrap
from enum import Enum
from pathlib import Path
from collections.abc import Callable
from typing import Any, NoReturn
from types import TracebackType

LINE_LENGTH = 80
WRAP_LENGTH = LINE_LENGTH - 2
RUNNER_OPTIONS: list[str] = []                        # for production
#RUNNER_OPTIONS: list[str]= ['verbose']               # only verbose
#RUNNER_OPTIONS: list[str] = ['verbose', 'simulate']  # only print commands for debugging

class OsCommandRunner:
    def __init__(self, options: list[str] = []):
      self.options = options
    def do(self, cmd: str):
        if 'verbose' in self.options:
            print_line('-')
            print(textwrap.fill(cmd, WRAP_LENGTH))
            print_line('-')
        if 'simulate' not in self.options:
            exitcode = os.system(cmd)      # pyright: ignore[reportDeprecated]
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

def abort(*msg: str) -> NoReturn:
    messageLine = '...'
    for m in msg: 
        messageLine += ' ' + m
    print(textwrap.fill(messageLine, WRAP_LENGTH))
    print('... aborting')
    sys.exit(1)

def check_root_user():
    if platform.system() != 'Windows' and os.getuid() != 0: # type: ignore
        abort('Please run as root.')

def query_continue():
    ch = input('Enter q to abort or other key to continue: ')
    if ch == 'q':
        quit()

def query_int(msg: str, min: int, max: int) -> int:
    num = -1
    try:
        val = input(msg + ' or q to abort: ')
        if val == 'q':
            quit()
        num = int(val)
        if num < min or num > max:
            abort('number out of range [' + str(min) + ',' + str(max) + ']')
    except ValueError:
        abort('not a number')
    except KeyboardInterrupt:    
        abort('interrupted by user')
    return num

def print_line(char: str = '='):
    print(LINE_LENGTH * char)

def ensure_dir(dir: str) -> None:
    if os.path.isdir(dir):
        return
    if 'simulate' not in RUNNER_OPTIONS:
        os.makedirs(dir, 0o700)

def _make_writable_and_retry(func: Callable[[str], Any], path: str) -> None:
    """Remove the write protection and repeat the operation that failed."""
    # "os.chmod(path, stat.S_IWRITE)" removed all read/execution permissions 
    # for all users, which is not intended. Instead, only the write permission
    # for the user should be added.
    os.chmod(path, os.stat(path).st_mode | stat.S_IWUSR)
    func(path)

def rmtree_force(path: str | os.PathLike[str]) -> None:
    """Like shutil.rmtree, but it also deletes read-only files."""
    # Python 3.12 added onexc (new signature for remove_readonly!) 
    # und deprecated onerror, which may be removed in 3.14.
    if sys.version_info >= (3, 12):
        def onexc(func: Callable[[str], Any], p: str, exc: BaseException) -> None:
            _make_writable_and_retry(func, p)

        shutil.rmtree(path, onexc=onexc)
    else:
        def onerror(
            func: Callable[[str], Any],
            p: str,
            exc_info: tuple[type[BaseException], BaseException, TracebackType],
        ) -> None:
            _make_writable_and_retry(func, p)

        shutil.rmtree(path, onerror=onerror)

def remove_readonly(
        func: Callable[[str], Any], 
        path: str, 
        exc_info: tuple[type[BaseException], BaseException, TracebackType]):
    """Remove write protection and continue delete process."""
    mode = os.stat(path).st_mode
    os.chmod(path, mode | stat.S_IWUSR)
    # "os.chmod(path, stat.S_IWRITE)" removed all read/execution permissions 
    # for all users, which is not intended. Instead, only the write permission
    # for the user should be added.
    func(path)

def delete_dir(dir: str, usePython: bool=True):
    if dir == 'none':
        return
    p = Path(dir)
    if p.is_file():
        abort('delete_dir:', dir, 'is a file instead of a directory')
    if not p.is_dir():
        return
    print('Removing', dir, 'directory...')
    if usePython == True:
        rmtree_force(p)
    else:
        RUNNER.do('rm -R ' + dir)

def make_empty_dir(dir: str):
    delete_dir(dir)
    if 'simulate' not in RUNNER_OPTIONS:
        os.makedirs(dir, 0o755)

def is_dir_or_abort(dir: str):
    if not os.path.isdir(dir):
        abort('Directory missing  ' + dir)

def is_file_or_abort(path: str):
    if not os.path.isfile(path):
        abort('File missing  ' + path)

def delete_file(file: str):
    if os.path.isfile(file):
        os.remove(file)

def append_logfile(logFile: str, tag: str):
    print('action:', tag)
    comment = input('Add comment to action for logfile:  ')
    with open(logFile, 'a') as f:
        f.write(tag + comment + '\n')
    print('Comment added in:     ', logFile)

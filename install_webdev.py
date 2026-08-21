#!/usr/bin/env python
# This little helper script copies the webdev files into a folder of your choice.
import os, shutil, stat
from pathlib import Path
try:                # for line editing on input for Linux
    import readline # type: ignore
except ImportError:
    readline = None

# List of tuples comprising subdirectories and scripts they contain:
_TOOL_LIST: list[ tuple[str, str] ] = [
    ('showdns', 'show_dns.py'),
    ('parsecerts', 'parse_certificates.py'),
    ('vhosts', 'show_vhosts.py'),
    ('vhosts', 'backup_vhost_confs.sh'),
    ('vhosts', 'create_vhost_pool.sh'),
    ('websitemanager', 'website_manager.py'),
    ('websitemanager', 'load_site_from_ftp.py'),
    ('websitemanager', 'dbaccess_adjustment.py'),
    ('websitereporter', 'website_reporter.py'),
    ('mediawiki', 'mediawiki_update.py'),
    ('certs', 'test_cert_renewal.sh'),
]

# List of of tuples of tool dirs and its module subdirectories:
_MODULE_LIST: list[ tuple[str, str] ] = [
    ('websitemanager', 'wm'),
    ('websitereporter', 'wr'),
    ('mediawiki', 'mu'),
]

def abort(msg: str=''):
    if msg != '':
        print('...' + msg)
    print('...aborting')
    quit()

def query_continue():
    ch = input('Enter q to abort or other key to continue: ')
    if ch == 'q':
        quit()

def query_int(msg: str, min_value: int, max_value: int) -> int:
    try:
        num = int(input(f"{msg} [{min_value}-{max_value}]: "))
        if num < min_value or num > max_value:
            abort(f'number out of range [{min_value}-{max_value}]')
            quit()
    except ValueError:
        abort('not a number')
        quit()
    return num

def copy_file(src: str, dest: str):
    shutil.copy2(src, dest)
    print('copied', src, 'to', dest)

def contains_subdir(dir: str) -> bool:
    for item in os.listdir(dir):
        item_path = os.path.join(dir, item)
        if os.path.isdir(item_path):
            return True
    return False

def make_executable(file: str):
    st = os.stat(file)
    os.chmod(file, st.st_mode | stat.S_IEXEC)
    print(file, 'made executable')

def install_tool_scripts(webdev_path: str, target_folder: str):
    for subdir, script in _TOOL_LIST:
        source_file = os.path.join(webdev_path, subdir, script)
        target_script = os.path.join(target_folder, script)
        if not os.path.isfile(source_file):
            abort('source file ' + source_file + ' is missing')
        if os.path.exists(target_script) and not os.path.isfile(target_script):
            abort(target_script + ' is not a file!')
        if os.path.isfile(target_script):
            print(f'==> {target_script} will be overwritten')
        else:
            print(f'--> {target_script} is created')
    query_continue()
    for subdir, script in _TOOL_LIST:
        source_file = os.path.join(webdev_path, subdir, script)
        target_script = os.path.join(target_folder, script)
        copy_file(source_file, target_script)
        make_executable(target_script)

def replace_tree(src: str, dest: str):
    if not os.path.isdir(src):
        abort(' ' + src + ' is missing')
    if os.path.isfile(dest):
        abort(dest + ' is an existing file and not a directory')
    if os.path.isdir(dest):
        print('replace existing folder', dest, 'with', src)
        query_continue()
        shutil.rmtree(dest)
    else:
        print('copy folder', src, 'to', dest)
    shutil.copytree(src, dest)

def install_modules(source_dir: str, target_dir: str):
    source_dest_list: list[tuple[str, str]] = []
    for tool_dir, module_dir in _MODULE_LIST:
        module_source_path = os.path.join(source_dir, tool_dir, module_dir)
        module_dest_path = os.path.join(target_dir, module_dir)
        if not os.path.isdir(module_source_path):
            abort('source dir ' + module_source_path + ' is missing')
        if os.path.exists(module_dest_path) and not os.path.isdir(module_dest_path):
            abort(module_dest_path + ' is not a directory!')
        if os.path.isdir(module_dest_path):
            print(f'==> {module_dest_path} will be overwritten')
        else:
            print(f'--> {module_dest_path} is created')
        source_dest_list.append((module_source_path, module_dest_path))
    query_continue()
    for src, dest in source_dest_list:
        replace_tree(src, dest)

def find_writable_backup_script(target_rel_file: str) -> list[str]:
    # Start at the directory of the current script
    current_dir = Path(__file__).resolve().parent
    print("Searching for", target_rel_file)
    print("Start from", current_dir)
    print("Search the directory path all the way to the root")
    # The relative target file path used to search within each folder
    #target_rel_path = Path("Backup/script/website_manager.py")
    target_rel_path = Path(target_rel_file)
    valid_directories: list[str] = []

    while True:
        # 1. Exit condition: No longer has permission to read the current directory
        if not os.access(current_dir, os.R_OK | os.X_OK):
            break
        target_file = current_dir / target_rel_path
        # print("===> look for", target_file)
        if target_file.is_file():
            # Check whether the file found is writable
            if os.access(target_file, os.W_OK):
                valid_directories.append(str(target_file.parent))
            else:
                # 2. Exit condition: File found, but no write permissions
                break
        # 3. Exit condition: Root directory (e.g. ‘/’) reached
        parent_dir = current_dir.parent
        if parent_dir == current_dir:
            break
        # Go up one level
        current_dir = parent_dir
    return valid_directories

def create_folder(folder_path: str) -> None:
    # .resolve() converts the path to an absolute one, which prevents
    # problems when locating the root directory for relative paths.
    p = Path(folder_path).resolve()
    # If folder_path already exists, stop
    if p.exists():
        return
    # Find the first existing parent directory
    closest_existing_parent = p.parent
    while not closest_existing_parent.exists():
        closest_existing_parent = closest_existing_parent.parent
    # If writing to this directory is not permitted, abort
    if not os.access(closest_existing_parent, os.W_OK):
        return
    # Create a new directory, including all missing subfolders
    try:
        # parents=True entspricht dem Linux-Befehl `mkdir -p`
        p.mkdir(parents=True)
    except OSError as e:
        print(f"Fehler beim Erstellen von {p}: {e}")

# main script -----------------------------------------------...
def main():
    print()
    # look for an existing installation folde
    script_file_searched_for = "Backup/script/website_manager.py"
    folder_list = find_writable_backup_script(script_file_searched_for)

    # select target folder
    num_folders = len(folder_list)
    if num_folders > 1:
        print(">>> Warning: multiple installation folders found")
        print(*folder_list, sep="\n")
        query_continue()
        print('Where to copy the scripts?')
        for i in range(0, num_folders):
            print(i, ":", folder_list[i])
        option = query_int('Enter int: ', 0, num_folders-1)
        target_folder = folder_list[option]
    elif num_folders == 0:
        print(">>> No installation folder was found")
        target_folder = input('Enter full installation path: ')
        if not os.path.exists(target_folder):
            create_folder(target_folder)
    else:
        target_folder = folder_list[0]
        print('Found installation folder:', target_folder)
        query_continue()

    # target folder must already exist
    if not os.path.isdir(target_folder):
        abort(target_folder + ' is missing')
    if not os.access(target_folder, os.W_OK):
        abort('missing write permissions in folder: ' + target_folder)
    if not contains_subdir('.'):
        abort(os.getcwd() + ' does not contain any directories')

    webdev_path = os.path.dirname(os.path.realpath(__file__))
    print('Install webdev from folder:', webdev_path)

    install_tool_scripts(webdev_path, target_folder)
    install_modules(webdev_path, target_folder)

    print('...installation finished')

if __name__ == "__main__":
    main()

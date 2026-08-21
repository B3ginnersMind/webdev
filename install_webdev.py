#!/usr/bin/env python
# This little helper script copies the webdev files into a folder of your choice.
import os, pathlib, shutil, stat
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

# main script -----------------------------------------------...
def main():

    # select target folder
    HOME = str(pathlib.Path.home())
    BACKUP = '/Backup/script'
    HOME_BACKUP = HOME + '/' + BACKUP

    print('Where to copy the scripts?')
    print('1    : ', HOME)
    print('2    : ', BACKUP)
    print('3    : ', HOME_BACKUP)
    print('4    : ', 'other folder')
    print('other: ', 'quit script')
    option = query_int('Enter int: ', 1, 4)

    if option == 1:
        target_folder = HOME
    elif option == 2:
        target_folder = BACKUP
    elif option == 3:
        target_folder = HOME_BACKUP
    else:
        target_folder = input('Enter full installation path: ')

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

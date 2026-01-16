#!/usr/bin/env python
# This little helper script copies the webdev files into a folder of your choice.
import os, pathlib, shutil, stat

def abort(msg=''):
    if msg != '':
        print('...' + msg)
    print('...aborting')
    quit()

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

def copy_file(src, dest):
    if not os.path.isfile(src):
        abort('file ' + src + ' is missing')
    if os.path.isfile(dest):
        print(dest + ' will be overwritten')
        query_continue()
    shutil.copy2(src, dest)
    print('copied', src, 'to', dest)

def contains_subdir(dir):
    for item in os.listdir(dir):
        item_path = os.path.join(dir, item)
        if os.path.isdir(item_path):
            return True
    return False

def make_executable(file):
    st = os.stat(file)
    os.chmod(file, st.st_mode | stat.S_IEXEC)
    print(file, 'made executable')

def install_pyscript(webdev_path, subdir, pyscript, target_folder):
    source_file = os.path.join(webdev_path, subdir, pyscript)
    target_script = os.path.join(target_folder, pyscript)
    copy_file(source_file, target_script)
    make_executable(target_script)

def replace_tree(src, dest):
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

# main script -----------------------------------------------...
def main():

    # select target folder
    HOME = str(pathlib.Path.home())
    BACKUP = '/Backup/script'

    print('Where to copy the scripts?')
    print('1    : ', HOME)
    print('2    : ', BACKUP)
    print('3    : ', 'other folder')
    print('other: ', 'quit script')
    option = query_int('Enter int: ', 1, 3)

    if option == 1:
        target_folder = HOME
    elif option == 2:
        target_folder = BACKUP
    elif option == 3:
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

    install_pyscript(webdev_path, 'showdns', 'show_dns.py', target_folder)
    install_pyscript(webdev_path, 'parsecerts', 'parse_certificates.py', target_folder)
    install_pyscript(webdev_path, 'showvhosts', 'show_vhosts.py', target_folder)
    install_pyscript(webdev_path, 'websitemanager', 'website_manager.py', target_folder)
    install_pyscript(webdev_path, 'websitemanager', 'load_site_from_ftp.py', target_folder)
    install_pyscript(webdev_path, 'mediawiki', 'mediawiki_update.py', target_folder)

    websitemanager_module = os.path.join(webdev_path, 'websitemanager', 'wm')
    websitemanager_module_dest = os.path.join(target_folder, 'wm')
    replace_tree(websitemanager_module, websitemanager_module_dest)

    mw_updateer_module = os.path.join(webdev_path, 'mediawiki', 'mu')
    mw_updateer_module_dest = os.path.join(target_folder, 'mu')
    replace_tree(mw_updateer_module, mw_updateer_module_dest)

    print('...installation finished')

if __name__ == "__main__":
    main()

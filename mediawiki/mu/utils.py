
import configparser, grp, logging, os, pwd, shutil, zipfile
import mu.constants as const
from subprocess import run
from pathlib import PurePosixPath, Path
from mu.dataclasses import Release, UpdateData

def query_continue():
    ch = input('Enter q to abort or other key to continue: ')
    if ch == 'q':
        quit()

def read_config(config_path: Path, section: str = "settings") -> UpdateData:
    """
    Read input data from the config file. This is an example config:

    # comment about the config
    [settings]
    mw_folder_live = "/var/www/newhomoeopedia"
    mw_basefolder_new = "/home/koerkel/cms/mediawiki"
    release_new = "1.45.1"
    """
    logging.info(f"Reading configuration from: {config_path}")
    logging.info(f"Configuration section: {section}")
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    config = configparser.ConfigParser()
    config.read(config_path)
    data: UpdateData = UpdateData()
    data.mw_folder_live = Path(config.get(section, "mw_folder_live"))
    data.mw_basefolder_new = Path(config.get(section, "mw_basefolder_new"))
    data.release_new = Release(config.get(section, "release_new"))
    data.php_command = config.get(section, "php_command")
    data.group_owner = config.get(section, "group_owner")
    # int(value, 0):
    # Base 0 means "auto-detect the base from the prefix"
    data.dir_mode = int(config.get(section, "dir_mode"), 0)
    data.file_mode = int(config.get(section, "file_mode"), 0)
    return data

def remtree(path: Path) -> None:
    """Recursively remove a directory tree."""
    if path.is_dir():
        logging.warning(f"Removing already existing folder: {path}")
        shutil.rmtree(str(path))
    elif path.is_file():
        raise RuntimeError(f"Expected directory but found file: {path}")

def get_zip_root_folder(zip_path: str) -> str:
    """
    Returns the root directory name of a ZIP file that contains
    exactly one top-level directory tree.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        roots = set()

        for name in zf.namelist():
            # Ignore empty entries
            if not name.strip():
                continue

            parts = PurePosixPath(name).parts
            if parts:
                roots.add(parts[0])

        if len(roots) != 1:
            raise ValueError(
                f"ZIP does not contain exactly one root directory: {roots}"
            )

        return roots.pop()

def copy_live_site_data(src_dir: Path, dst_dir: Path) -> None:
    """
    src_dir is the root folder of the live Mediawiki.
    .htaccess, LocalSettings.php, images and txt files 
    are copied from src_dir to dst_dir if they exist in src_dir.
    Foldere tree src_dir/images is copied to dst_dir/images.
    """
    logging.info(const.SHORT_LINE + f" copy_live_site_data:")
    logging.info(f"Source directory: {src_dir}")
    logging.info(f"Destination directory: {dst_dir}")

    COPIED_EXTENSIONS = {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".txt"
    }
    FURTHER_FILES = [".htaccess", "LocalSettings.php"]
    dst_dir.mkdir(parents=True, exist_ok=True)
    for src_path in src_dir.iterdir():
        if not src_path.is_file():
            continue
        if (
            src_path.suffix.lower() in COPIED_EXTENSIONS or
            src_path.name in FURTHER_FILES
           ):
            logging.info(f"Copying file: {src_path.name}")
            dst_path = dst_dir / src_path.name
            shutil.copy2(src_path, dst_path)

    src_images_dir = src_dir / "images"
    dst_images_dir = dst_dir / "images"
    remtree(dst_images_dir)
    logging.info(f"Copying images folder from: {src_images_dir}")
    logging.info(f"To: {dst_images_dir}")
    shutil.copytree(src_images_dir, dst_images_dir)
    logging.info(const.LONG_LINE)

def fix_permissions_mw_folder_new(d: UpdateData):
    """
    Adjust the permissions for the webfile tree (owner and mode).
    Take the values frim the ini file. Owner change skipped without sudo!
    """
    do_chown = os.getuid() == 0
    folder: Path = d.mw_folder_new
    logging.info(f"Fix permissions of folder tree: {folder}")
    if not do_chown:
        logging.warning(f"Skipping ôwner fix since skript not run as root.")
    if not folder.is_dir():
        raise ValueError(f"{folder} is not a directory")
    if do_chown: # Resolve uid and gid
        uid = pwd.getpwnam(d.user_owner).pw_uid
        gid = grp.getgrnam(d.group_owner).gr_gid
    # Change root folder
    os.chmod(folder, d.dir_mode)
    if do_chown: os.chown(folder, uid, gid)
    # Walk directory tree
    for p in folder.rglob("*"):
        if do_chown: os.chown(p, uid, gid)
        if p.is_dir():
            os.chmod(p, d.dir_mode)
        else:
            os.chmod(p, d.file_mode)

def exchange_live_new_mw_folder(d: UpdateData):
    """
    Move the live folder to a backup folder.
    Move the new folder to the live folder path.
    """
    logging.info(const.SHORT_LINE + " exchange_live_new_mw_folder:")
    save_base_dir = d.mw_basefolder_new / "backup"
    os.makedirs(save_base_dir, exist_ok=True)
    save_dir = save_base_dir / d.mw_folder_live.name
    remtree(save_dir)
    logging.info(f"Move: {d.mw_folder_live}")
    logging.info(f"To: {save_dir}")
    shutil.move(str(d.mw_folder_live), str(save_dir))
    logging.info(f"Move: {d.mw_folder_new}")
    logging.info(f"To: {d.mw_folder_live}")
    shutil.move(str(d.mw_folder_new), str(d.mw_folder_live))
    logging.info(const.LONG_LINE)

def run_php(d: UpdateData, php_script_call: str):
    """
    Run a PHP skript.
    The interpreter command is taken from the ini file.
    'php_script_call' contains the actual PHP commands.
    """
    logging.info(const.SHORT_LINE + " run_php:")
    command = list()
    command.append(d.php_command)
    command.extend(php_script_call.split(" "))

    plain_command = ""
    for token in command:
        plain_command += token + " "
    logging.info(f"Running command: {plain_command}")

    result = run(command, capture_output=True, text=True, check=True)
    str_len = len(result.stdout)
    post_fix = ""
    if str_len > 0:
        c = result.stdout[str_len-1]
        if c != "\n":
            post_fix = "\n"
    logging.info("Result:\n\n" + result.stdout + post_fix)
    logging.info(const.LONG_LINE)

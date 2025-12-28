#!/usr/bin/env python
"""
Update a Mediawiki installation. Also perform the database update.
Input data is taken from a section of a config file.
See file 'mediawiki_update.txt'. Example for 'mediawiki_update.ini':

[mysite]
mw_folder_live = /var/www/mywebsite
mw_basefolder_new = /home/user/mediawiki
release_new = 1.45.1
php_command = php8.2
user_owner = www-data
group_owner = www-data
dir_mode = 0o750
file_mode = 0o640
"""
__version__ = "1.03"
import argparse, logging, os, platform, shutil
from pathlib import Path
import mu.utils as utils
from mu.dataclasses import Release, UpdateData
from mu.mediawiki_fetcher import get_mediawiki_release
from mu.mediawiki_version_detector import detect_mediawiki_version
from mu.missing_folders import get_missing_folders
from mu.extension_fetcher import fetch_missing_extensions
from mu.skin_fetcher import fetch_missing_skins

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("mediawiki_update.log"),
        logging.StreamHandler()
    ]
)

def update(config_path: Path, config_section: str):
    current_sysem =  platform.system()
    # "Linux" may be Ubuntu, Debian, RHEL ...
    if current_sysem != 'Linux':
        if current_sysem in ('FreeBSD', 'OpenBSD'):
            logging.warning(f"Untested operation system type: {current_sysem}")
        else:
            logging.error(f"Unsupported system: {current_sysem}")
            quit()

    if os.getuid() != 0:
        logging.warning(f"Skript not run as root. Proceed anyway?")
        utils.query_continue()

    data: UpdateData = utils.read_config(config_path, config_section)
    data.test_input()
    data.release_live = detect_mediawiki_version(data.mw_folder_live)
    data.show()
    data.test_before_update()

    logging.info("Files of live website will be updated, as will its database.")
    logging.info("Have you made a backup yet? Procceed with the update?")
    utils.query_continue()

    get_mediawiki_release(data)
    detected_new_release = detect_mediawiki_version(data.mw_folder_new)
    if detected_new_release != data.release_new:
        logging.error(
            "Version mismatch: requested %s but got %s",
            data.release_new,
            detected_new_release
        )
        raise ValueError("Version mismatch after download")

    # which extensions are missing in the new code base?
    missing_extensions = get_missing_folders(data, "extensions")
    # which skins are missing in the new code base?
    missing_skins = get_missing_folders(data, "skins")

    fetch_missing_extensions(data, missing_extensions)
    fetch_missing_skins(data, missing_skins)
    utils.copy_live_site_data(data.mw_folder_live, data.mw_folder_new)

    # Do the the database update skripts exist?
    location = str(data.mw_folder_new / "maintenance")
    skripts = [location + "/run.php", location + "/update.php"]
    status = [os.path.exists(f) for f in skripts]
    if not (all(status)):
        logging.error("run.php or update.php skript missing in maintenance folder.")
        quit()

    # run chown and chmod for new Mediawiki folder
    utils.fix_permissions_mw_folder_new(data)
    utils.exchange_live_new_mw_folder(data)

    # run database update
    utils.run_php(data, str(data.mw_folder_live) + "/maintenance/run.php update")

def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        # formatter used to preserve the raw doc format
        formatter_class=argparse.RawTextHelpFormatter
        )
    
    p.add_argument("-c", "--config", type=str,
                   help="config file path instead of default './mediawiki_update.ini'")
    p.add_argument("section", type=str, default='none',
                   help="section of the config file to be read")
    p.add_argument("-v", "--version", action='version', 
                   version='%(prog)s version {version}'.format(version=__version__))
    args = p.parse_args()

    ini_file = Path(__file__).parent.resolve() / "mediawiki_update.ini"
    if args.config:
        ini_file = Path(args.config)

    logging.info("Starting Mediawiki update")
    update(ini_file, args.section)

if __name__ == "__main__":
    main()

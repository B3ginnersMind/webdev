import logging, shutil, tarfile
import urllib.request
from pathlib import Path
from helper.extension_link_finder import get_extension_link
from helper.dataclasses import UpdateData

def fetch_missing_extensions(d: UpdateData, missing_extensions: list) -> None:
    """
    Fetch and install missing extensions into the new Mediawiki installation.

    Args:
        missing_extensions (list): List of missing extension names.
        new_major_version (str): Major version string of the new Mediawiki release.
        mw_basefolder_new (str): Base folder path for the new Mediawiki installation.
        mw_folder_new (str): Full path to the new Mediawiki installation folder.
    """
    logging.info(f"============================ fetch_missing_extensions: {len(missing_extensions)}")
    URL_EXTENSIONS = "https://extdist.wmflabs.org/dist/extensions/"
    for ext in missing_extensions:
        logging.info(85 *"-")
        logging.info(f"Processing extension: {ext}")
        
        # get the download link
        prefix = URL_EXTENSIONS+ ext + "-REL1_" + str(d.version_new.major)
        logging.info(f"Prefix: {prefix}")
        dowload_link = get_extension_link(URL_EXTENSIONS, prefix)
        if dowload_link is None:
            continue

        # download the archive into the new mediawiki base folder
        archive = f"{ext}-REL1_{d.version_new.major}.tar.gz"
        archive_path = d.mw_basefolder_new / archive
        logging.info(f"Archive path: {archive_path}")
        urllib.request.urlretrieve(dowload_link, str(archive_path))
        logging.info(f"Extension archive downloaded")

        # extract the archive into the new mediawiki base folder
        # it will be extracted into a subfolder named after the extension
        with tarfile.open(str(archive_path), 'r:gz') as tar:
            tar.extractall(path=str(d.mw_basefolder_new))
        logging.info(f"Archive extracted")
        # verify that the extension folder now exists
        ext_folder = d.mw_basefolder_new / ext
        if ext_folder.is_dir():
            logging.info(f"New extension folder exists: {ext_folder}")
        else:
            logging.error(f"Extension folder missing after extraction: {ext_folder}")
            continue

        # copy the extension folder into the new mediawiki installation
        target_folder = d.mw_folder_new / "extensions" / ext
        logging.info(f"Move to: {target_folder}")

        if target_folder.is_dir():
            logging.warning(f"Target folder already exists, remove it")
            shutil.rmtree(str(target_folder))
        shutil.move(str(ext_folder), str(target_folder))
        if target_folder.is_dir():
           logging.info(f"Extension {ext} installed into new Mediawiki installation.")
        else:
            raise RuntimeError(f"Failed to move extension {ext} to target folder.") 

    logging.info(85 *"=")

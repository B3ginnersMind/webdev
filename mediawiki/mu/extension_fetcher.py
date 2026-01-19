import logging, shutil, tarfile
import urllib.request
import mu.constants as const
import mu.utils as utils
from mu.extension_link_finder import get_extension_link
from mu.dataclasses import UpdateData

def fetch_missing_extensions(d: UpdateData, missing_extensions: list) -> None:
    """
    Fetch and install missing extensions into the new Mediawiki installation.
    Args:
        d (UpdateData): Data class containing update information.
        missing_extensions (list): List of missing extension names.
    Note:
    release_new.major is used to determine the correct version of the extensions to download.
    release_basefolder() is used to determine where to download and extract the extensions.
    mw_folder_new is used to determine where to install the extensions.
    """
    logging.info(const.SHORT_LINE + f" fetch_missing_extensions: {len(missing_extensions)}")
    for ext in missing_extensions:
        logging.info(const.THIN_LINE)
        logging.info(f"Processing extension: {ext}")
        
        # get the download link
        prefix = const.URL_EXTENSIONS+ ext + "-REL1_" + str(d.release_new.major)
        logging.info(f"Prefix: {prefix}")
        download_link = get_extension_link(const.URL_EXTENSIONS, prefix)
        if download_link is None:
            logging.warning(f"Download link not found for extension: {ext}")
            continue

        # download the archive into the new mediawiki base folder
        archive = f"{ext}-REL1_{d.release_new.major}.tar.gz"
        archive_path = d.release_basefolder() / archive
        logging.info(f"Archive path: {archive_path}")
        urllib.request.urlretrieve(download_link, str(archive_path))
        logging.info(f"Extension archive downloaded")
 
        # extract the archive into the new mediawiki base folder
        # it will be extracted into a subfolder named after the extension
        with tarfile.open(str(archive_path), 'r:gz') as tar:
            tar.extractall(path=str(d.release_basefolder()))
        logging.info(f"Archive extracted")
        # verify that the extension folder now exists
        ext_folder = d.release_basefolder() / ext
        if ext_folder.is_dir():
            logging.info(f"New extension folder exists: {ext_folder}")
        else:
            logging.warning(f"Extension folder missing after extraction: {ext_folder}")
            continue

        # copy the extension folder into the new mediawiki installation
        target_folder = d.mw_folder_new / "extensions" / ext
        logging.info(f"Move to: {target_folder}")

        utils.remtree(target_folder)
        shutil.move(str(ext_folder), str(target_folder))
        if target_folder.is_dir():
           logging.info(f"Extension {ext} installed into new Mediawiki installation.")
        else:
            raise RuntimeError(f"Failed to move extension {ext} to target folder.") 

    logging.info(const.LONG_LINE)

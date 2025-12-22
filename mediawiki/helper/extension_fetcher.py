import logging, shutil, tarfile
import urllib.request
from pathlib import Path
from helper.extension_link_finder import get_extension_link

def fetch_missing_extensions(
    missing_extensions: list,
    new_major_version: str,
    mw_basefolder_new: Path,
    mw_folder_new: Path
) -> None:
    """
    Fetch and install missing extensions into the new Mediawiki installation.

    Args:
        missing_extensions (list): List of missing extension names.
        new_major_version (str): Major version string of the new Mediawiki release.
        mw_basefolder_new (str): Base folder path for the new Mediawiki installation.
        mw_folder_new (str): Full path to the new Mediawiki installation folder.
    """
    URL_EXTENSIONS = "https://extdist.wmflabs.org/dist/extensions/"
    for ext in missing_extensions:
        logging.info(85 *"-")
        logging.info("Processing extension: %s", ext)
        
        # get the download link
        prefix = URL_EXTENSIONS+ ext + "-REL1_" + new_major_version
        logging.info("Prefix: %s", prefix)
        dowload_link = get_extension_link(URL_EXTENSIONS, prefix)
        if dowload_link is None:
            logging.error("Missing download link for %s", ext)
            continue
        logging.info("Found link: %s", dowload_link)

        # download the archive into the new mediawiki base folder
        archive = f"{ext}-REL1_{new_major_version}.tar.gz"
        archive_path = mw_basefolder_new / archive
        logging.info("Archive path: %s", archive_path)
        urllib.request.urlretrieve(dowload_link, str(archive_path))
        logging.info("Downloaded extension archive: %s", archive_path)

        # extract the archive into the new mediawiki base folder
        # it will be extracted into a subfolder named after the extension
        with tarfile.open(str(archive_path), 'r:gz') as tar:
            tar.extractall(path=str(mw_basefolder_new))
        logging.info("Archive extracted: %s", archive_path)
        # verify that the extension folder now exists
        ext_folder = mw_basefolder_new / ext
        if ext_folder.is_dir():
            logging.info("New extension folder exists: %s", ext_folder)
        else:
            logging.error("Extension folder missing after extraction: %s", ext_folder)
            continue
        # copy the extension folder into the new mediawiki installation
        target_folder = mw_folder_new / "extensions" / ext
        logging.info("Move to: %s", target_folder)
        if target_folder.is_dir():
            logging.warning("Target extension folder already exists, overwriting: %s", target_folder)
            shutil.rmtree(str(target_folder))
        shutil.move(str(ext_folder), str(target_folder))
        logging.info("Extension %s installed into new Mediawiki installation.", ext)

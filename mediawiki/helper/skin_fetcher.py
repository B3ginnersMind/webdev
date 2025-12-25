import logging, shutil
import urllib.request
from pathlib import Path
import zipfile
import helper.constants as const
import helper.utils as utils
from helper.dataclasses import UpdateData

def fetch_missing_skins(d: UpdateData, missing_skins: list) -> None:
    """
    Docstring for fetch_missing_skins
    
    :param d: read release_basefolder() and mw_folder_new
    :type d: UpdateData
    :param missing_skins: names of missing skins in new Mediawiki release
    :type missing_skins: list

    Only skin Citizen is treated. Its latest zip archive is downloaded and extracted.
    The skin is then moved to the folder of the new Mediawiki release.
    """
    logging.info(const.SHORT_LINE + f" fetch_missing_skins: {len(missing_skins)}")
    for skin in missing_skins:
        logging.info(const.THIN_LINE)
        logging.info(f"Processing skin: {skin}")
        if skin == const.CITIZEN_NAME:
            logging.info(f"Special handling for {skin} skin")
            # download the archive into the mediawiki major release folder
            archive_path = d.release_basefolder() / const.ARCHIVE_CITIZEN_SKIN
            logging.info(f"Downloading from {const.URL_CITIZEN_SKIN}")
            logging.info(f"To: {archive_path}")
            urllib.request.urlretrieve(const.URL_CITIZEN_SKIN, archive_path)
            if not archive_path.is_file():
                logging.warning(f"Failed to download Citizen skin archive.")
                continue
            
            root: str = utils.get_zip_root_folder(archive_path)
            logging.info(f"Root folder in zip: {root}")
            extraction_folder: Path = d.release_basefolder() / root
            utils.remtree(extraction_folder)
            skin_folder = d.release_basefolder() / const.CITIZEN_NAME
            utils.remtree(skin_folder)
            
            # may raise a BadZipFile exception
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(path=str(d.release_basefolder()))
            if not extraction_folder.is_dir():
                logging.warning(f"Extraction failed, root folder missing: {root}")
                continue
            logging.info(f"Archive extracted")

            # rename the extracted folder to 'Citizen'
            skin_folder = d.release_basefolder() / const.CITIZEN_NAME
            extraction_folder.rename(skin_folder)
            logging.info(f"Skin folder renamed to: {const.CITIZEN_NAME}")

            # copy the skin folder into the new mediawiki installation
            target_folder = d.mw_folder_new / "skins" / skin
            logging.info(f"Move to: {target_folder}")
            utils.remtree(target_folder)
            shutil.move(skin_folder, target_folder)
            if target_folder.is_dir():
                logging.info(f"Skin {skin} installed into new Mediawiki installation.")
            else:
                raise RuntimeError(f"Failed to move extension {skin} to target folder.") 
        else:
            logging.warning(f"No special handling for skin: {skin}, skipping.")
            continue

    logging.info(const.LONG_LINE)

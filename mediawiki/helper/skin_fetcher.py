import logging, shutil, tarfile
import urllib.request
from pathlib import Path
from helper.dataclasses import UpdateData

def fetch_missing_skins(s: UpdateData, missing_skins: list) -> None:
    logging.info(f"============================ fetch_missing_skins: {len(missing_skins)}")

    # # /skins/Citizen

    # for skin in missing_skins:
    #         logging.info(85 *"-")
    #         logging.info("Processing skin: %s", skin)

    #         logging.info(85 *"-")

    logging.info(85 *"=")

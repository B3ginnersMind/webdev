import logging
from pathlib import Path
from helper.dataclasses import UpdateData

#def get_missing_folders(folder_live: Path, folder_new: Path, subfolder: str) -> list[str]:
def get_missing_folders(d: UpdateData, subfolder: str) -> list[str]:
    """
    Iterates through all subfolders of folder_live/subfolder
    and checks if they exist in folder_new/subfolder.
    Returns a list of missing folder names.
    """
    logging.info(f"============================ get_missing_folders: {subfolder}")
    base_live: Path =  d.mw_folder_live / subfolder
    base_new: Path = d.mw_folder_new / subfolder
    logging.info(85 *"-")
    logging.info(f"Live release    : {d.mw_folder_live}")
    logging.info(f"New release     : {d.mw_folder_new}" )
    logging.info(f"Tested subfolder: {subfolder}")
    logging.info("Which subfolders are missing in the new release?")

    if not  base_live.is_dir():
        raise FileNotFoundError(f"Live installation not found: {base_live}")

    if not base_new.is_dir():
        # If the target subfolder is missing, all are considered missing.
        return [
            item.name for item in base_live.iterdir()
            if item.is_dir()
        ]

    missing: list[str] = []

    for child in base_live.iterdir():
        new_path = base_new / child.name
        if child.is_dir() and not new_path.is_dir():
            missing.append(child.name)

    if not missing:
        logging.info("=> Nothing is missing.")
    else:
        logging.info(f"=> Missing: {missing}")
  
    logging.info(85 *"=")
    return missing

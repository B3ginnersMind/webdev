import logging, os
from pathlib import Path
from dataclasses import dataclass

@dataclass(order=True)
class Release:
   """ Mediawiki release """
   main: int = 0
   major: int = 0
   minor: int = 0
   def __init__(self, lead: int | str = 0, major: int = 0, minor: int = 0) -> None:
      if isinstance(lead, str):
         parts = lead.split(".")
         if len(parts) < 2 or len(parts) > 3:
            raise ValueError(f"Invalid release: {lead}")
         self.main = int(parts[0])
         self.major = int(parts[1])
         self.minor = int(parts[2])
      else:
         self.main = lead
         self.major = major
         self.minor = minor
   def __str__(self) -> str:
      return f"{self.main}.{self.major}.{self.minor}"

@dataclass
class UpdateData:
   """
   Data for live and new Mediawiki files
   """
   mw_folder_live: Path = None
   release_live: Release = None
   mw_basefolder_new: Path = None
   release_new: Release = None
   mw_folder_new: Path = None
   php_command: str = "php"
   user_owner: str = "www-data"
   group_owner: str = "www-data"
   dir_mode: int = int(0o750)
   file_mode: int = int(0o640)

   def release_basefolder(self) -> Path:
      if self.mw_basefolder_new is None or self.release_new is None:
         raise ValueError("mw_basefolder_new and release_new must be set")
      rel_folder = self.mw_basefolder_new / \
                   f"{self.release_new.main}.{self.release_new.major}"
      if rel_folder.is_file():
         raise NotADirectoryError(f"Release basefolder is a file: {rel_folder}")
      if not rel_folder.is_dir():
         os.makedirs(rel_folder)
      return rel_folder
   
   def show(self) -> None:
      logging.info(f"Live folder: {self.mw_folder_live}")
      logging.info(f"Live Mediawiki version: {self.release_live}")
      logging.info(f"Base folder of new release: {self.mw_basefolder_new}")
      logging.info(f"Requested release: {self.release_new}")
      if self.mw_folder_new:
         logging.info(f"New folder after download: {self.mw_folder_new}")
      logging.info(f"PHP command: {self.php_command}")
      logging.info(f"Owner: {self.user_owner}")
      logging.info(f"Group: {self.group_owner}")
      logging.info(f"Directory permissions: {self.dir_mode}")
      logging.info(f"File permissions: {self.file_mode}")
   
   def test_input(self):
      if not self.mw_folder_live.is_dir():
         raise ValueError(f"Invalid live release: {self.mw_folder_live}")
      if (self.release_new.main == 0 
         or self.release_new.major == 0
         or self.release_new.minor == 0
         ):
         raise ValueError(f"Invalid required release: {self.release_new}")

   def test_before_update(self):
      self.test_input()
      if (self.release_live.main == 0 
         or self.release_live.major == 0
         or self.release_live.minor == 0
         ):
         raise ValueError(f"Invalid live release: {self.release_live}")
      if self.release_new <= self.release_live:
         raise ValueError(f"Required release not newer than live release")

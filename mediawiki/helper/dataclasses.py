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
      logging.info(f"New folder after download: {self.mw_folder_new}")

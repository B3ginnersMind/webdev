from pathlib import Path
from dataclasses import dataclass

@dataclass(order=True)
class Release:
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
   mw_folder_live: Path = None
   version_live: Release = Release()
   mw_basefolder_new: Path = None
   version_new: Release = Release()
   mw_folder_new: Path = None

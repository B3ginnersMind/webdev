import logging, re
from pathlib import Path
from mu.dataclasses import Release
import mu.constants as const
import mu.utils as utils

def detect_mediawiki_version(folder: Path) -> Release:
    """
    folder is the root of a MediaWiki installation.
    Look within includes/Defines.php after:
        define( 'MW_VERSION', 'VERSION' );
    und return VERSION zurück (e.g. '1.43.6').
    """
    logging.info(const.SHORT_LINE + " detect_mediawiki_version:")
    defines_path: Path = folder / "includes" / "Defines.php"
    
    if not defines_path.is_file():
        utils.error_exit(f"Defines.php not found in: {defines_path}")
        quit()

    pattern = re.compile(
        r"define\s*\(\s*['\"]MW_VERSION['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)\s*;"
    )

    with open(defines_path, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                release = match.group(1)
                logging.info(f"In MW folder: {folder}")
                logging.info(f"Found Mediawiki release: {release}")
                logging.info(const.LONG_LINE)
                return Release(release)
            
    utils.error_exit(f"Constant MW_VERSION not found in Defines.php: {defines_path}")
    quit()

    

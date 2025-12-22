import logging, os, re
from pathlib import Path

def detect_mediawiki_version(folder: Path) -> str:
    """
    folder is the root of a MediaWiki installation.
    Look within includes/Defines.php after:
        define( 'MW_VERSION', 'VERSION' );
    und return VERSION zurück (e.g. '1.43.6').
    """
    defines_path: Path = folder / "includes" / "Defines.php"
    
    if not defines_path.is_file():
        raise FileNotFoundError(f"Defines.php not found in: {defines_path}")

    pattern = re.compile(
        r"define\s*\(\s*['\"]MW_VERSION['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)\s*;"
    )

    with open(defines_path, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                release = match.group(1)
                logging.info("In MW folder:%s", folder)
                logging.info("Found Mediawiki release:%s", release)
                return release

    raise ValueError("Constant MW_VERSION not found in Defines.php")


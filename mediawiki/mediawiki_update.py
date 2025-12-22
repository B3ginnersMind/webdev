import logging
from pathlib import Path
from helper.mediawiki_fetcher import get_mediawiki_release
from helper.mediawiki_version_detector import detect_mediawiki_version
from helper.missing_folders import get_missing_folders
from helper.extension_fetcher import fetch_missing_extensions

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("mediawiki_update.log"),
        logging.StreamHandler()
    ]
)
logging.info("Starting Mediawiki update test script")
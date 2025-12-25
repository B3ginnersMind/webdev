"""
Download and extract a MediaWiki release archive.
"""
import logging, os, tarfile
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError
import helper.utils as utils
from helper.dataclasses import UpdateData
import helper.constants as const

def download_mediawiki_archive(url: str, target_path: Path) -> None:
    req = urllib.request.Request(
        url,
        headers={
            # Accepted user agent, avoids 403
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) MediaWiki-updater/1.0",
            "Accept": "*/*",
            "Connection": "close",
        }
    )
    logging.info(f"Downloading from: {url}")
    try:
        with urllib.request.urlopen(req, timeout=30) as response, \
             open(target_path, "wb") as out:

            # Stream download (memory-saving)
            block_size = 1024 * 64  # 64 KB
            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                out.write(chunk)

    except HTTPError as e:
        raise RuntimeError(
            f"HTTP-Fehler {e.code} beim Download von {url}"
        ) from e
    except URLError as e:
        raise RuntimeError(
            f"Netzwerkfehler beim Download von {url}: {e.reason}"
        ) from e

def get_mediawiki_release(d: UpdateData) -> None:
    """
    Download MediaWiki release archive in a robust way.
    Extract archive and stores everything into UpdateData.mw_basefolder_new. 
    Input example:
        UpdateData.release_new = Release("1.44.3")
        UpdateData.mw_basefolder_new = Path("/home/user")
    Downloads archive /home/user/mediawiki-1.44.3.tar.gz
    Extracts archive into:
        UpdateData.mw_folder_new <- /home/user/mediawiki-1.44.3/

    Features:
    -  Sets *valid user agent* (prevents 403)
    -  Streams large files (no RAM problem)
    -  Creates target directory automatically
    -  Clear error messages
    -  No external libraries
    """
    logging.info(const.SHORT_LINE + f" get_mediawiki_release: {d.release_new}")
    filename = f"mediawiki-{d.release_new}.tar.gz"
    logging.info(f"Requested Mediawiki archive: {filename}")
    url = (
        f"{const.MEDIAWIKI_RELEASE_BASE_URL}1.{d.release_new.major}/{filename}"
    )

    target_folder = d.mw_basefolder_new
    os.makedirs(target_folder, exist_ok=True)
    archive_path: Path = target_folder / filename
    if archive_path.is_file():
        logging.warning("Archive file already exists, keep it")
    else:
        download_mediawiki_archive(url, archive_path)
    
    d.mw_folder_new = target_folder / f"mediawiki-{d.release_new}"
    utils.remtree(d.mw_folder_new)

    logging.info(f"Extract archive: {filename}") 
    logging.info(f"Into folder: {target_folder}")
    with tarfile.open(archive_path, 'r:gz') as tar:
        tar.extractall(path=target_folder)
    if not d.mw_folder_new.is_dir():
        raise RuntimeError(
            f"Error: Missing extracted Mediawiki folder: {d.mw_folder_new}"
        )
    else:
        logging.info(f"Extracted Mediawiki folder exists: {d.mw_folder_new}")

    logging.info(const.LONG_LINE)

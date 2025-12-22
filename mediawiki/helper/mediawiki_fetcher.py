"""
Download and extract a MediaWiki release archive.
"""
import argparse, logging, os, tarfile
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError
from typing import Tuple

MEDIAWIKI_RELEASE_BASE_URL = "https://releases.wikimedia.org/mediawiki/"

def extract_mediawiki_archive(archive_path: Path, extract_to: Path) -> None:
    logging.info("Extracting: %s", archive_path)
    with tarfile.open(archive_path, 'r:gz') as tar:
        tar.extractall(path=extract_to)
    logging.info("...Archive extracted")

def get_mediawiki_release(major_release: int, minor_release: int,
                          target_folder: Path) -> Tuple[str, Path]:
    """
    Download MediaWiki release archive in a robust way. Example:
        major_release="44"
        minor_release="3"
        -> mediawiki-1.44.3.tar.gz
    Returns archive name and the path to the extracted files.

    Features:
    -  Sets *valid user agent* (prevents 403)
    -  Streams large files (no RAM problem)
    -  Creates target directory automatically
    -  Clear error messages
    -  No external libraries
    """

    filename = f"mediawiki-1.{major_release}.{minor_release}.tar.gz"
    url = (
        f"{MEDIAWIKI_RELEASE_BASE_URL}1.{major_release}/{filename}"
    )

    os.makedirs(target_folder, exist_ok=True)
    target_path: Path = target_folder / filename

    req = urllib.request.Request(
        url,
        headers={
            # Accepted UA, avoids 403
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) MediaWiki-updater/1.0",
            "Accept": "*/*",
            "Connection": "close",
        }
    )
    logging.info("Downloading from: %s", url)
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
    
    extract_mediawiki_archive(
        archive_path=target_path,
        extract_to=target_folder
    )
    new_mw_folder: Path = target_folder / f"mediawiki-1.{major_release}.{minor_release}"
    if not os.path.isdir(new_mw_folder):
        raise RuntimeError(
            f"Error: Missing eExctracted Mediawiki folder: {new_mw_folder}"
        )
    return (filename, new_mw_folder)

def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        # formatter used to preserve the raw doc format
        formatter_class=argparse.RawTextHelpFormatter
        )
    
    p.add_argument("-f", "--target_folder", type=str, default="~/cms/mediawiki",
               help="folder to download the release archive into")
    p.add_argument("-m", "--major_release", type=str, default="44",
               help="Mediawiki main version, e.g. '44'")
    p.add_argument("-p", "--minor_release", type=str, default="3",
               help="Mediawiki patch release, e.g. '3'")
    args = p.parse_args()

    archive, path = get_mediawiki_release(
        major_release=args.major_release,
        minor_release=args.minor_release,
        target_folder=args.target_folder
    )
    print("Downloaded:", archive)
    print("Extracted to:", path)

if __name__ == "__main__":
    main()

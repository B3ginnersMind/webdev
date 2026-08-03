"""
Download and extract a MediaWiki release archive.
"""
import logging, os, socket, tarfile
import urllib.request, gzip, zlib
from pathlib import Path
from urllib.error import HTTPError, URLError
import mu.utils as utils
from mu.dataclasses import UpdateData
import mu.constants as const

def is_valid_targz(filepath: Path | str) -> bool:
    """
    Prüft, ob ein .tar.gz Archiv valide und vollständig ist.
    """
    try:
        # "r:gz" weist tarfile an, das Archiv als gzip-komprimiert zu behandeln
        with tarfile.open(filepath, "r:gz") as tar:
            # getmembers() liest die Metadaten aller Dateien im Archiv.
            # Fehlt das korrekte Dateiende (EOF) durch einen abgebrochenen Download,
            # wird hier eine Exception geworfen.
            tar.getmembers()
            
        return True
        
    except EOFError:
        # Typischer Fehler, wenn der Download mittendrin abriss
        return False
    except tarfile.ReadError:
        # Das Archiv ist kein gültiges Tar-Archiv oder stark beschädigt
        return False
    except (gzip.BadGzipFile, zlib.error):
        # Fehler in der Gzip-Kompressionsebene
        return False
    except Exception as e:
        print("Unexpected Exception:", type(e).__name__) 
        # Genereller Fallback für unerwartete I/O-Fehler
        return False

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
        with urllib.request.urlopen(req, timeout=90) as response, \
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
        # Prüfung: War die Ursache für den URLError ein Timeout beim Verbindungsaufbau?
        if isinstance(e.reason, (TimeoutError, socket.timeout)):
            raise RuntimeError(
                f"Timeout beim Verbindungsaufbau zu {url}"
            ) from e
            
        raise RuntimeError(
            f"Netzwerkfehler beim Download von {url}: {e.reason}"
        ) from e
        
    except (TimeoutError, socket.timeout) as e:
        # Wird geworfen, wenn der Timeout WÄHREND des Lesens (response.read) auftritt
        raise RuntimeError(
            f"Timeout während der Datenübertragung von {url}"
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
    filename = str(f"mediawiki-{d.release_new}.tar.gz")
    logging.info(f"Requested Mediawiki archive: {filename}")
    url = (
        f"{const.MEDIAWIKI_RELEASE_BASE_URL}1.{d.release_new.major}/{filename}"
    )

    target_folder = d.mw_basefolder_new
    os.makedirs(target_folder, exist_ok=True)
    archive_path: Path = target_folder / filename
    valid_archive_already_exists = False
    if archive_path.is_file():
        if is_valid_targz(archive_path):
            logging.warning("Archive file already exists, keep it")
            valid_archive_already_exists = True
        else:
            logging.warning("Existing archive file corrupted, remove it")
            valid_archive_already_exists = False
            archive_path.unlink()
    if not valid_archive_already_exists:
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

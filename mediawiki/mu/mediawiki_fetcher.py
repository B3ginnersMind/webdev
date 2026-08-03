"""
Download and extract a MediaWiki release archive.
"""
import datetime, logging, os, socket, tarfile, time
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
            # Fehlt das korrekte Dateiende (EOF) durch einen abgebrochenen
            # Download, wird hier eine Exception geworfen.
            tar.getmembers()
        return True
        
    except EOFError:
        logging.error(f"Archive with: EOFError")
        return False
    except tarfile.ReadError:
        logging.error(f"Archive with: tarfile.ReadError")
        return False
    except (gzip.BadGzipFile, zlib.error):
        logging.error(f"Archive with: (gzip.BadGzipFile, zlib.error")
        return False
    except Exception as e:
        logging.error(f"Archive with unknown Exception: {type(e).__name__}")
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
        with urllib.request.urlopen(req, timeout=180) as response, \
                                    open(target_path, "wb") as out:
            # Stream download (memory-saving)
            block_size = 1024 * 64  # 64 KB
            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                out.write(chunk)

    except HTTPError as e:
        raise RuntimeError(f"HTTP-Fehler {e.code} beim Download von {url}") from e
    except URLError as e:
        # Prüfung: War die Ursache für den URLError ein Timeout beim Verbindungsaufbau?
        if isinstance(e.reason, (TimeoutError, socket.timeout)):
            raise RuntimeError(f"Timeout beim Verbindungsaufbau zu {url}") from e
        raise RuntimeError(f"Netzwerkfehler beim Download von {url}: {e.reason}") from e
    except (TimeoutError, socket.timeout) as e:
        # Wird geworfen, wenn der Timeout WÄHREND des Lesens (response.read) auftritt
        raise RuntimeError(
            f"Timeout während der Datenübertragung von {url}"
        ) from e

def download_mediawiki_archive_robust(url: str, target_path: Path, max_retries: int = 5) -> None:
    logging.info(f"Downloading from: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) MediaWiki-updater/1.0",
        "Accept": "*/*",
        "Connection": "keep-alive",
    }
    
    retries = 0
    while retries < max_retries:
        # Prüfen, wie viel bereits heruntergeladen wurde
        current_size = target_path.stat().st_size if target_path.exists() else 0
        
        req = urllib.request.Request(url, headers=headers)
        
        # Wenn wir schon Daten haben, fordern wir nur den Rest an (Resume)
        if current_size > 0:
            req.add_header("Range", f"bytes={current_size}-")
            logging.info(f"Setze Download fort ab Byte {current_size}...")

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                # Gesamtgröße der Datei bestimmen (nur beim ersten Versuch möglich/nötig)
                expected_length = response.getheader('Content-Length')
                
                # Wenn es ein Resume ist (HTTP 206), müssen wir die Größen addieren
                if response.status == 206 and expected_length:
                    total_size = current_size + int(expected_length)
                elif expected_length:
                    total_size = int(expected_length)
                else:
                    total_size = None # Server sendet keine Länge mit

                # Datei öffnen (anhängen, wenn wir fortsetzen, sonst neu schreiben)
                mode = "ab" if current_size > 0 else "wb"
                with open(target_path, mode) as out:
                    block_size = 1024 * 64
                    while True:
                        chunk = response.read(block_size)
                        if not chunk:
                            break
                        out.write(chunk)
                
                # Nach der Schleife: Prüfen, ob wir wirklich alles haben
                final_size = target_path.stat().st_size
                if total_size and final_size < total_size:
                    logging.warning(f"Download vorzeitig vom Server beendet ({final_size}/{total_size} Bytes). Starte neuen Versuch...")
                    retries += 1
                    time.sleep(2) # Kurze Pause vor dem Reconnect
                    continue # Nächster Versuch in der while-Schleife
                    
                # Wenn wir hier ankommen, ist die Datei komplett
                logging.info("Download erfolgreich abgeschlossen.")
                return

        except HTTPError as e:
            # HTTP 416 bedeutet "Requested Range Not Satisfiable" (Datei ist schon komplett fertig)
            if e.code == 416:
                logging.info("Download war bereits vollständig.")
                return
            raise RuntimeError(f"HTTP-Fehler {e.code} beim Download") from e
            
        except (URLError, TimeoutError, ConnectionResetError) as e:
            logging.warning(f"Netzwerkfehler: {e}. Versuche es erneut...")
            retries += 1
            time.sleep(2)

    raise RuntimeError(f"Download nach {max_retries} Versuchen fehlgeschlagen.")

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
        start_time = datetime.datetime.now()
        # download_mediawiki_archive(url, archive_path)
        download_mediawiki_archive_robust(url, archive_path)
        end_time = datetime.datetime.now()
        elapsed_time = str((end_time - start_time).total_seconds())
        logging.info(f"Time elapsed during the download: {elapsed_time} sec")
    if not archive_path.is_file():
        logging.error("Downloaded archive file missing. Exit.")
        raise RuntimeError(
            f"Error: Missing archive file download: {archive_path}"
        )
    if not is_valid_targz(archive_path):
        logging.error("Downloaded archive corrupted. Exit.")
        raise RuntimeError(
            f"Error: Corrupted archive file download: {archive_path}"
        )

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


import configparser, logging, shutil, zipfile
import helper.constants as const
from pathlib import PurePosixPath, Path
from helper.dataclasses import Release, UpdateData

def read_config(config_path: Path, section: str = "settings") -> UpdateData:
    """
    Read input data from the config file. This is an example config:

    # comment about the config
    [settings]
    mw_folder_live = "/var/www/newhomoeopedia"
    mw_basefolder_new = "/home/koerkel/cms/mediawiki"
    release_new = "1.45.1"
    """
    logging.info(f"Reading configuration from: {config_path}")
    logging.info(f"Configuration section: {section}")
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    config = configparser.ConfigParser()
    config.read(config_path)
    data: UpdateData = UpdateData()
    data.mw_folder_live = Path(config.get("settings", "mw_folder_live", fallback=""))
    data.mw_basefolder_new = Path(config.get("settings", "mw_basefolder_new", fallback=""))
    data.release_new = Release(config.get("settings", "release_new", fallback=""))
    return data

def remtree(path: Path) -> None:
    """Recursively remove a directory tree."""
    if path.is_dir():
        logging.warning(f"Removing already existing folder: {path}")
        shutil.rmtree(str(path))
    elif path.is_file():
        raise RuntimeError(f"Expected directory but found file: {path}")

def get_zip_root_folder(zip_path: str) -> str:
    """
    Returns the root directory name of a ZIP file that contains
    exactly one top-level directory tree.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        roots = set()

        for name in zf.namelist():
            # Ignore empty entries
            if not name.strip():
                continue

            parts = PurePosixPath(name).parts
            if parts:
                roots.add(parts[0])

        if len(roots) != 1:
            raise ValueError(
                f"ZIP does not contain exactly one root directory: {roots}"
            )

        return roots.pop()

def copy_live_site_data(src_dir: Path, dst_dir: Path) -> None:
    """
    Copies .htaccess from src_dir to dst_dir.
    Colpied LocalSettings.php from src_dir to dst_dir.
    Copies all picture files from src_dir to dst_dir (no subfolders).
    Copies src_dir/images to dst_dir/images.
    """
    logging.info(const.SHORT_LINE + f" copy_live_site_data:")
    logging.info(f"Source directory: {src_dir}")
    logging.info(f"Destination directory: {dst_dir}")

    IMAGE_EXTENSIONS = {
        ".jpg", ".jpeg", ".png", ".gif",
        ".bmp", ".tiff", ".tif", ".webp"
    }
    dst_dir.mkdir(parents=True, exist_ok=True)
    for src_path in src_dir.iterdir():
        if not src_path.is_file():
            continue
        if src_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        logging.info(f"Copying image file: {src_path.name}")
        dst_path = dst_dir / src_path.name
        shutil.copy2(src_path, dst_path)
    
    logging.info("Copying .htaccess and LocalSettings.php")
    shutil.copy2(src_dir / ".htaccess", dst_dir / ".htaccess")
    shutil.copy2(src_dir / "LocalSettings.php", dst_dir / "LocalSettings.php")

    src_images_dir = src_dir / "images"
    dst_images_dir = dst_dir / "images"
    remtree(dst_images_dir)
    logging.info(f"Copying images folder from: {src_images_dir}")
    logging.info(f"To: {dst_images_dir}")
    shutil.copytree(src_images_dir, dst_images_dir)
    logging.info(const.LONG_LINE)


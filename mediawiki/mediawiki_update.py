import logging
import argparse, logging, os
from pathlib import Path
from helper.mediawiki_fetcher import get_mediawiki_release
from pathlib import Path
from helper.dataclasses import Release

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("mediawiki_update.log"),
        logging.StreamHandler()
    ]
)

def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        # formatter used to preserve the raw doc format
        formatter_class=argparse.RawTextHelpFormatter
        )
    
    p.add_argument("-f", "--target_folder", type=str, default="~/cms/mediawiki",
               help="folder to download the release archive into")
    p.add_argument("-m", "--release", type=str, default="1.44.3",
               help="Mediawiki main version, e.g. '1.44.3'")
    args = p.parse_args()

    rel = Release(args.release)
    target = Path(os.path.expanduser(args.target_folder))

    logging.info("Starting Mediawiki update")

    # archive, path = get_mediawiki_release(release=rel, 
    #                                       target_folder=target)
    # print("Downloaded:", archive)
    # print("Extracted to:", path)

if __name__ == "__main__":
    main()

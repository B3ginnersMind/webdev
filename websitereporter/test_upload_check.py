#!/usr/bin/env python
"""
--------------------------------------------------------------------------------
test upload_checks
--------------------------------------------------------------------------------
"""
import argparse, os, platform, time
from pathlib import Path
from wr.config import read_config, settings
import wr.utils as u
from wr.upload_check import upload_checks
from wr.upload_check import AppMode
__version__ = "1.0.0"

if platform.system() != 'Linux':
    print(f"Skript does only support Linux. Exiting...")
    quit()

currenttime = time.strftime('%d.%m.%Y %H:%M')
script_name = os.path.basename(__file__)

p = argparse.ArgumentParser(
    description=__doc__,
    # formatter used to preserve the raw doc format
    formatter_class=argparse.RawTextHelpFormatter
    )
p.add_argument("--accept", action="store_true",
                help="accept all found files as benign")
p.add_argument("-v", "--version", action='version', 
                version='%(prog)s version {version}'.format(version=__version__))
p.add_argument("website", nargs='?', type=str, default='none',
               help="the only website document root to be analysed")
args = p.parse_args()

read_config(Path(__file__).parent / "website_reporter_config.ini")
settings.show()
if settings.run_as_root and os.getuid() != 0: # type: ignore
    print(f"Skript not run as root. Exiting...")
    quit()

print('=== Generate reports on active virtual hosts ===')
print('This is Python script', script_name, 'version', __version__)
print('Query time:', currenttime)

u.print_double_line()
if args.website != 'none':
    doc_root: list[Path] = [Path(args.website)]
    cms: u.CmsPaths = u.detect_cms(doc_root)
elif len(settings.web_roots) > 0:
    cms: u.CmsPaths = u.detect_cms(settings.web_roots)
else:
    # doc_roots: list[Path] = u.get_subdirectories(Path("/var/www"))
    doc_roots: list[Path] = u.get_document_roots("/etc/apache2/sites-enabled")
    cms: u.CmsPaths = u.detect_cms(doc_roots)

if args.accept:
    upload_checks(AppMode.ACCEPT_MODE, cms)
else:
    upload_checks(AppMode.TEST_MODE, cms)
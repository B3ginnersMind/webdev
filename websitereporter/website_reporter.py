#!/usr/bin/env python
"""
--------------------------------------------------------------------------------
Generate reports on the virtual hosts installed in the web root directories.
The document roots are taken from the Apache vhost config files.
Without any arguments, the script will only list all detected vhost types.
Detectable vhost types are Joomla, MediaWiki, WordPress, Drupal and static sites.

Setting are read from file "website_reporter_config.ini" which has to be in the 
same directory as this script. If this file is missing, the default settings are
used. See "demo_website_reporter_config.ini" for the default settings.
"""
import argparse, os, platform, time
from pathlib import Path
from wr.config import read_config, settings
import wr.utils as u
import wr.joomla as j
import wr.mediawiki as m
import wr.wordpress as w
import wr.drupal as d
__version__ = "1.2.0"

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
p.add_argument("-j", "--joomla", action="store_true",
                help="check Joomla sites")
p.add_argument("-m", "--mediawiki", action="store_true",
                help="check MediaWiki sites")
p.add_argument("-w", "--wordpress", action="store_true",
                help="check WordPress sites")
p.add_argument("-d", "--drupal", action="store_true",
                help="check Drupal sites")
p.add_argument("-u", "--users", action="store_true",
                help="output CMS user lists")
p.add_argument("-v", "--version", action='version', 
                version='%(prog)s version {version}'.format(version=__version__))
p.add_argument("website", nargs='?', type=str, default='none',
               help="the only website document root to be analysed")
args = p.parse_args()

read_config(Path(__file__).parent / "website_reporter_config.ini")
if args.users:
    settings.show_cms_users = True
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
    args.joomla = True
    args.mediawiki = True
    args.wordpress = True
    args.drupal = True
elif len(settings.web_roots) > 0:
    cms: u.CmsPaths = u.detect_cms(settings.web_roots)
else:
    # doc_roots: list[Path] = u.get_subdirectories(Path("/var/www"))
    doc_roots: list[Path] = u.get_document_roots("/etc/apache2/sites-enabled")
    cms: u.CmsPaths = u.detect_cms(doc_roots)

if args.joomla and cms.joomla_sites:
    j.check_joomla_sites(cms)
if args.mediawiki and cms.mediawiki_sites:
    m.check_mediawiki_sites(cms)
if args.wordpress and cms.wordpress_sites:
    w.check_wordpress_sites(cms)
if args.drupal and cms.drupal_sites:
    d.check_drupal_sites(cms)
# u.check_static_sites(cms)

#!/usr/bin/env python
"""
--------------------------------------------------------------------------------
Generate reports on the virtual hosts installed in the web root directory.
The document roots are taken from the Apache vhost config files.
Without any arguments, the script will only list all detected vhost types.
Detectable vhost types are Joomla, MediaWiki, WordPress, Drupal and static sites.
"""
import argparse, os, platform
from pathlib import Path
import wr.utils as u
import wr.joomla as j
import wr.mediawiki as m
import wr.wordpress as w
import wr.drupal as d
__version__ = "1.0.2"

if platform.system() != 'Linux':
    print(f"Skript does only support Linux. Exiting...")
    quit()
if os.getuid() != 0: # type: ignore
    print(f"Skript not run as root. Exiting...")
    quit()

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
p.add_argument("-v", "--version", action='version', 
                version='%(prog)s version {version}'.format(version=__version__))
args = p.parse_args()

u.print_double_line()
doc_roots: list[Path] = u.get_document_roots("/etc/apache2/sites-enabled")
# doc_roots: list[Path] = u.get_subdirectories(Path("/var/www"))
cms: u.CmsLists = u.detect_cms(doc_roots)
if args.joomla:
    j.check_joomla_sites(cms)
if args.mediawiki:
    m.check_mediawiki_sites(cms)
if args.wordpress:
    w.check_wordpress_sites(cms)
if args.drupal:
    d.check_drupal_sites(cms)
# u.check_static_sites(cms)

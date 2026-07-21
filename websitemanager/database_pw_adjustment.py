#!/usr/bin/env python
"""
--------------------------------------------------------------------
Read and adjust database passwords of websites which use a database.
New passwords (if any) are taken from the file website_table.txt.
Possible for CMS Joomla, Mediawiki and WordPress.
Without options nothing is changed, only checked. 
If the option --change is set, the passwords are adjusted in the 
configuration files and in the database.
--------------------------------------------------------------------
"""

import argparse, os
import wm.utils as u
import wm.cms_configs as cfg
from wm.websites import WebSiteTable
from wm.config import Parameters
__version__ = "1.1.0"

p = argparse.ArgumentParser(description=__doc__,
               # formatter used to preserve the raw doc format
               formatter_class=argparse.RawTextHelpFormatter)

p.add_argument("-v", "--version", action='version', 
               version='%(prog)s version {version}'.format(version=__version__))
p.add_argument('-c', '--change', action="store_true", 
               help='not only check but also adjust non-matching database passwords')
p.add_argument("siteName", nargs='?', type=str, default='none',
               help="site name which is treated exclusively, otherwise all are treated.")
args = p.parse_args()

if args.change:
    u.check_root_user()

script_folder = os.path.dirname(os.path.realpath(__file__))
paramsfile = script_folder + '/website_manager_config.ini'
u.is_file_or_abort(paramsfile)
websitesfile = script_folder + '/website_table.txt'
u.is_file_or_abort(websitesfile)

siteName = args.siteName

# ensure that working dir is the source dir
os.chdir(script_folder)
u.print_line()
print('Current working directory:', os. getcwd())
# create congiguration table objects
websites = WebSiteTable(websitesfile)
numSites = websites.getNumWebsites()

params = Parameters(paramsfile)
if params.get('runasroot') == 'true':
    u.check_root_user()

if siteName != 'none' and not websites.hasSite(siteName):
    print('Entered "' + siteName + '" not present in website table', websitesfile)
    u.abort("Retry with existing siteName.")

ok = cfg.check_user_password_consistency(websites, siteName)
if not ok:
    u.abort("A problem with te website table occurred")

if siteName == 'none':
    websites.show()
    for row in range(numSites):
        site = websites.getData(row)
        cfg.process_dbpassword(params, site, change=args.change)
        print()
else:
    site = websites.getSite(siteName)
    cfg.process_dbpassword(params, site, change=args.change)
    print()

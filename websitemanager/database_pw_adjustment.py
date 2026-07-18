#!/usr/bin/env python
"""
-----------------------------------------------------------------
read and adjust database passwords of websites which use a database.
"""

import argparse, os
# from wm.backup import get_archive_dir, backup, dumpwebsite
# from wm.restore import prepare_database, get_archive_timestamp, restore

import wm.utils as u
import wm.cms_configs as cfg
from wm.websites import WebSiteTable
from wm.config import Parameters
__version__ = "1.0.0"

p = argparse.ArgumentParser(description=__doc__,
               # formatter used to preserve the raw doc format
               formatter_class=argparse.RawTextHelpFormatter)

# g = p.add_mutually_exclusive_group()
# g.add_argument("-a", "--saveall", help="batch backup of all websites", 
#                action="store_true")

p.add_argument("-v", "--version", action='version', 
               version='%(prog)s version {version}'.format(version=__version__))
p.add_argument('-c', '--check', action="store_true", 
               help='only check if database passwords are correct in CMS config files')
p.add_argument("siteName", nargs='?', type=str, default='none',
               help="site name which is treated exclusively")
args = p.parse_args()

if not args.check:
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
        cfg.process_dbpassword(params, site, checkOnly=args.check)
        print()
else:
    site = websites.getSite(siteName)
    cfg.process_dbpassword(params, site, checkOnly=args.check)
    print()

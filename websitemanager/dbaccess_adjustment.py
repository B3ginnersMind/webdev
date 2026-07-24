#!/usr/bin/env python
"""
-------------------------------------------------------------------------------
Read, compare and, optionally, adjust database credentials of CMS websites.

The credentials in the file website_table.txt are compared to the corresponding
values in the config file of the CMS. This is possible for
- Joomla, 
- Mediawiki, 
- WordPress.
Without options nothing is changed, only differences are reported.
If the option --change is set, the credendials within the configuration files
are adjusted to the values in the website table.
-------------------------------------------------------------------------------
"""
import argparse, os
import wm.utils as u
import wm.dbaccess as acc
from wm.dbaccess import Options
from wm.websites import WebSiteTable
from wm.config import Parameters
__version__ = "1.0.0"

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

options = Options()
options.adjust = args.change

u.print_line()
print("Database access adjustment program version", __version__)
if options.adjust:
    print("Database access will be adjusted in configuration files.")
else:
    print("Only check database access, no changes will be made.")

script_folder = os.path.dirname(os.path.realpath(__file__))
paramsfile = script_folder + '/website_manager_config.ini'
u.is_file_or_abort(paramsfile)
websitesfile = script_folder + '/website_table.txt'
u.is_file_or_abort(websitesfile)

singleSiteNameTreated = args.siteName

# ensure that working dir is the source dir
os.chdir(script_folder)
print('Current working directory:', os. getcwd())
# create congiguration table objects
websites = WebSiteTable(websitesfile)
numSites = websites.getNumWebsites()

params = Parameters(paramsfile)
if params.get('runasroot') == 'true':
    u.check_root_user()

if singleSiteNameTreated != 'none' and not websites.hasSite(singleSiteNameTreated):
    print('Entered "' + singleSiteNameTreated + '" not present in website table', websitesfile)
    u.abort("Retry with existing siteName.")

if singleSiteNameTreated == 'none':
    # Treat all websites in the website table.
    websites.show()
    for row in range(numSites):
        site = websites.getData(row)
        acc.adjust_config_after_restore(params, site, options)
        print()
else:
    # Only treat the entered website in the argument.
    site = websites.getSite(singleSiteNameTreated)
    acc.adjust_config_after_restore(params, site, options)
    print()

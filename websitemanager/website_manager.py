#!/usr/bin/env python
# Note:  "!/usr/bin/env python3" does not work on Windows!
"""
-----------------------------------------------------------------
Manage backup and recovery of websites which use a database.
Each website backup is stored in a zipped archive.
Both the SQL dump and all the web files are saved.
Tested with MySQL 8 and MariaDB 15.

The following features are supported:
- saveall: bulk backup of the sites in the website table
- snapshot: save only one website
- replace: recover one website from a backup archive
- replace after snapshot: take a snapshot first, then recover
- prepare database: add missing database and DB user of a website

There must be two files which contain tables separated by spaces
in the same directory as this script:
website_manager_params.txt - contains configuration parameters
website_table.txt          - contains the data for each website

- Without argument the interactive mode is entered.
  Website recovery is only possible in the interactive mode.
- Use the saveall option to run an autosave batch over all sites.
  Autosave mode overwrites older archives from the same day.
  Backups are stored in the directory specified by the sitedumpdir parameter.
- Use the spapshot option to create a time-stamped backup of a website
  which must be specified by its identifier in the website table.
  Backups are stored in the directory specified by the snapshotdir parameter.
"""

import argparse, glob, os, textwrap
from pathlib import Path
from wm.website_manager_worker import backup, dumpwebsite, restore, prepare_database
# Table processing in website_manager_utils by module pandas.
import wm.website_manager_utils as u
from wm.website_manager_utils import Parameters, WebSiteTable, WebSiteData
__version__ = "1.0"

WRAP_LENGTH = 65
# Modes of operation:
UNKNOWN = 0
BATCH_SAVEALL = -1
SAVEALL = 1
SNAPSHOT = 2
REPLACE_AFTER_SNAPSHOT = 3
REPLACE = 4
DBEXIST = 5
# specify configuration files
script_folder = os.path.dirname(os.path.realpath(__file__))
websitesfile = script_folder + '/website_table.txt'
paramsfile = script_folder + '/website_manager_params.txt'

p = argparse.ArgumentParser(description=__doc__,
               # formatter used to preserve the raw doc format
               formatter_class=argparse.RawDescriptionHelpFormatter)
g = p.add_mutually_exclusive_group()
g.add_argument("-a", "--saveall", help="batch backup of all websites", 
               action="store_true")
g.add_argument("-s", "--spapshot", help="make a time-stamped snapshot", 
               action="store_true")
p.add_argument("siteName", nargs='?', default='none', type=str,
               help="site name of a single treated website")
p.add_argument("-v", "--version", action='version', 
               version='%(prog)s version {version}'.format(version=__version__))
args = p.parse_args()

mode = UNKNOWN
if args.saveall:
    mode = BATCH_SAVEALL
elif args.spapshot:
    mode = SNAPSHOT

# ensure that working dir is the source dir
source_path = Path(__file__).resolve()
source_dir = source_path.parent
os.chdir(source_dir)
u.print_line()
print('Current working directory:', os. getcwd())
# create congiguration table objects
websites = WebSiteTable(websitesfile)
numSites = websites.getNumWebsites()

params = Parameters(paramsfile)
if params.get('runasroot') != 'false':
    u.check_root_user()

if mode == UNKNOWN:
    print('Select task:')
    print(UNKNOWN, ': abort')
    print(SAVEALL, ': saveall')
    print(SNAPSHOT, ': snapshot')
    print(REPLACE_AFTER_SNAPSHOT, ': replace after snapshot')
    print(REPLACE, ': replace')
    print(DBEXIST, ': prepare database')
    mode = u.query_int('Enter digit', SAVEALL, DBEXIST)
    if mode == SAVEALL:
        u.print_line()
        websites.show()
        print('=> Entering saveall mode...')
        print('Note: Older archives from this day will be overwritten.')
        u.query_continue()

if mode == UNKNOWN:
    quit()

if mode in [SAVEALL, BATCH_SAVEALL]:
    for row in range(numSites):
        dumpwebsite(params, websites.getData(row))
    quit()

siteName = args.siteName
if siteName != 'none' and not websites.hasSite(siteName):
    print('Entered', siteName, 'not present in website table', websitesfile)
    siteName = 'none'
if siteName == 'none':
    u.print_line()
    websites.show()
    row = u.query_int('Enter row number of treated website', 0, numSites-1)
    s = websites.getData(row)
    siteName = s.siteName
site = websites.getSite(siteName)
print('=> Treated website:', site.siteName, '"' + site.comment + '"')

if mode in [SNAPSHOT, REPLACE_AFTER_SNAPSHOT]:
    u.print_line()
    print('=> Create snapshot of', site.siteName)
    dailydump = False
    backup(params, site, dailydump)

if mode in [REPLACE_AFTER_SNAPSHOT, REPLACE]:
    u.print_line()
    print('=> Replace content of website', site.siteName)
    
    # "root_dir=DIRECTORY_PATH" is not yet in glob with Python 3.8:
    cwd = os.getcwd()
    os.chdir(params.get('sitedumpdir'))
    sitedumps = glob.glob(site.siteName + '*tar.gz')
    os.chdir(params.get('snapshotdir'))
    snapshots = glob.glob(site.siteName + '*tar.gz')
    os.chdir(cwd)
    print('Present sitedumps:', textwrap.fill(" ".join(sitedumps), WRAP_LENGTH))
    print('Present snapshots:', textwrap.fill(" ".join(snapshots), WRAP_LENGTH))
    
    print('Snapshot timestamp has format YYYY-MM-DD_hh-mm')
    print('Sitedump timestamp has format wd#, w# or m# where # is integer')
    timestamp = input('Enter timestamp of "' + site.siteName 
                      + '" archive to be restored: ')
    if timestamp == '' or ' ' in timestamp or timestamp.isspace():
        print('Timestamp may not contain whitespace.')
        u.abort('invalid timestamp entered')
    print('Try restoring from archive', site.siteName + '.' + timestamp + '.tar.gz')
    restore(params, site, timestamp)
    
if mode == DBEXIST:
    prepare_database(params, site)

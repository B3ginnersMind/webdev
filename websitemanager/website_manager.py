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

In the same directory as this script, there must be two files 
containing tables with columns separated by spaces:
website_manager_params.txt - contains configuration parameters
website_table.txt          - contains the data for each website

- Without argument the interactive mode is entered.
- Use the saveall option to run an autosave batch over all sites.
  Autosave mode overwrites older archives from the same day.
  Backups are stored in the directory specified by the sitedumpdir parameter.
  No other arguments are allowed when the saveall option is entered.
- Use the snapshot option to create a time-stamped backup of just one website
  which must have been specified by its identifier in the website table.
  The default storage location of the backups is configured in the parameter file.
- A website to treat can be selected interactively or entered as the first 
  positional argument. An alternative location for snapshots can be specified 
  as the second positional argument.
- Single website actions are logged in a folder specified in the parameter file.
"""

import argparse, os
from wm.website_manager_worker import backup, dumpwebsite, restore, prepare_database
from wm.website_manager_worker import get_archive_timestamp, get_archive_dir
# Table processing in website_manager_utils by module pandas.
import wm.website_manager_utils as u
from wm.website_manager_utils import Operation, Parameters, WebSiteTable
__version__ = "1.2"

p = argparse.ArgumentParser(description=__doc__,
               # formatter used to preserve the raw doc format
               formatter_class=argparse.RawDescriptionHelpFormatter)

g = p.add_mutually_exclusive_group()
g.add_argument("-a", "--saveall", help="batch backup of all websites", 
               action="store_true")
g.add_argument("-s", "--snapshot", help="make a time-stamped snapshot", 
               action="store_true")
g.add_argument("-r", "--replace", help="recover website from backup archive", 
               action="store_true")
g.add_argument("-b", "--back", help="recover after having made a snapshot", 
               action="store_true")
g.add_argument("-p", "--prepare", help="prepare database", 
               action="store_true")

p.add_argument('-c', '--config', type=str, help='enter alternative parameter file name')
p.add_argument('-w', '--websites', type=str, help='enter alternative websites file name')
p.add_argument("siteName", nargs='?', type=str, default='none',
               help="site name which is treated")
p.add_argument("altDir", nargs='?', type=str, default='none',
               help="alternative path for snapshots")
p.add_argument("-v", "--version", action='version', 
               version='%(prog)s version {version}'.format(version=__version__))
args = p.parse_args()

script_folder = os.path.dirname(os.path.realpath(__file__))
paramsfile = script_folder + '/website_manager_params.txt'
if (args.config):
    paramsfile = script_folder + '/' + args.config
u.is_file_or_abort(paramsfile)
websitesfile = script_folder + '/website_table.txt'
if (args.websites):
    websitesfile = script_folder + '/' + args.websites
u.is_file_or_abort(websitesfile)

siteName = args.siteName
mode = Operation.UNKNOWN
if args.saveall:
    mode = Operation.BATCH_SAVEALL
    if siteName != 'none':
        u.abort('Site name argument prohibited for saveall mode')
elif args.snapshot:
    mode = Operation.SNAPSHOT
elif args.replace:
    mode = Operation.REPLACE
elif args.back:
    mode = Operation.REPLACE_AFTER_SNAPSHOT
elif args.prepare:
    mode = Operation.DBEXIST

altDir = args.altDir
if altDir != "none":    
    u.is_dir_or_abort(altDir)

# ensure that working dir is the source dir
os.chdir(script_folder)
u.print_line()
print('Current working directory:', os. getcwd())
# create congiguration table objects
websites = WebSiteTable(websitesfile)
numSites = websites.getNumWebsites()

params = Parameters(paramsfile)
if params.get('runasroot') != 'false':
    u.check_root_user()

if mode == Operation.UNKNOWN:
    print('Select task:')
    print(Operation.UNKNOWN.value, ': abort')
    print(Operation.SAVEALL.value, ': saveall')
    print(Operation.SNAPSHOT.value, ': snapshot')
    print(Operation.REPLACE_AFTER_SNAPSHOT.value, ': replace after snapshot')
    print(Operation.REPLACE.value, ': replace')
    print(Operation.DBEXIST.value, ': prepare database')
    m = u.query_int('Enter digit', mode.min(), mode.max())
    mode = Operation(m)
    if mode == Operation.SAVEALL:
        u.print_line()
        websites.show()
        print('=> Entering saveall mode...')
        print('Note: Older archives from this day will be overwritten.')
        u.query_continue()

if mode == Operation.UNKNOWN:
    quit()

if mode.isSaveall():
    for row in range(numSites):
        dumpwebsite(params, websites.getData(row))
    quit()

if siteName != 'none' and not websites.hasSite(siteName):
    print('Entered "' + siteName + '" not present in website table', websitesfile)
    u.abort("Retry with existing siteName or use interactive mode.")

if siteName == 'none':
    u.print_line()
    websites.show()
    row = u.query_int('Enter row number of treated website', 0, numSites-1)
    s = websites.getData(row)
    siteName = s.siteName
site = websites.getSite(siteName)
print('=> Treated website:', site.siteName, '"' + site.comment + '"')

if mode.isSnapshot():
    u.print_line()
    print('=> Create snapshot of', site.siteName)
    dailydump = False
    backup(params, site, dailydump, altDir)

if mode.isReplace():
    u.print_line()
    print('=> Replace content of website', site.siteName)
    timestamp = get_archive_timestamp(params, site, altDir)
    backupDir = get_archive_dir(params, timestamp, altDir)
    restore(params, site, timestamp, backupDir)
    
if mode == Operation.DBEXIST:
    prepare_database(params, site)

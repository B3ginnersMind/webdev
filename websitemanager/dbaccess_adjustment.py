#!/usr/bin/env python
"""
-------------------------------------------------------------------------------
Read, compare and, optionally, adjust database credentials for CMS websites.

The current database credentials for each website are taken from the  
website_table.txt file. These credentials are then used to test
- whether access to the corresponding database ist possible and
- whether they match the corresponding credentials in the CMS config.
Without options nothing is changed; only problems are reported.
If the option --change is set, the credentials within the database software
and the configuration files are updated to match the values in the website table.
In the database software only the passowrd of a database user can be updated.
In a configfile the database name, user, password and host can be adjusted.
This feature is available for the CMS
- Joomla, 
- Mediawiki and 
- WordPress.
-------------------------------------------------------------------------------
"""
import argparse, os
import wm.utils as u
import wm.dbaccess as acc
from wm.dbaccess import Options
from wm.websites import WebSiteTable, WebSiteData
from wm.config import Parameters
__version__ = "1.1.0"

def process_dbaccess(params: Parameters, site: WebSiteData, options: Options) -> None:
    if options.adjust:
        acc.adjust_dbaccess(params, site)
    else:
        acc.test_dbaccess(params, site)

def main():
    p = argparse.ArgumentParser(description=__doc__,
                # formatter used to preserve the raw doc format
                formatter_class=argparse.RawTextHelpFormatter)

    p.add_argument("-v", "--version", action='version', 
                version='%(prog)s version {version}'.format(version=__version__))
    p.add_argument('-c', '--change', action="store_true", 
                help='not only check but also adjust non-matching database credentials')
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
        print("Only check database access data, no changes will be made.")

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
            process_dbaccess(params, site, options)
            print()
    else:
        # Only treat the entered website in the argument.
        site = websites.getSite(singleSiteNameTreated)
        process_dbaccess(params, site, options)
        print()

if __name__ == "__main__":
    main()

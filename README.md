# webdev

## Installation

Simple Python tools for managing websites. Tested with Python 3.10.12.

### Manual installation

Download a zip file of the latest version from https://github.com/B3ginnersMind/webdev/zipball/main/

Download and unzip this zip file e.g. from a console using curl (use curl.exe in Powershell):

    curl -L -o webdev.zip https://github.com/B3ginnersMind/webdev/zipball/main/
    unzip webdev.zip

Go to the newly created subfolder *B3ginnersMind-webdev-xxxxxx* where xxxxxx is the tag of the downloaded revision. Copy the content to the desired location.

### Script supported installation

This is especially useful if you want to update webdev. Get the download script:

    curl -LJO https://raw.githubusercontent.com/B3ginnersMind/webdev/main/download_webdev.py

This script requires the Python "requests" package to perform the download. 

- Run *download_webdev.py*.
- The archive is then downloaded and unzipped.
- You will be asked whether you want to run the install script.
- If you run the install script, only the python files will be updated.
- This means that the readme and the sample files will not be copied.
- You can run *install_webdev.py* any time when you want to copy the python files again.

## website_manager.py in folder websitemanager

- Requires the pandas package to read ASCII tables.
- Manage backup and recovery of websites which use a database
  such as Wordpress, Joomla, Mediawiki, Drupal etc.
- Add a missing database and a missing database user to install 
  a new content management system.
- Show help with option -h and version with -v.
- Website backups are saved in zipped archives.
- Bulk backup and single snapshots are supported.
- Both automatic and interactive modes are supported.
- Two configuration files must be present in the same directory
  as website_manager.py:
  + *website_manager_params.txt* with the script configurations.
  + *website_table.txt* with the data of the managed websites.
- Copy and rename *demo_website_manager_params.txt* and 
  *demo_website_table.txt* to create your own configuration.
  These demo files contain further documentation.
- Website manager has been successfully applied with 
  MySQL 8 and MariaDB 15.

The following features are supported:

- saveall: bulk backup of the sites in the website table
- snapshot: save only one website
- replace: recover one website from a backup archive
- replace after snapshot: take a snapshot first, then recover
- prepare database: only prepare the database for a website

Snapshots are time stamped. Bulk backups are kept daily for a week,
weekly for a month, and monthly for a year. They are labeled with
wd#, w# and m# where # is an integer, wd denotes weekday, w denotes
week and m denotes month. Bulk backups are intended to be run as 
nightly cronjobs.

### Version 1.0

Initial version

### Version 1.1

- Treated website may be entered by argument for all modes dealing with a single website.
- An alternative folder path for snapshots may be entered.
- Improved output of available backup archives in the restore mode.
- Improved logfile handling. The logfile folder may be configured.

### Version 1.2

- Added -c option to overwrite default parameter file
- Added -w option to overwrite default websites table

### Version 1.3

- Added -t option to specify a snapshot timestamp to be used to locate
  the backup archive from which a site is being restored.

## Further tiny tools

### load_site_from_ftp.py

- Overwrite a website with the content of a remote backup archive.
- A local configuration file of the site may be saved and restored again.
- The timestamp tag of the archive has to contain yyyy-mm-dd.
- This little helper utility is intended to refresh a local dev installation.

### parse_certificates.py in folder parsecerts

Display the Letsencrypt certificates in a clear format so that those that need to be renewed soon are at the top.

- Read file "certificates.txt" containing output of "certbot certificates".
- Shorten the content such that for each certificate only one line remains.
- Sort the lines such that the oldest certificates are on top.
- Print this result to stdout.

### show_vhosts.py in folder showvhosts

Utility for an Ubuntu server with Apache2 that prints out the running virtual 
hosts and the PHP FPM versions used. The output is truncated and formatted for
clarity.

### show_dns.py in folder showdns

- Requires at least dnspython 2.x.
- Queries DNS records of a list of domains.
- Writes the results to text files.
- Show help with option -h and version with -v.
- exampleDomains.txt is a demo domain file.
- exampleHosts.txt is a demo file with knows hosts.

Possible commands resulting in file show_ips_exampleDomains.txt:

    show_dns.py exampleDomains.txt -ip
    show_dns.py exampleDomains.txt -k exampleHosts.txt -ns 8.8.8.8  -ip

Possible commands resulting in file show_dns_exampleDomains.txt:

    show_dns.py exampleDomains.txt
    show_dns.py exampleDomains.txt -k exampleHosts.txt -ns 8.8.8.8

### mediawiki_update.py in folder mediawiki

Skript which updates a Mediawiki installation:
It updates the web files and also calls the database update script. The data
is read from an INI file. If no path to this config file is entered, the file
'mediawiki_update.ini' in the folder containing 'mediawiki_update.py' is 
assumed as the default. See also 'mediawiki_update.txt' for a description of
the INI file. 'mediawiki_update.py' requires a section name for the INI file.
Only the data within this section is read.

Examples for possible arguments:

 -v                                    : get version
 --help                                : get help
 -h                                    : get help
 mysite                      : read section 'mysite' from default INI file
 mysite -c /path/to/conf.ini : read from INI file /path/to/conf.ini instead

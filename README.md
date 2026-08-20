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
  + *website_manager_config.ini* with the script settings.
  + *website_table.txt* with the data of the managed websites.
- Copy and rename *demo_website_manager_config.ini* and 
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
  (This is only possible for localhost and with sudo rights.)

Snapshots are time stamped. Bulk backups are kept daily for a week,
weekly for a month, and monthly for a year. They are labeled with
wd#, w# and m# where # is an integer, wd denotes weekday, w denotes
week and m denotes month. Bulk backups are intended to be run as 
nightly cronjobs.

For the release history see "history.md".

## Further tools

### load_site_from_ftp.py

- Overwrite a website with the content of a remote backup archive.
- A local configuration file of the site may be saved and restored again.
- The timestamp tag of the archive has to contain yyyy-mm-dd.
- This little helper utility is intended to refresh a local dev installation.

### dbaccess_adjustment.py

Read, compare and, optionally, adjust database credentials of CMS websites.

- Version 1.1.0
- Test whether database credentials in the website table are valid.
- Optionally, change database passwords if the DB user exists.
- Compare website table database credentials with the CMS config data.
- Report differences.
- Optionally, adjust database credentials in the CMS config files to
  the corresponding values in the website table.
- This is supported for Joomla, Mediawiki and WordPress.

### test_cert_renewal.sh in folder certs

Test the renewal of a certificate for a vhost using Certbot.
Streamlines bugfixing. Designed for Ubuntu file paths.

- Create a backup of the Apache2 configuration for a virtual host.
- Allows Editing the virtual host configuration (bug fixing step).
- Check the configuration syntax and load the configuration into Apache2.
- Run a Certbot dry run to simulate the certificate renewal.

### parse_certificates.py in folder parsecerts

Display the Letsencrypt certificates in a clear format so that those that need to be renewed soon are at the top.

- Read file "certificates.txt" containing output of "certbot certificates".
- Shorten the content such that for each certificate only one line remains.
- Sort the lines such that the oldest certificates are on top.
- Print this result to stdout.

### folder vhosts

- *show_vhosts.py:* Utility for an Ubuntu server with Apache2 that prints out the running virtual hosts and the PHP FPM versions used. The output is truncated and formatted for clarity.
- *backup_vhost_confs.sh:* Backup all files in /etc/apache2/sites-available
- *create_vhost_pool.sh:* Create a PHP-FPM pool for an Apache vhost.

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

    -v                          : get version
    --help                      : get help
    -h                           : get help
    mysite                      : read section 'mysite' from default INI file
    mysite -c /path/to/conf.ini : read from INI file /path/to/conf.ini instead

### website_reporter.py in folder websitereporter

Generate reports on the virtual hosts installed in the web root directories.
The document roots are taken from the Apache vhost config files on default.
Without any arguments, the script will only list all detected vhost types.
Detectable vhost types are Joomla, MediaWiki, WordPress, Drupal and static sites.

Setting are read from file "website_reporter_config.ini" which has to be in the 
same directory as this script. If this file is missing, the default settings are
used. See "demo_website_reporter_config.ini" for the default settings.

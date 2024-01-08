# webdev

Simple Python 3 tools for managing websites.

## show_dns.py in folder showdns

- Requires at least dnspython 2.x.
- Queries DNS records of a list of domains.
- Writes the results to text files.
- Show help with option -h and version with -v.
- exampleDomains.txt is a demo domain file.
- exampleHosts.txt is a demo file with knows hosts.

Feasible commands resulting in file show_ips_exampleDomains.txt:

    show_dns.py exampleDomains.txt -ip
    show_dns.py exampleDomains.txt -k exampleHosts.txt -ns 8.8.8.8  -ip

Feasible commands resulting in file show_dns_exampleDomains.txt:

    show_dns.py exampleDomains.txt
    show_dns.py exampleDomains.txt -k exampleHosts.txt -ns 8.8.8.8

### Version 1.0

Initial version

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
  + `website_manager_params.txt` with the script configurations.
  + `website_table.txt contains` with the data of the managed websites.
- Copy and rename `demo_website_manager_params.txt` and 
  `demo_website_table.txt` to create your own configuration.
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
week and m denotes month.

### Version 1.0

Initial version
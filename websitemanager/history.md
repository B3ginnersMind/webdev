### Version 1.8.0

- After restoration of a CMS (Joomla, Wordpress oder Mediawiki) the database
  credentials are adjusted to the corresponding values in the website table.
  This makes it possible to restore backups with outdated database settings 
  and get them up and running right away.

### Version 1.7.0

- Introduced column "owner" of webfiles for PHP pool isolation.

### Version 1.6.3

- Fixed lineedit on comment input.
- "load_site_from_ftp.py" made compatible to website_manager.
- Comment added that web subdirectory paths are possible.

### Version 1.6.2

- Bugfix for database passwords with special characters.

### Version 1.6.1

- fix for webfolder with symbolic links

### Version 1.6

- Websites without databases may also be saved and recovered.
- No more warnings about passing DB passwords in command line.

### Version 1.5.2

- if runasroot is 'false', restore does not try to create DB or dBuser.

### Version 1.5

- order of columns in website_table.txt may vary.
- Database host column is included in website_table.txt.

### Version 1.4

- website_manager_config.ini file instead of website_manager_params.txt.
  See demo_website_manager_config.ini.
- Module pandas no longer necessary to read ini and website table input.

### Version 1.3

- Added -t option to specify a snapshot timestamp to be used to locate
  the backup archive from which a site is being restored.

### Version 1.2

- Added -c option to overwrite default parameter file
- Added -w option to overwrite default websites table

### Version 1.1

- Treated website may be entered by argument for all modes dealing with a single website.
- An alternative folder path for snapshots may be entered.
- Improved output of available backup archives in the restore mode.
- Improved logfile handling. The logfile folder may be configured.

### Version 1.0

Initial version

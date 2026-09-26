# website_reporter.py

This tool is designed for Linux web servers with vhosts (Apache) or server blocks (Nginx). It generates a report on one or more websites by analysing their web files. The document roots of the websites are either taken from the Apache vhost configuration files or provided as input. Autodetection of document roots has not yet been implemented for Nginx.

## Settings

Settings must be configured in the "website_reporter_config.ini" file.
Use 'demo_website_reporter_config.ini' as a template and edit its content as required.

## Detected properties of websites

### File owner:

The file owner is determined. Having different owners allows for effective website isolation to prevent cross-site contamination.

### Type of website:

Without any arguments specified, the script will list all the types of website that have been identified.
The following can be identified:

- Joomla, 
- MediaWiki,
- WordPress, 
- Drupal,
- unknown PHP sites, and 
- sites without PHP, which are assumed to be static.

### Basic Auth (Apache only):

.htaccess scans to see if a website is protected by basic authentication.

### Version of a CMS:

- The installed versions of the CMSs Joomla, MediaWiki, WordPress and Drupal are determined.
- For Joomla and WordPress, it is tested whether updates to the CMS core are available.

### CMS components

Joomla:

It is tested whether extension updates are available.

MediaWiki:

General statistics are listed.

WordPress:

- The installed plugins and themes, together with their versions, are determined.
- Core and plugins are verified against checksums from wordpress.org.
- Plugin and theme updates are checked for.
- It is determined whether there are any closed or commercial plugins present. The latter cannot be verified against checksums.
- The Wordfence database is searched for security vulnerabilities in the installed versions of plugins and themes.

### User data

- CMS users and their permissions can be listed optionally.
- If there are many users on WordPress, only admins are listed.

## Wordfence database

The update_wordfence_db.py script provides the Wordfence CVE database.

- A JSON file containing all CVEs is downloaded from Wordfence.
- Some unnecessary data is stripped from the JSON file.
- The data from the JSON file is inserted into a flat SQLite database table for efficient lookups.
- All operations are implemented to save memory in restricted shared hosting environments.

## File scan

- Image and upload folders of Joomla, MediaWiki, WordPress and Drupal are investigated for suspicious file types such as .php or .js.
- The first lines of any suspicious files found are included in the report.
- Benign files may be approved by the test_upload_check.py script. It saves the hashes of approved files, which are used next time to prevent false positives.

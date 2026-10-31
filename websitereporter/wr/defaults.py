APACHE_VHOST_DIR = "/etc/apache2/sites-enabled"
JOOMLA_CLI: str = "php8.4 cli/joomla.php"
MEDIAWIKI_CLI: str = "php8.4 maintenance/"
WP_CLI: str = "wp"
KNOWN_BENIGN_SCRIPTS: str = "known_script_hashes"

# Access key from the Wordfence account.
# Wordfence API Token (v3) - This is a public token for the Wordfence API. 
WF_API_TOKEN = "none"  # off by default
# Where to get the current wordfence v3 vulnerability JSON feed.
WF_FEED_URL = "https://www.wordfence.com/api/intelligence/v3/vulnerabilities/production"
# JSON file of vulnerabilities downloaded from the Wordfence API.
# This file is used to build the SQLite database.
WF_JSON_FILE = "wordfence_production.json"
# WF_ETAG_FILE = "wordfence_production.etag"
WF_LAST_MOD_FILE = "wordfence_production.last_mod"
# JSON file where some unused properties were removed
WF_JSON_REDUCED_FILE = "wordfence_reduced.json"
# Sqlite database file to store the vulnerabilities in a flat table for fast lookups
WF_DB_FILE = "wordfence.db"

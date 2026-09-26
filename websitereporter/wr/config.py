import configparser, textwrap
from dataclasses import dataclass, field, fields
from pathlib import Path
import wr.utils as u

APACHE_VHOST_DIR = "/etc/apache2/sites-enabled"
JOOMLA_CLI: str = "php8.4 cli/joomla.php"
MEDIAWIKI_CLI: str = "php8.4 maintenance/"
WP_CLI: str = "wp"
KNOWN_BENIGN_SCRIPTS: str = "known_script_hashes"

# Command to call the Wordfence CLI which was shut down in Oct 2026.
WORDFENCE_CLI: str = "none" # off by default
# Access key from the Wordfence account.
# Wordfence API Token (v3) - This is a public token for the Wordfence API. 
WF_API_TOKEN = "none"  # off by default
# Where to get the current wordfence v3 vulnerability JSON feed.
WF_FEED_URL = "https://www.wordfence.com/api/intelligence/v3/vulnerabilities/production"
# JSON file of vulnerabilities downloaded from the Wordfence API.
# This file is used to build the SQLite database.
WF_JSON_FILE = "wordfence_production.json"
WF_ETAG_FILE = "wordfence_production.etag"
# JSON file where some unused properties were removed
WF_JSON_REDUCED_FILE = "wordfence_reduced.json"
# Sqlite database file to store the vulnerabilities in a flat table for fast lookups
WF_DB_FILE = "wordfence.db"

@dataclass
class Configuration:
    run_as_root: bool = True
    joomla_cli: str = JOOMLA_CLI
    mediawiki_cli: str = MEDIAWIKI_CLI
    wp_cli: str = WP_CLI
    known_benign_scripts: Path = Path(KNOWN_BENIGN_SCRIPTS)
    wordfence_cli: str = WORDFENCE_CLI
    wf_api_token: str = WF_API_TOKEN 
    wf_feed_url: str = WF_FEED_URL
    wf_folder: Path = Path(".")
    wf_json_file: Path = Path(WF_JSON_FILE)
    wf_etag_file: Path = Path(WF_ETAG_FILE)
    wf_json_reduced_file: Path = Path(WF_JSON_REDUCED_FILE)
    wf_db_file: Path = Path(WF_DB_FILE)
    show_cms_users: bool = False
    apache_vhost_dir: Path = Path(APACHE_VHOST_DIR)
    web_roots: list[Path] = field(default_factory=list[Path])
    def show(self):
        u.print_dots()
        print('Configuration')
        num_indent = u.get_indent()
        for field in fields(self):
            if field.type is bool:
                line = (field.name + ':').ljust(num_indent) + str(getattr(self, field.name))
                print(line)
            elif field.name == "web_roots":
                str_dir_list = [str(r) for r in getattr(self, field.name)]
                line: str = (str(field.name) + ':').ljust(num_indent) + ", ".join(str_dir_list)
                indent = (u.get_indent()) * ' '
                wrappedLine = textwrap.fill(line, u.get_line_len(), subsequent_indent=indent)
                print(wrappedLine)
            else:
                line: str = (str(field.name) + ':').ljust(num_indent) + str(getattr(self, field.name))
                indent = (u.get_indent() + 1) * ' '
                wrappedLine = textwrap.fill(line, u.get_line_len(), subsequent_indent=indent)
                print(wrappedLine)
        u.print_dots()

settings = Configuration()

def read_config(config_file: Path) -> None:
    global settings
    if not config_file.is_file():
        print("Missing:", config_file)
        print("Proceeding with defaults...")
    else:
        print("Reading:", config_file)
        config = configparser.ConfigParser()
        config.read(config_file, encoding="utf-8")
        section_name = "website_reporter"
        # Read section [website_reporter]
        if section_name not in config:
            print("Missing section:", section_name)
            print("Proceeding with defaults...")
        else:
            sec = config[section_name]
            # read plain parameters
            settings.run_as_root = sec.getboolean("run_as_root", True)
            settings.joomla_cli = sec.get("joomla_cli", JOOMLA_CLI)
            settings.mediawiki_cli = sec.get("mediawiki_cli", MEDIAWIKI_CLI)
            settings.wp_cli = sec.get("wp_cli", WP_CLI)
            settings.known_benign_scripts = Path(sec.get("known_benign_scripts", KNOWN_BENIGN_SCRIPTS))

            settings.wordfence_cli = sec.get("wordfence_cli", WORDFENCE_CLI)
            settings.wf_api_token = sec.get("wf_api_token", WF_API_TOKEN)
            settings.wf_feed_url = sec.get("wf_feed_url", WF_FEED_URL)
            settings.wf_folder = Path(sec.get("wf_json_file", "."))
            settings.wf_json_file = Path(sec.get("wf_json_file", WF_JSON_FILE))
            settings.wf_etag_file = Path(sec.get("wf_etag_file", WF_ETAG_FILE))
            settings.wf_json_reduced_file = Path(sec.get("wf_json_reduced_file", WF_JSON_REDUCED_FILE))
            settings.wf_db_file = Path(sec.get("wf_db_file", WF_DB_FILE))

            settings.show_cms_users = sec.getboolean("show_cms_users", False)
            if "apache_vhost_dir" in sec:
                settings.apache_vhost_dir = Path(
                    sec.get("apache_vhost_dir", APACHE_VHOST_DIR)
                )
                print("Web roots are taken from vhost configs...")
                return
            else:
                settings.apache_vhost_dir = Path()
            # transform comma-separated list into Path objects
            if "web_roots" in sec and sec["web_roots"].strip():
                print("Web roots are taken from list 'web_roots'...")
                settings.web_roots = [
                    Path(p.strip()) 
                    for p in sec["web_roots"].split(",") 
                    if p.strip()
                ]

import configparser, textwrap
from dataclasses import dataclass, field, fields
from pathlib import Path
import wr.utils as u

APACHE_VHOST_DIR = "/etc/apache2/sites-enabled"
JOOMLA_CLI: str = "php8.4 cli/joomla.php"
MEDIAWIKI_CLI: str = "php8.4 maintenance/"
WP_CLI: str = "wp"

@dataclass
class Configuration:
    run_as_root: bool = True
    joomla_cli: str = JOOMLA_CLI
    mediawiki_cli: str = MEDIAWIKI_CLI
    wp_cli: str = WP_CLI
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

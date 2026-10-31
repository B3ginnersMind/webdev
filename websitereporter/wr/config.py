import textwrap
from dataclasses import dataclass, field, fields
from pathlib import Path
from wr.defaults import *

@dataclass
class Configuration:
    run_as_root: bool = True
    joomla_cli: str = JOOMLA_CLI
    mediawiki_cli: str = MEDIAWIKI_CLI
    wp_cli: str = WP_CLI
    known_benign_scripts: Path = Path(KNOWN_BENIGN_SCRIPTS)
    wf_api_token: str = WF_API_TOKEN 
    wf_feed_url: str = WF_FEED_URL
    wf_folder: Path = Path(".")
    wf_json_file: Path = Path(WF_JSON_FILE)
    wf_last_mod_file: Path = Path(WF_LAST_MOD_FILE)
    wf_json_reduced_file: Path = Path(WF_JSON_REDUCED_FILE)
    wf_db_file: Path = Path(WF_DB_FILE)
    show_cms_users: bool = False
    apache_vhost_dir: Path = Path(APACHE_VHOST_DIR)
    web_roots: list[Path] = field(default_factory=list[Path])
    def show(self) -> None:
        import wr.utils as u
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

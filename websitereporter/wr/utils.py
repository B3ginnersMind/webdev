import os, re, subprocess
from dataclasses import dataclass, field
from pathlib import Path
_VERBOSE = False
_LJ = 25

@dataclass
class CmsTypes:
    drupal: str = "Drupal"
    drupal_detect: str = "core/lib/Drupal.php"
    joomla: str = "Joomla"
    joomla_detect: str = "configuration.php"
    mediawiki: str = "Mediawiki"
    mediawiki_detect: str = "LocalSettings.php"
    wordpress: str = "Wordpress"
    wordpress_detect: str = "wp-settings.php"
    unknown: str = "UnknownPHP"
    unknown_php_detect: str = "php"
    static: str = "Static"

@dataclass
class CmsPaths:
    drupal_sites: list[Path] = field(default_factory=list[Path])
    joomla_sites: list[Path] = field(default_factory=list[Path])
    mediawiki_sites: list[Path] = field(default_factory=list[Path])
    wordpress_sites: list[Path] = field(default_factory=list[Path])
    static_sites: list[Path] = field(default_factory=list[Path])
    unknown_php_sites: list[Path] = field(default_factory=list[Path])

@dataclass(order=True)
class Release:
   """ CMS release (dataclass with ordering for comparison) """
   main: int = 0
   major: int = 0
   minor: int = 0
   def __init__(self, lead: int | str = 0, major: int = 0, minor: int = 0) -> None:
      if isinstance(lead, str):
         parts = lead.split(".")
         if len(parts) < 2 or len(parts) > 3:
            raise ValueError(f"Invalid release: {lead}")
         self.main = int(parts[0])
         self.major = int(parts[1])
         self.minor = int(parts[2])
      else:
         self.main = lead
         self.major = major
         self.minor = minor
   def __str__(self) -> str:
      return f"{self.main}.{self.major}.{self.minor}"

def print_dots():
    print(80 * ".")
def print_line():
    print()
    print(80 * "-")
def print_double_line():    
    print()
    print(80 * "=")

def has_file_extension(start_directory: str, file_extension: str) -> bool:
    """
    Searches the entire directory tree recursively for a specific file extension.
    Returns True if at least one file is found, otherwise False.
    """
    # Ensure the extension starts with a dot (e.g., '.ext')
    ext: str = file_extension if file_extension.startswith(".") else f".{file_extension}"
    
    # Path.rglob() searches recursively through all subdirectories.
    # any() evaluates the generator lazily and stops at the very first match.
    return any(Path(start_directory).rglob(f"*{ext}"))

def has_any_file_extension(start_directory: str, extensions: list[str]) -> bool:
    # 1. Bereite ein Set der gesuchten Endungen vor (für sofortige O(1) Lookups)
    # Fügt fehlende Punkte hinzu
    target_exts = {ext if ext.startswith(".") else f".{ext}" for ext in extensions}
    
    # 2. Generator-Expression mit any(): 
    # Durchsucht den Baum EINMAL. any() bricht die Suche sofort ab (Short-Circuit), 
    # sobald die allererste passende Datei gefunden wurde.
    return any(
        p.suffix in target_exts 
        for p in Path(start_directory).rglob("*") 
        if p.is_file()
    )

def get_document_roots(apache_config_dir: str) -> list[Path]:
    """
    Returns a list of DocumentRoot directories for all vhosts.
    """
    print("DocumentRoots are from:".ljust(_LJ), apache_config_dir)
    docroot_list: list[Path] = []
    command = ("find -L " + apache_config_dir + " -name '*.conf' -exec "
               "grep -h -i 'documentroot' {} + | grep -E -v '^[[:space:]]*#'")
    lines = get_shell_command_output(command)
    if _VERBOSE:
        for line in lines:
            print("Found DocumentRoot line:", line)
    # Find the last block before the end of the line 
    # that does not contain any spaces or quotation marks.
    pattern = re.compile(r"['\"]?([^\s'\"]+)['\"]?\s*$")
    for line in lines:
        match = pattern.search(line)
        if match:
            docroot_list.append(Path(match.group(1)))
    unique_docroots = list(set(docroot_list))
    if _VERBOSE:
        for path in unique_docroots:
            print(f"Extracted document root: {path}")
    return unique_docroots

def get_subdirectories(base_path: Path) -> list[Path]:
    print("Find subdirectories in       :", base_path)
    # Ensure the provided path exists and is actually a directory
    if not base_path.is_dir():
        print(f"Error: '{base_path}' is not a valid directory.")
        quit()
    # iterdir() yields all files and folders in the directory (no recursion)
    sub_dirs: list[Path] = [p for p in base_path.iterdir() if p.is_dir()]
    if _VERBOSE:
        for path in sub_dirs:
            print(f"Found subdirectory: {path}")
    return sub_dirs

def show_num_websites(cms: str, path_list: list[Path], common_root: str):
    if (len(path_list) > 0):
        path_list.sort()
        dir_names: list[str] = [re.sub(common_root, '', str(p)) for p in path_list]
        name_str: str = ", ".join(dir_names)
        detected_sites = f"Detected {cms}:".ljust(_LJ)
        print(detected_sites, name_str)

def detect_cms(doc_roots: list[Path]) -> CmsPaths:
    print("Scanned WebDocRoots:".ljust(_LJ), len(doc_roots))
    types = CmsTypes()
    cms_type = ""
    cms_paths = CmsPaths()
    common_root = os.path.commonpath(doc_roots)
    if common_root[-1] != '/':
        common_root += '/'

    num_skipped_symlinks = 0
    # iterdir() yields all files and folders in the directory (no recursion)
    for web_root in doc_roots:
        # Filter: Only process the item if it is a directory
        cms_type = types.static
        if web_root.is_symlink():
            num_skipped_symlinks += 1
            if _VERBOSE:
                print(f"Folder {web_root} : skipped due to symlink")
            continue
        if (web_root / types.joomla_detect).exists():
            cms_type = types.joomla
            cms_paths.joomla_sites.append(web_root)
        elif (web_root / types.mediawiki_detect).exists():
            cms_type = types.mediawiki
            cms_paths.mediawiki_sites.append(web_root)
        elif (web_root / types.wordpress_detect).exists():
            cms_type = types.wordpress
            cms_paths.wordpress_sites.append(web_root)
        elif (web_root / types.drupal_detect).exists():
            cms_type = types.drupal
            cms_paths.drupal_sites.append(web_root)
        elif has_file_extension(str(web_root), types.unknown_php_detect):
            cms_type = types.unknown
            cms_paths.unknown_php_sites.append(web_root)
        else:
            cms_paths.static_sites.append(web_root)
        if _VERBOSE:
            print(f"Folder {web_root} : {cms_type} detected")

    show_num_websites(CmsTypes.drupal, cms_paths.drupal_sites, common_root)
    show_num_websites(CmsTypes.joomla, cms_paths.joomla_sites, common_root)
    show_num_websites(CmsTypes.mediawiki, cms_paths.mediawiki_sites, common_root)
    show_num_websites(CmsTypes.wordpress, cms_paths.wordpress_sites, common_root)
    show_num_websites(CmsTypes.static, cms_paths.static_sites, common_root)
    show_num_websites(CmsTypes.unknown, cms_paths.unknown_php_sites, common_root)
    print("Skipped Symlinks:".ljust(_LJ), num_skipped_symlinks)
    print_double_line()
    print("Owners not root/www-data:".ljust(_LJ), "different isolated PHP pools!")
    print("Common webroot directory:".ljust(_LJ), common_root)
    get_shell_command_output(f"sudo ls -l {common_root}", verbose=True)
    return cms_paths

def check_static_sites(cms: CmsPaths):
    print_line()
    if len(cms.static_sites) == 0:
        print("==> Static sites: none")
    print("==> Static sites:")
    for dir in cms.static_sites:
        print(dir)

def run_command(command_str: str):
    """
    Run the command 'command_str' and print its output. 
    Tabbed output is aligned in columns.
    """
    command: list[str] = []
    command.extend(command_str.split(" "))

    plain_command = ""
    for token in command:
        plain_command += token + " "
    print_dots()        
    print(f"--> Command: {plain_command}")

    result = subprocess.run(command, capture_output=True, text=True, check=True)
    if result.stderr.strip():
        print(result.stderr)

    lines = result.stdout.splitlines()
    rows = [line.split("\t") for line in lines]
    # compute column widths
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    for row in rows:
        print("  ".join(col.ljust(widths[i]) for i, col in enumerate(row)))

def get_shell_command_output(command: str, verbose: bool=False) -> list[str]:
    """runs shell command and returns output as list of strings"""
    if _VERBOSE:
        print('Processing', '"'+command+'"')
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                            universal_newlines=True, shell=True)
    if verbose:
        print(result.stdout.strip())
    lines = result.stdout.splitlines()
    lines = [l.strip() for l in lines]
    lines = [" ".join(l.split()) for l in lines]
    return lines

import os, re, stat, subprocess, textwrap
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
_VERBOSE = False
_INDENT = 25
_INDENT1 = _INDENT + 1
_LINE_LEN = 100

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

def get_indent():
    return _INDENT
def get_line_len():
    return _LINE_LEN
def print_dots():
    print(_LINE_LEN * ".")
def print_line():
    print()
    print(_LINE_LEN * "-")
def print_double_line():
    print()
    print()
    print(_LINE_LEN * "=")
def print_headline(text: str = ""):
    print()
    headline = _LINE_LEN * "#"
    if text:
        head = " " + text + " "
        headline = headline[:4] + head + headline[4 + len(head):]
        # headline = headline[:_LINE_LEN]
        
    print(headline)

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
    print("DocumentRoots are from:".ljust(_INDENT), apache_config_dir)
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
        detected_sites = f"Detected {cms}:".ljust(_INDENT1)
        line = detected_sites + name_str
        indent = _INDENT1 * ' '
        wrappedLine = textwrap.fill(line, get_line_len(), subsequent_indent=indent)
        print(wrappedLine)

def list_directories(pathlist: list[Path]) -> None:
    if not pathlist:
        return

    rows: list[tuple[str, str, str, str, str]] = []
    for p in pathlist:
        if not p.exists():
            continue
        name = p.name 
        mode = stat.filemode(p.stat().st_mode)
        owner = p.owner()  # type: ignore
        group = p.group()  # type: ignore
        mtime = p.stat().st_mtime
        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        target = ""
        if p.is_symlink():
            target = "-> " + str(p.readlink())
        rows.append((mode, f"{owner}:{group}", date_str, name, target))

    if not rows:
        return
    
    widths = [max(len(row[index]) for row in rows) for index in range(4)]
    for mode, owner_group, date_str, name, target in rows:
        line = (
            f"{mode:<{widths[0]}} {owner_group:<{widths[1]}} "
            f"{date_str:<{widths[2]}} {name:<{widths[3]}}"
        )
        print(f"{line} {target}".rstrip())
    return

def detect_cms(doc_roots: list[Path]) -> CmsPaths:
    print("Scanned WebDocRoots:".ljust(_INDENT), len(doc_roots))
    types = CmsTypes()
    cms_type = ""
    cms_paths = CmsPaths()
    common_root = os.path.commonpath(doc_roots)
    if common_root[-1] != '/':
        common_root += '/'

    num_skipped_symlinks = 0
    num_non_existent_folders = 0
    # iterdir() yields all files and folders in the directory (no recursion)
    for web_root in doc_roots:
        # Filter: Only process the item if it is a directory
        cms_type = types.static
        if web_root.is_symlink():
            num_skipped_symlinks += 1
            if _VERBOSE:
                print(f"Folder {web_root} : skipped due to symlink")
            continue
        if not web_root.exists() or not web_root.is_dir():
            num_non_existent_folders += 1
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
    if num_skipped_symlinks > 0:
        print("Skipped Symlinks:".ljust(_INDENT), num_skipped_symlinks)
    if num_non_existent_folders > 0:
        print("Skipped non-existent:".ljust(_INDENT), num_non_existent_folders)
    print_double_line()
    print("Owners not root/www-data:".ljust(_INDENT), "different isolated PHP pools")
    print("Common webroot directory:".ljust(_INDENT), common_root)
    # only list the relevant directories
    list_directories(doc_roots)
    # get_shell_command_output(f"sudo ls -l {common_root}", verbose=True)
    return cms_paths

def check_static_sites(cms: CmsPaths):
    print_line()
    if len(cms.static_sites) == 0:
        print("==> Static sites: none")
    print("==> Static sites:")
    for dir in cms.static_sites:
        print(dir)

def remove_ansi_esc_sequences(raw_text: str) -> str:
    """ Get rid of ANSI escape sequences for text formatting in the terminal """
    if re.match(r'\x1b\[[0-9;]*m', raw_text):
        return re.sub(r'\x1b\[[0-9;]*m', '', raw_text)
    return raw_text

def get_nonempty_lines(raw_text: str) -> list[str]:
    # [stripped for line in raw_text.splitlines() if (stripped := line.strip())]
    # list(filter(None, (line.strip() for line in raw_text.splitlines())))
    return [line.strip() for line in raw_text.splitlines() if line.strip()]

def insert_vspace_before_found(lines: list[str]) -> list[str]:
    token = "Found"
    count = 0
    for l in lines:
        if l.startswith(token):
            count += 1
    if count < 2:
        return lines
    new_lines: list[str] = []
    new_lines.append(lines[0])
    for l in lines[1:]:
        if l.startswith(token):
            new_lines.append("")
        new_lines.append(l)
    return new_lines

def run_command(command_str: str, 
                environ_variable: tuple[str, str] = ("", "")):
    """
    Run the command 'command_str' and print its output. 
    Tabbed output is aligned in columns.
    """
    command: list[str] = []
    command.extend(command_str.split(" "))

    if environ_variable == ("", ""):
        plain_command = ""
        my_env = os.environ
    else:
        plain_command = environ_variable[0] + "=" + environ_variable[1] + " "
        # Copy current environment as dictionary
        my_env = os.environ.copy()
        # Add the variable
        my_env[environ_variable[0]] = environ_variable[1]

    for token in command:
        plain_command += token + " "
    print_dots()        
    print(f"--> Command: {plain_command}")
    result = subprocess.run(command, capture_output=True, text=True, check=False, env=my_env)

    if result.stderr.strip():
        lines = get_nonempty_lines(result.stderr)
        warning_msg = "human output format requires a terminal with color"
        # Filters out all lines containing the warning text
        lines = [line for line in lines if warning_msg not in line]
        if lines:
            print(">>> stderr output ................")
            print(*lines, sep="\n")
            print("..................................")
    clean_text = remove_ansi_esc_sequences(result.stdout)
    lines = get_nonempty_lines(clean_text)
    if not lines:
        return

    lines = insert_vspace_before_found(lines)
    rows = [line.split("\t") for line in lines]
    # Compute max. number of columns.
    max_cols = max(len(row) for row in rows)
    if max_cols == 1:
        print(*lines, sep="\n")
        return

    # Pad any lines that are too short with empty strings (‘’) so that all
    # lines have exactly the same number of elements (indices).
    rows = [row + [""] * (max_cols - len(row)) for row in rows]
    # Compute the widths of the columns
    widths = [max(len(row[i]) for row in rows) for i in range(max_cols)]
    # Formatted output
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

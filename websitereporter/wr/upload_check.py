import hashlib, re, shutil
from enum import Enum
from pathlib import Path
from wr.config import settings
from wr.utils import CmsPaths, CmsTypes
import wr.utils as u

# In this dict suspicious PHP files are collected. Key is a hash of the file content.
# hash -> (file_content, list_of_paths_where_file_found)
FileDict = dict[str, tuple[str, list[Path]]] # Without TypeAlias for Python 3.10
hash_to_file: FileDict = {}
# Set of file hashes where is has been checked that the files are benign.
benign_file_hashes: set[str] = set()
# List of file types which should not occur in upload directories.
tested_file_types: list[str] = [ "*.js" ]

class AppMode(Enum):
    TEST_MODE = "check_mode"
    ACCEPT_MODE = "adjust_mode"


def sus_files(cmsPath: Path, checked_subdirs: list[str]):
    """
    Look for suspicious program source files in upload folders.
    """
    for subdir in checked_subdirs:
        sus_php_in_uploads(cmsPath / subdir)
        sus_file_types(cmsPath/ subdir)
 
def upload_checks(mode: AppMode, cms_paths: CmsPaths):
    """
    Perform all upload checks. If in ACCEPT_MODE write new
    file of accepted program source files in upload folders.
    """
    load_file_hashes()
    types = CmsTypes()
    for p in cms_paths.drupal_sites:
        sus_files(p, types.drupal_checked_subdirs)
    for p in cms_paths.joomla_sites:
        sus_files(p, types.joomla_checked_subdirs)
    for p in cms_paths.mediawiki_sites:
        sus_files(p, types.mediawiki_checked_subdirs)
    for p in cms_paths.wordpress_sites:
        sus_files(p, types.wordpress_checked_subdirs)
    show_suspicious_files()
    if mode == AppMode.ACCEPT_MODE:
        save_file_hashes()

def sus_php_in_uploads(uploads: Path) -> None:
    """ 
    Look for suspicious PHP files and collect them in the set hash_to_file. 
    """
    u.print_dots()
    print(f"--> Check for '*.php' in: {uploads}")
    global hash_to_file
    if not uploads.is_dir():
        return
    num_found = 0
    num_found_stored = 0

    for p in uploads.rglob("*.php"):
        if p.is_file():
            hash = hashlib.sha256(p.read_bytes()).hexdigest()
            if hash in benign_file_hashes:
                continue  # known + unchanged
            if p.name == "index.php":
                # If the file is < 1001 bytes: parse it. Otherwise, it’s suspicious anyway.
                if p.stat().st_size > 1000 or not_empty_php(p):
                    print(f"🔴 Datei: {p}")
                    num_found += 1
            else:
                # That file doesn’t belong there. Just a case of uncontrolled plugin proliferation?
                print(f"🔴 Datei: {p}")
                num_found += 1
            if num_found > num_found_stored:
                num_found_stored = num_found
                if hash not in hash_to_file:
                    hash_to_file[hash] = (p.read_text(),[p])
                else:
                    hash_to_file[hash][1].append(p)

    print(f"Number of suspicious '*.php' files found: {num_found}")
    return

def sus_file_types(uploads: Path) -> None:
    """ 
    Look for suspicious file types and collect them in the set hash_to_file. 
    """
    global hash_to_file
    num_found = 0
    num_found_stored = 0
    for ft in tested_file_types:
        print(f"--> Check for '{ft}' in: {uploads}")
        for p in uploads.rglob(ft):
            if p.is_file():
                hash = hashlib.sha256(p.read_bytes()).hexdigest()
                if hash in benign_file_hashes:
                    continue  # known + unchanged
                print(f"🔴 Datei: {p}")
                num_found += 1
                if num_found > num_found_stored:
                    num_found_stored = num_found
                    hash = hashlib.sha256(p.read_bytes()).hexdigest()
                    if hash not in hash_to_file:
                        hash_to_file[hash] = (p.read_text(),[p])
                    else:
                        hash_to_file[hash][1].append(p)
        print(f"Number of suspicious '{ft}' files found: {num_found}")

def show_suspicious_files():
    u.print_double_line()
    print(f"Total number of suspicious upload files found: {len(hash_to_file)}")
    for _, (text, paths) in hash_to_file.items():
        print()
        for p in paths:
            print("file:", str(p))
        print("_____BEGIN_FILE__________________________________________________")
        lines = text.splitlines()
        max_columns = 120
        max_lines = 8
        longest_line = 0
        if len(lines) > max_lines:
            for zeile in lines[:max_lines]:
                if len(zeile) > max_columns:
                    longest_line = max(longest_line, len(zeile))
                    zeile = zeile[:max_columns] + "...[truncated]"
                print(zeile)
            print(f"... output truncated as {len(lines)} lines exceeds {max_lines}")
            if longest_line > max_columns:
                print(f"... lines truncated as {longest_line} chars exceeds {max_columns}")
        else:
            print(text)
        print("_____END_FILE____________________________________________________")

def save_file_hashes():
    global benign_file_hashes
    u.print_double_line()
    if not hash_to_file:
        print("There are no additional script hashes for storage.")
        return
    file = settings.known_benign_scripts
    if len(benign_file_hashes) > 0:
        backup_file = file.name + ".bak"
        print("Save current script hashes to:", backup_file)
        shutil.copy2(file, file.with_name(backup_file)) 

    print("Write new script hashes to:", file)
    lines = "\n".join(f"{digest}" for digest in hash_to_file)
    file.write_text(lines + "\n")

def load_file_hashes() -> None:
    global benign_file_hashes
    u.print_dots()
    file = settings.known_benign_scripts
    if file.exists():
        print(f"Read: {file}")
        for line in file.read_text().splitlines():
            benign_file_hashes.add(line.strip())
        print("Number of loaded known benign files hashes", len(benign_file_hashes))
    else:
        print(f"Still no file {file} with known scripts.")
    return

def contains_executable_php_code(php_content: str) -> bool:
    # Remove PHP tags (<?php, <?, ?>, but leave the = in <?= as it means “echo”)
    # Replaces <?php, <? and ?> with nothing.
    php_content = re.sub(r'<\?(?:php)?|\?>', '', php_content, flags=re.IGNORECASE)
    # Regular expression that finds EITHER strings OR comments
    pattern = re.compile(
        r'('
        r'"(?:\\.|[^"\\])*"|'   # Group 1: Double quotation marks (strings)
        r"'(?:\\.|[^'\\])*'"    # Group 1: Single quotation marks (strings)
        r')|('
        r'/\*.*?\*/|'           # Group 2: Multi-line comments /* ... */
        r'//[^\n]*|'            # Group 2: Single-line comments // ...
        r'#[^\n]*'              # Group 2: Single-line comments # ... (allowed in PHP!)
        r')',
        re.DOTALL | re.MULTILINE
    )
    # Replacement function: Keep strings, remove comments
    def replacer(match: re.Match[str]) -> str:
        if match.group(1):
            return match.group(1) # It is a string -> return unchanged
        else:
            return ''             # It is a comment -> replace with nothing
    # Remove comments
    cleaned_code = pattern.sub(replacer, php_content)
    # Remove whitespace (spaces, tabs, line breaks)
    cleaned_code = cleaned_code.strip()
    # If anything remains, the file contains executable code
    return bool(cleaned_code)

def not_empty_php(php_file: Path) -> bool:
    """True, wenn Inhalt leer oder regex matcht."""
    text = php_file.read_text(encoding="utf-8", errors="replace")
    if text.strip() == "":
        return False
    return contains_executable_php_code(text)

import hashlib, re, sys
from pathlib import Path
from wr.utils import CmsPaths
import wr.utils as u
import termios, tty # type: ignore

FileDict = dict[str, tuple[str, list[Path]]] # Without TypeAlias for Python 3.10
hash_to_file: FileDict = {}


# __ Konfiguration ____________________________________________________________
# _STATE_DIR = Path("/usr/home/gwupqo/.gwup-monitor")     # absolut, kein ~

def upload_checks(cms_paths: CmsPaths):
    for p in cms_paths.joomla_sites:
        cmd_upload_check(p / "images")
    for p in cms_paths.wordpress_sites:
        cmd_upload_check(p / "wp-content" / "uploads")
    show_files()

def cmd_upload_check(upload_dir: Path) -> None:
    """Prüft alle WP-Roots auf verdächtige PHP-Dateien in uploads/."""
    # Auf PHP/JS-Dateien in uploads prüfen (Backdoor-Indikator)
    u.print_dots()
    print(f"--> Check uploads in: {upload_dir}")
    sus_php_in_uploads(upload_dir)

def sus_php_in_uploads(uploads: Path) -> None:
    global hash_to_file
    if not uploads.is_dir():
        return
    baseline_hashes: dict[Path, str] = {}
    # bf = baseline_file(uploads)
    # if bf.exists():
    #     baseline_hashes = load_baseline(uploads)

    num_found = 0
    num_found_stored = 0
    # print("sus_php_in_uploads")
    for p in uploads.rglob("*.php"):
        if p.is_file():
            key = p
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            if baseline_hashes.get(key) == digest:
                continue  # known + unchanged
            if p.name == "index.php":
                # If the file is < 1001 bytes: parse it. Otherwise, it’s suspicious anyway.
                if p.stat().st_size > 1000 or not_empty_php(p):
                    print(f"🔴 Datei: {p}")
                    num_found += 1
            else:
                # That file doesn’t really belong there. Just a case of uncontrolled plugin proliferation?
                print(f"🔴 Datei: {p}")
                num_found += 1
            if num_found > num_found_stored:
                num_found_stored = num_found
                if digest not in hash_to_file:
                    hash_to_file[digest] = (p.read_text(),[p])
                else:
                    hash_to_file[digest][1].append(p)

    print(f"Number of suspicious PHP files found: {num_found}")
    return

def show_files() -> None:
    u.print_double_line()
    print(f"Total number of suspicious PHP files found: {len(hash_to_file)}")
    for _, (text, paths) in hash_to_file.items():
        # print("hash:", key)
        print()
        for p in paths:
            print("file:", str(p))
        print("_____BEGIN_FILE_____")
        print(text)
        print("_____END_FILE_______")


# def baseline_file(wp_root: Path) -> Path:
#     return _STATE_DIR / f"baseline_{path_to_slug(wp_root)}.sha256"

# def load_baseline(wp_root: Path) -> dict[Path, str]:
#     """Gespeicherte Baseline einlesen."""
#     bf = baseline_file(wp_root)
#     if not bf.exists():
#         return {}
#     hashes: dict[Path, str] = {}
#     for line in bf.read_text().splitlines():
#         digest, _, path = line.partition("  ")
#         hashes[Path(path)] = digest
#     return hashes

def contains_executable_code(php_content: str) -> bool:
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
    return contains_executable_code(text)

def path_to_slug(wp_root: Path) -> str:
    """Pfad in sicheren Dateinamen umwandeln, z.B. für Baseline-Dateien."""
    return str(wp_root).replace("/", "_").replace(" ", "_")

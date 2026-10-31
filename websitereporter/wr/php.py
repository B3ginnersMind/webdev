
import re
from pathlib import Path
import subprocess

def get_php_cli_version(php_command: str = "php") -> str:
    try:
        # Run the command and capture its text output (stdout)
        result = subprocess.run(
            [php_command, "-v"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # Split the text at line breaks and return the first line
        first_line = result.stdout.splitlines()[0]
        return first_line
        
    except FileNotFoundError:
        return "Error: PHP is not installed on this system."
    except subprocess.CalledProcessError as e:
        return f"Error during execution: {e}"
    except IndexError:
        return "Error: The command did not produce any output."

def get_installed_php_versions() -> list[tuple[str, str]]:
    try:
        # 1. Call "which php" and capture its output
        result = subprocess.run(
            ['which', 'php'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        php_path = Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Fehler: Kein Standard-PHP gefunden.")
        return []

    # 2. Extract the directory (usually /usr/bin)
    php_dir = php_path.parent

    # Check whether the directory actually exists
    if not php_dir.exists() or not php_dir.is_dir():
        print(f"Fehler: Verzeichnis {php_dir} existiert nicht.")
        return []

    # 3. & 4. Find "php*" commands in the directory and store them in a list
    # (Equivalent to "cd /usr/bin && ls -1 php*")
    all_php_commands = [f.name for f in php_dir.glob("php*")]

    # 5. Filter: Allow only entries in the form phpX or phpX.Y
    # Explanation of the regex pattern:
    # ^php      -> Starts exactly with "php"
    # \d+       -> Followed by at least one digit (the "X")
    # (?:\.\d+)? -> Optional: A dot followed by at least one digit (the ".Y")
    # $         -> The end of the filename (excludes phpX.Y-cli, phpX.Y-fpm, etc.)
    pattern = re.compile(r"^php\d+(?:\.\d+)?$")
    
    filtered_versions = [cmd for cmd in all_php_commands if pattern.match(cmd)]

    # Sort the list alphabetically for easier browsing
    filtered_versions.sort()
    php_releases: list[tuple[str, str]] = []
    for version in filtered_versions:
        version_info = get_php_cli_version(version)
        php_releases.append((version, version_info))
    return php_releases

def scan_config_file(conf_file: Path) -> tuple[Path, set[str]] | None:
    if not conf_file.is_file():
        return None
    try:
        lines = conf_file.read_text(encoding='utf-8').splitlines()
    except UnicodeDecodeError:
        print(f"Warning: Could not read '{conf_file.name}' due to encoding issues.")
        return None

    # Regex matches strings like 'php8.4' or 'php7'
    php_pattern = re.compile(r'php\d+(?:\.\d+)?')
    # Matches 'DocumentRoot' (case-insensitive), captures spacing and the path
    # (?i) case-insensitive flag
    # (...) first capture group with any front whitespace chars \s*
    #       and at least one trailing whitespace char
    # (...) 2nd capture group with at least obe char
    docroot_pattern = re.compile(r'(?i)^(\s*DocumentRoot\s+)(.+)$')
    php_releases: set[str] = set()
    docroot: Path | None = None
    
    for line in lines:
        # Skip commented lines
        if line.lstrip().startswith('#'):
            continue
        # Search for PHP socket/version
        if "/run/php/" in line:
            matches = php_pattern.findall(line)
            for match in matches:
                php_releases.add(match)
        # Search for DocumentRoot
        docroot_match = docroot_pattern.match(line)
        if docroot_match:
            # Extract path and strip any accidental quotes
            extracted_path = docroot_match.group(2).strip('"\'')
            docroot = Path(extracted_path)

    # There is nothing to scan if we don't have a DocumentRoot
    if docroot is None:
        return None
    print(f"DocRoot {docroot} with PHP: {php_releases}")
    return (docroot, php_releases)

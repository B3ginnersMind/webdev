#!/usr/bin/env python3
"""
-----------------------------------------------------------------------------
This script can be used to redirect all websites that use PHP to a static 
maintenance page. This may be advisable if there is a critical security 
vulnerability in PHP and a patch is pending.

First, all configuration files are backed up. The script then checks all 
Apache configurations to see whether PHP is being used. If so, the 
"DocumentRoot" parameter is changed. The Apache web server is then restarted.
The backed-up configuration files can also be restored from the backup directory.

The script must be run with root privileges (sudo) to modify the Apache 
configuration files. See the demo_php_killswitch_config.ini file for the 
configuration of the script.
-----------------------------------------------------------------------------
"""
import argparse, configparser, datetime, os, re
import difflib, filecmp
import shutil, subprocess, sys, textwrap
from pathlib import Path
from wm.utils import abort, is_file_or_abort, query_continue, print_line
__version__ = "1.0.0"
TOKEN_FILE = "php_killswitch_token.txt" 

def set_php_sites_to_maintenance(
    apache_conf_dir: Path, 
    backup_dir: Path, 
    maintenance_dir: Path
) -> None:
    
    # 1. Check if the script is executed as root (sudo)
    if os.geteuid() != 0:
        print("Error: This script must be run as root (sudo).")
        sys.exit(1)
        
    # 2. Check if maintenance_dir exists and contains index.html
    if not maintenance_dir.is_dir():
        print(f"Error: Maintenance directory '{maintenance_dir}' does not exist.")
        sys.exit(1)
        
    index_file = maintenance_dir / "index.html"
    if not index_file.is_file():
        print(f"Error: '{index_file}' not found in the maintenance directory.")
        sys.exit(1)

    if token_file_exists(apache_conf_dir):
        print("PHP killswitch is already set. Nothing to do.")
        return

    # Create backup directory if it does not exist
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. Perform backup of all *.conf files in new timestamp folder
    current_time = datetime.datetime.now()
    timestamp = current_time.strftime('%Y-%m-%d_%H-%M')
    curr_backup_dir = backup_dir / timestamp
    curr_backup_dir.mkdir(parents=True, exist_ok=True)
    
    for conf_file in apache_conf_dir.glob("*.conf"):
        if conf_file.is_file():
            backup_path = curr_backup_dir / conf_file.name
            print("Saved:", backup_path)
            shutil.copy2(conf_file, backup_path)

    print("Backup completed. Configs are saved in:", curr_backup_dir)
    print("Switch now DocumentRoots to maintenance page?")
    query_continue()

    # 4. List of tuples: (conf_filename, PHP-Releases, DocRoot-Path)
    conf_data: list[tuple[str, set[str], Path]] = []
    
    # Regex patterns
    # Matches strings like 'php8.4' or 'php7'
    php_pattern = re.compile(r'php\d+(?:\.\d+)?')
    # Matches 'DocumentRoot' (case-insensitive), captures spacing and the path
    docroot_pattern = re.compile(r'(?i)^(\s*DocumentRoot\s+)(.+)$')
    
    # 5. Process all *.conf files
    for conf_file in apache_conf_dir.glob("*.conf"):
        if not conf_file.is_file():
            continue
            
        try:
            lines = conf_file.read_text(encoding='utf-8').splitlines()
        except UnicodeDecodeError:
            print(f"Warning: Could not read '{conf_file.name}' due to encoding issues. Skipping.")
            continue
            
        php_releases: set[str] = set()
        docroot_index = -1
        website_dir: Path | None = None
        
        for i, line in enumerate(lines):
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
                docroot_index = i
                # Extract path and strip any accidental quotes
                extracted_path = docroot_match.group(2).strip('"\'')
                website_dir = Path(extracted_path)
                
        # If no PHP string was found, proceed to the next file
        if not php_releases:
            continue
            
        # If PHP was found and a DocumentRoot exists, update the configuration
        if docroot_index != -1 and website_dir is not None:
            # Add to our data list
            conf_data.append((conf_file.name, php_releases, website_dir))
            
            # Replace the directory path with maintenance_dir (keeping original indentation)
            prefix = docroot_pattern.match(lines[docroot_index]).group(1)
            lines[docroot_index] = f"{prefix}{maintenance_dir}"
            
            # Save the modified .conf file
            conf_file.write_text("\n".join(lines) + "\n", encoding='utf-8')

    write_token_file(apache_conf_dir)

    # 6. Print the collected configuration data to stdout
    print("\n--- Collected Configuration Data ---")
    for data_tuple in conf_data:
        print(data_tuple)
    
    restart_apache()

def restart_apache():
    # Test configuration and restart Apache
    print("Testing Apache configuration...")
    # apache2ctl configtest writes its output primarily to stderr
    test_result = subprocess.run(["apache2ctl", "configtest"], capture_output=True, text=True)
    
    if test_result.returncode == 0:
        print("Configuration OK. Restarting Apache...")
        subprocess.run(["apache2ctl", "restart"], check=True)
    else:
        print("Error: Apache configuration test failed! Restart aborted.")
        print(test_result.stderr)

def token_file_exists(apache_conf_dir: Path):
    return (apache_conf_dir / TOKEN_FILE).is_file()

def write_token_file(apache_conf_dir: Path):
    token_file = apache_conf_dir / TOKEN_FILE
    with open(token_file, "w", encoding="utf-8") as token:
        token.write("PHP Websites are switched to maintenance.\n")
        token.write("Restore them with 'php_killswitch.py -r'.\n")

def remove_token_file(apache_conf_dir: Path):
    token = apache_conf_dir / TOKEN_FILE
    token.unlink(missing_ok=True)

def show_timestamps(backup_dir: Path) -> list[str]:
    # Initialize the list for matching directory names
    timestamps: list[str] = []
    
    # Check if the provided path exists and is a directory
    if not backup_dir.is_dir():
        print(f"Error: The directory '{backup_dir}' does not exist.")
        return timestamps

    # Regular expression to match the exact format 'y-m-d_h-m' (only integers)
    # \d+ matches one or more digits.
    # ^ and $ ensure the entire string matches the pattern, with no extra characters.
    pattern = re.compile(r"^\d+-\d+-\d+_\d+-\d+$")
    
    # Iterate over all items in the backup directory
    for item in backup_dir.iterdir():
        # Check if the item is a directory and its name matches the pattern
        if item.is_dir() and pattern.match(item.name):
            timestamps.append(item.name)
            
    # Sort the list so the output is neatly ordered
    timestamps.sort()
            
    # Check if any timestamps were found
    if not timestamps:
        print("No matching timestamp directories found in the backup directory.")
        return timestamps

    # Join the directory names into a single string separated by spaces
    joined_text = " ".join(timestamps)
    
    # Wrap the string at a maximum of 80 characters per line
    # textwrap will automatically break the lines at spaces, keeping names intact
    wrapped_output = textwrap.fill(joined_text, width=80)
    
    # Print the result to the console
    print("Available timestamps:")
    print(wrapped_output)
    return timestamps

def compare_files(live_file: Path, backup_file: Path) -> bool:
    # Check file status
    if not backup_file.is_file():
        print("Error: Backup config file does not exist or is not a file.")
        return False  # Indicate that restoration is not possible
    if not live_file.is_file():
        print("Live config file is missing and has to be restored.")
        return True  # Indicate that restoration is needed

    # 1. Fast identity check
    # shallow=False forces a content-based comparison (byte by byte)
    # in case the file sizes are identical.
    if filecmp.cmp(live_file, backup_file, shallow=False):
        print(f"The backup file of '{live_file.name}' is exactly identical.")
        return False  # No restoration needed

    # 2. Files are different -> generate diff
    print(f"Differences between '{live_file.name}' and '{backup_file.name}':\n")
    
    # Read text files. 
    # Using .readlines() preserves the actual line breaks needed for the diff.
    try:
        with live_file.open('r', encoding='utf-8') as f1, backup_file.open('r', encoding='utf-8') as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()
    except UnicodeDecodeError:
        print("Error: Files could not be read as UTF-8 text (possibly binary files).")
        return True  # Indicate that restoration is needed

    # Calculate unified diff (standard format)
    diff = difflib.unified_diff(
        lines1, 
        lines2, 
        fromfile=str(live_file), 
        tofile=str(backup_file),
        n=0 # Number of unchanged context lines (like in git diff)
    )
    
    # Output diff directly to the console (stdout)
    print_line('.')
    sys.stdout.writelines(diff)
    return True  # Indicate that restoration is needed

def restore_php_sites_from_backup(
    apache_conf_dir: Path, 
    backup_dir: Path
) -> None:
    
    # Check if the backup directory exists
    if not backup_dir.is_dir():
        print(f"Error: Backup directory '{backup_dir}' does not exist.")
        return

    if not token_file_exists(apache_conf_dir):
        print("PHP killswitch is not set. Restore anyway?.")
        query_continue()
        return

    # Define the search pattern as conf files
    search_pattern = "*.conf"
    # Change working directory to backup_dir for globbing
    os.chdir(backup_dir)
    print(backup_dir)
    # Iterate over all matching files in the backup directory
    for backup_file in backup_dir.glob(search_pattern):
        if not backup_file.is_file():
            continue
            
        # Define the target path in the Apache configuration directory
        target_path = apache_conf_dir / backup_file.name

        restoration_needed = compare_files(target_path, backup_file)
        if not restoration_needed:
            continue

        # Check if the file already exists and prompt for overwrite
        if target_path.exists():
            user_input = input(f"File '{target_path}' already exists. Overwrite? [y/N]: ").strip().lower()
            if user_input != 'y':
                print(f"Skipped restoring '{backup_file.name}'.")
                continue
                
        # Copy the backup file to the Apache directory (preserving metadata)
        try:
            shutil.copy2(backup_file, target_path)
            print(f"Successfully restored '{backup_file.name}'.")
        except Exception as e:
            print(f"Error restoring '{backup_file.name}': {e}")
    
    remove_token_file(apache_conf_dir)
    restart_apache()


#==============================================================================
if __name__ == "__main__":

    p = argparse.ArgumentParser(description=__doc__,
               # formatter used to preserve the raw doc format
               formatter_class=argparse.RawTextHelpFormatter)
    g = p.add_mutually_exclusive_group()
    p.add_argument("-v", "--version", action='version', 
               version='%(prog)s version {version}'.format(version=__version__))
    g.add_argument("-m", "--maintenance", 
                   help="direct all PHP websites to a static maintenance page", 
                   action="store_true")
    g.add_argument("-r", "--recover", 
                   help="recover websites from timestamped backup folder", 
                   action="store_true")
    args = p.parse_args()

    script_folder = os.path.dirname(os.path.realpath(__file__))
    paramsfile = script_folder + "/php_killswitch_config.ini"
    print("Reading:", paramsfile)
    is_file_or_abort(paramsfile)
    # Read configuration from the .ini file
    config = configparser.ConfigParser()
    config.read(paramsfile)
    # Define paths according to your Ubuntu environment
    apache_conf_dir = Path(config.get("directories", "apache_conf_dir"))
    backup_dir = Path(config.get("directories", "backup_dir"))
    maintenance_dir = Path(config.get("directories", "maintenance_dir"))

    if args.maintenance:
        print_line('-')
        print("Direct all websites using PHP to a static maintenance page.")
        print("Treat Apache configs in:  ", apache_conf_dir)
        print("Save Apache configs in:   ", backup_dir)
        print("Maintenance document root:", maintenance_dir)
        query_continue()
        set_php_sites_to_maintenance(apache_conf_dir, backup_dir, maintenance_dir)
    elif args.recover:
        print_line('-')
        print("Recover Apache configuration files from backup.")
        print("Treat Apache configs in:  ", apache_conf_dir)
        print("Backup directory:         ", backup_dir)
        timestamps = show_timestamps(backup_dir)
        if not timestamps:
            print("There are no config backups. Recovering not possible.")
            quit()
        if len(timestamps) == 1:
            print("There is just one backup.")
            timestamp = timestamps[0]
        else:
            timestamp = input("Enter timestamp (format: YYYY-MM-DD_HH-MM): ").strip()

        backup_dir = backup_dir / timestamp
        print(f"Recover configs from {backup_dir}?")
        query_continue()
        restore_php_sites_from_backup(apache_conf_dir, backup_dir) 
    else:
        abort("Enter either --maintenance (-m) or --recover (-r)")

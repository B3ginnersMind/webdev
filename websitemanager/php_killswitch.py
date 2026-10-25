#!/usr/bin/env python3
import os
import sys
import shutil
import re
import subprocess
import datetime
from pathlib import Path

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
        
    # Create backup directory if it does not exist
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. Perform backup of all *.conf files
    current_time = datetime.datetime.now()
    timestamp = current_time.strftime('%d-%m-%Y_%H-%M')
    
    for conf_file in apache_conf_dir.glob("*.conf"):
        if conf_file.is_file():
            backup_filename = f"{conf_file.name}.{timestamp}"
            backup_path = backup_dir / backup_filename
            shutil.copy2(conf_file, backup_path)
            
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
            
    # 6. Test configuration and restart Apache
    print("Testing Apache configuration...")
    # apache2ctl configtest writes its output primarily to stderr
    test_result = subprocess.run(["apache2ctl", "configtest"], capture_output=True, text=True)
    
    if test_result.returncode == 0:
        print("Configuration OK. Restarting Apache...")
        subprocess.run(["apache2ctl", "restart"], check=True)
    else:
        print("Error: Apache configuration test failed! Restart aborted.")
        print(test_result.stderr)
        
    # 7. Print the collected configuration data to stdout
    print("\n--- Collected Configuration Data ---")
    for data_tuple in conf_data:
        print(data_tuple)

def restore_php_sites_from_backup(
    timestamp: str, 
    apache_conf_dir: Path, 
    backup_dir: Path
) -> None:
    
    # Check if the backup directory exists
    if not backup_dir.is_dir():
        print(f"Error: Backup directory '{backup_dir}' does not exist.")
        return

    # Define the search pattern based on the provided timestamp
    search_pattern = f"*.conf.{timestamp}"
    suffix_to_remove = f".{timestamp}"
    
    # Iterate over all matching files in the backup directory
    for backup_file in backup_dir.glob(search_pattern):
        if not backup_file.is_file():
            continue
            
        # Strip the suffix ".{timestamp}" from the filename
        original_filename = backup_file.name
        if original_filename.endswith(suffix_to_remove):
            original_filename = original_filename[:-len(suffix_to_remove)]
            
        # Define the target path in the Apache configuration directory
        target_path = apache_conf_dir / original_filename
        
        # Check if the file already exists and prompt for overwrite
        if target_path.exists():
            user_input = input(f"File '{target_path}' already exists. Overwrite? [y/N]: ").strip().lower()
            if user_input != 'y':
                print(f"Skipped restoring '{original_filename}'.")
                continue
                
        # Copy the backup file to the Apache directory (preserving metadata)
        try:
            shutil.copy2(backup_file, target_path)
            print(f"Successfully restored '{original_filename}'.")
        except Exception as e:
            print(f"Error restoring '{original_filename}': {e}")

# --- Example execution block ---
if __name__ == "__main__":
    # Define paths according to your Ubuntu environment
    APACHE_DIR = Path("/etc/apache2/sites-available")
    BACKUP_DIR = Path("/etc/apache2/sites-backup")
    MAINTENANCE_DIR = Path("/var/www/maintenance")
    
    set_php_sites_to_maintenance(
        apache_conf_dir=APACHE_DIR,
        backup_dir=BACKUP_DIR,
        maintenance_dir=MAINTENANCE_DIR
    )
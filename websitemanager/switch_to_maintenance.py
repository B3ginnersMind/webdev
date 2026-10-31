#!/usr/bin/env python3
"""
-------------------------------------------------------------------------------
Switch between the original website and a maintenance page by renaming folders.
The script reads the configuration from the file switch_to_maintenance.ini.
It contains a list of website docroots. See demo_switch_to_maintenance.ini.
The folder to be treated can be chosen interactively.

Docroot folders with suffixes "_maintenance" or "_original" are used for backup.
To be able to do the switching a docroot with and without suffix "_maintenance"
must be present. Place a file "index.html" within the _maintenance folder which
should contain the maintenance message for the website visitors.

The switching is done by renaming:
docroot -> docroot_original
docroot_maintenance -> docroot

Switching back is done by renaming:
docroot -> docroot_maintenance
docroot_original -> docroot

The tool always flips the current state. 
On start-up the current state of the website folders is shown.

Benefits:
- The URL remains online and certbot may renew the certificate.
- A CMS which is not under active development is protected from hacking.
-------------------------------------------------------------------------------
"""
import argparse
import configparser
import os
from pathlib import Path
from wm.utils import abort, check_root_user, query_int

__version__ = "1.0.0"
INI_FILE_NAME = "switch_to_maintenance_config.ini"
    

def main():
    p = argparse.ArgumentParser(description=__doc__,
                # formatter used to preserve the raw doc format
                formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("-v", "--version", action='version', 
                version='%(prog)s version {version}'.format(version=__version__))
    p.add_argument("-s", "--show", help="show the state of the docroots and exit", 
                action="store_true")
    args = p.parse_args()

    script_folder = os.path.dirname(os.path.realpath(__file__))
    ini_path = Path(script_folder) / INI_FILE_NAME
    
    # Check if the INI file exists
    if not ini_path.is_file():
        abort(f"Error: Configuration file '{INI_FILE_NAME}' not found.")

    # Read from section [switchable_doc_roots] of the ini file
    config = configparser.ConfigParser()
    print("Reading configuration from:", ini_path)
    config.read(ini_path)

    if "switchable_doc_roots" not in config:
        abort("Error: Section [switchable_doc_roots] missing in INI file.")

    section = config["switchable_doc_roots"]
    run_as_root = section.getboolean("run_as_root", fallback=False)
    server_root_raw = section.get("server_root", fallback="")
    doc_folders_raw = section.get("doc_folders", fallback="")

    if (not server_root_raw.strip() or not doc_folders_raw.strip()):
        abort("Error: Missing 'server_root' or 'doc_folders' in INI file.")
    if run_as_root:
        check_root_user()

    server_root = Path(server_root_raw.strip())
    doc_folders = [
        folder.strip()
        for folder in doc_folders_raw.split(",")
        if folder.strip()
    ]
    if not doc_folders:
        abort("Error: 'doc_folders' list is empty.")

    def get_status(folder: str) -> str:
        base_dir = server_root / folder
        original_dir = server_root / (folder + "_original")
        maint_dir = server_root / (folder + "_maintenance")
        if base_dir.is_dir():
            if original_dir.is_dir():
                return "Maintenance"
            elif maint_dir.is_dir():
                return "Original"
            else:
                return "Unknown"
        else:
            return "Missing"

    # Print doc_folders to stdout together with indices
    print("Available document folders:")
    for idx, folder in enumerate(doc_folders):
        status = get_status(folder)
        print(f"  [{idx}] {folder} ({status})")

    if args.show:
        quit()

    # Query the index of the doc_folder to be treated
    index = query_int("Enter the index of the document folder to process", 
                      0, len(doc_folders) - 1)
    # base_dir is the actual DocumentRoot of the website to be treated
    doc_folder = doc_folders[index]
    base_dir = server_root / doc_folder
    # Test whether base_dir is a directory
    if not base_dir.is_dir():
        abort(f"Error: Directory '{base_dir}' does not exist.")

    cms_dir = server_root / (doc_folder + "_original")
    maint_dir = server_root / (doc_folder + "_maintenance")
    if cms_dir.is_dir() and maint_dir.is_dir():
        abort(f"Only one of {cms_dir.name} and {maint_dir.name} should exist.")
    print(f"Backup directory for the CMS: {cms_dir}")
    print(f"Backup directory for the maintenance page: {maint_dir}")

    # Switch back to CMS mode
    if cms_dir.is_dir():
        print(f"'{base_dir}' switched back to original website.")
        base_dir.rename(maint_dir)
        cms_dir.rename(base_dir)

    # Switch to maintenance mode
    elif maint_dir.is_dir():
        print(f"'{base_dir}' switched to maintenance.")
        base_dir.rename(cms_dir)
        maint_dir.rename(base_dir)

    else:
        abort(f"Maintenance folder still has not been set up in '{base_dir}'.")


if __name__ == "__main__":
    main()
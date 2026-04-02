# MediaWiki Update Script

## Overview

`mediawiki_update.py` is an automated tool for updating a live MediaWiki installation to a new version. It handles the entire update workflow including downloading the new release, managing extensions and skins, and executing the database migration scripts.

**Version:** 1.07

## Purpose

This script streamlines the MediaWiki upgrade process by:
- Downloading the new MediaWiki release
- Detecting version information for both live and new installations
- Identifying and fetching missing extensions and skins
- Preserving live site configuration and data
- Setting proper file permissions
- Running database update scripts
- All while maintaining a live website during the transition

## Requirements

- **Python:** 3.10 or later
- **OS:** Linux or Linux-based systems (FreeBSD and OpenBSD are untested)
- **Privilege:** Root access (recommended for proper permission management)
- **PHP:** Compatible PHP version for the target MediaWiki release

## Configuration

The script reads configuration from an INI file (default: `mediawiki_update.ini`). Each section defines one MediaWiki installation.

### Configuration File Format

```ini
[mysite]
mw_folder_live = /var/www/mywebsite          # Current live MediaWiki root
mw_basefolder_new = /home/user/mediawiki     # Base folder for new release
release_new = 1.45.1                         # Target MediaWiki version
php_command = php8.2                         # PHP command for this version
user_owner = www-data                        # File owner user
group_owner = www-data                       # File owner group
dir_mode = 0o750                             # Directory permissions
file_mode = 0o640                            # File permissions
```

### Configuration Parameters

| Parameter | Description |
|-----------|-------------|
| `mw_folder_live` | Absolute path to the current live MediaWiki installation |
| `mw_basefolder_new` | Base directory where new MediaWiki versions are stored |
| `release_new` | Target MediaWiki version to update to (e.g., 1.45.1) |
| `php_command` | PHP executable command compatible with the target version |
| `user_owner` | System user that should own MediaWiki files |
| `group_owner` | System group that should own MediaWiki files |
| `dir_mode` | Unix permissions for directories (octal notation) |
| `file_mode` | Unix permissions for files (octal notation) |

## Usage

### Basic Command

```bash
python mediawiki_update.py <section_name>
```

### With Custom Config File

```bash
python mediawiki_update.py -c /path/to/custom_config.ini <section_name>
```

### Get Help

```bash
python mediawiki_update.py -h
```

### Check Version

```bash
python mediawiki_update.py -v
```

### Example

```bash
python mediawiki_update.py newhomoeopedia
```

This reads the `[newhomoeopedia]` section from `mediawiki_update.ini` and performs the update.

## Update Process

The script follows these steps:

1. **System Check**
   - Verifies the script runs on a Linux-based system
   - Warns if not run as root
   - Checks if Python version is 3.10+

2. **Configuration Loading**
   - Reads the specified configuration section
   - Validates all configuration parameters
   - Displays configuration for user review

3. **Version Detection**
   - Detects the current live MediaWiki version
   - Confirms configuration validity before proceeding

4. **Pre-Update Validation**
   - Performs tests to ensure the system is ready for update
   - Requests user confirmation before making changes

5. **Download & Preparation**
   - Downloads the target MediaWiki release
   - Verifies the downloaded version matches the requested version
   - Identifies missing extensions in the new codebase
   - Identifies missing skins in the new codebase
   - Fetches missing extensions and skins from offical sources

6. **Data Migration**
   - Copies live site data (configuration, user data, etc.) to the new installation

7. **Permission Management**
   - Sets proper file ownership (user and group)
   - Applies correct file and directory permissions

8. **Filesystem Exchange**
   - Swaps the old live folder with the new one
   - Prepares the system for database migration

9. **Database Update**
   - Runs MediaWiki's database update scripts (`run.php update`)
   - Completes the migration process

## Logging

The script maintains detailed logs:
- **Output:** Logged to both console and `mediawiki_update.log`
- **Format:** Timestamp, log level, and message
- **Levels:** INFO for standard operations, WARNING for cautions, ERROR for failures

## Key Components

The script uses a modular architecture with several supporting modules:

| Module | Purpose |
|--------|---------|
| `mu.utils` | Utility functions (config reading, permissions, etc.) |
| `mu.dataclasses` | Data structures (Release, UpdateData) |
| `mu.mediawiki_fetcher` | Downloads MediaWiki releases |
| `mu.mediawiki_version_detector` | Detects installed versions |
| `mu.missing_folders` | Identifies missing extensions/skins |
| `mu.extension_fetcher` | Fetches missing extensions |
| `mu.skin_fetcher` | Fetches missing skins |
| `mu.constants` | Configuration constants (URLs, etc.) |

## Safety Features

- **User Confirmation:** Requires explicit user confirmation before making changes
- **Backup Reminder:** Prompts user to confirm backup before proceeding
- **Version Verification:** Validates downloaded version matches requested version
- **Maintenance Script Check:** Verifies database update scripts exist before proceeding
- **Non-destructive:** Preserves live site data during the update process

## Error Handling

The script:
- Checks for missing database update scripts and exits gracefully
- Validates version information and raises errors on mismatches
- Aborts on unsupported operating systems
- Logs all operations for troubleshooting

## Example Workflow

```bash
# 1. Prepare configuration file
cp mediawiki_update.txt mediawiki_update.ini
# Edit mediawiki_update.ini with your settings

# 2. Run the update
python mediawiki_update.py mywebsite

# 3. Script will:
#    - Display current and target versions
#    - Prompt for backup confirmation
#    - Download and prepare new release
#    - Fetch extensions and skins
#    - Migrate data
#    - Update permissions
#    - Run database migrations

# 4. Check the log file
cat mediawiki_update.log
```

## Notes

- No quotes should be used around string values in the configuration file
- The script is designed for production environments and expects proper backup procedures
- Always review the logs after an update
- The script handles multiple MediaWiki installations through separate configuration sections

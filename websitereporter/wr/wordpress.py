import json, os, subprocess, sys
import urllib.error, urllib.parse, urllib.request
from wr.config import settings
from wr import utils as u
from wr.utils import CmsPaths
from pathlib import Path
from typing import Any, Optional
_VERBOSE = False

# Important to use the pool owner to prevent damage if the site has been hacked.
def wp_cli(owner: str) -> str:
    """
    Returns the wp-cli command.
    """
    if settings.run_as_root:
        return f"sudo -u {owner} " + settings.wp_cli
    return settings.wp_cli

def check_wp_plugins_status(dir: Path) -> dict[str, list[Any]]:
    """
    Run "plugin list --format=json" of WP-CLI and check each plugin slug 
    against the official WordPress.org API. Detect whether a plugin is
    active, closed, or not contained at WordPress.org.
    """
    results: dict[str, list[Any]] = {
        "active_org": [],
        "closed_org": [],
        "not_on_org": [],
        "errors": []
    }
    command = f"{wp_cli(str(dir.owner()))} plugin list --format=json" # type: ignore
    u.print_dots()        
    print(f"--> Command: {command}")
    cmd: list[str] = command.split()
    try:
        # cmd: list[str] = ["sudo", "-u", "www-data", "wp", "plugin", "list", "--format=json", f"--path={dir}"]
        process = subprocess.run(cmd, capture_output=True, text=True, check=True)
        installed_plugins: list[dict[str, Any]] = json.loads(process.stdout)
    except Exception as e:
        print("error", f"Exception: {e}")
        results["errors"].append(f"Exception: {e}")
        return results

    print(f"--> Checking whether plugins are active, closed, or not contained at WordPress.org")
    def check_single_plugin(plugin_data: dict[str, Any]) -> None:
        slug: Optional[str] = plugin_data.get("name")
        version: Optional[str] = plugin_data.get("version")
        if not slug:
            return

        if _VERBOSE:
            print(f"Prüfe Plugin: {slug} (Version: {version})")
        # Use URL encoding for square brackets
        query_params = urllib.parse.urlencode({
            "action": "plugin_information",
            "request[slug]": slug
        })
        api_url: str = f"https://api.wordpress.org/plugins/info/1.2/?{query_params}"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Python-WP-Checker'})
        if _VERBOSE:
            print(api_url)
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                # Status 200 OK: Plugin is active
                data: dict[str, Any] = json.loads(response.read().decode('utf-8'))
                entry: dict[str, Any]  = {"slug": slug, "version": version}
                if data.get("last_updated"):
                    entry["last_updated"] = str(data.get("last_updated")).split()[0]
                results["active_org"].append(entry)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Read the body of the 404 error message!
                try:
                    error_body = e.read().decode('utf-8')
                    error_data = json.loads(error_body)
                    
                    # Check if the 404 JSON indicates the plugin is "closed"
                    if error_data.get("closed"):
                        results["closed_org"].append({
                            "slug": slug,
                            "version": version,
                            "closed_date": error_data.get("closed_date"),
                            "reason": error_data.get("reason")
                        })
                    else:
                        # 404 and not ‘closed’ -> genuine purchase/private plugin
                        results["not_on_org"].append({"slug": slug, "version": version})
                        
                except json.JSONDecodeError:
                    # If the 404 body was not valid JSON
                    results["not_on_org"].append({"slug": slug, "version": version})
            else:
                results["errors"].append(f"HTTP-Fehler {e.code} bei '{slug}'")
                
        except Exception as e:
            results["errors"].append(f"Netzwerk-Fehler bei '{slug}': {e}")

    for plugin_data in installed_plugins:
        check_single_plugin(plugin_data)

    return results

def print_as_table(data: list[dict[str, str]]):
    if not data:
        return

    # Extract column names (keys) from the first dictionary
    keys = list(data[0].keys())

    # Calculate the maximum width for each column
    # We’ll start with the length of the column name itself
    col_widths = {key: len(key) for key in keys}
    
    for row in data:
        for key in keys:
            # If a value is longer than the current maximum width, update
            val_len = len(str(row.get(key, "")))
            if val_len > col_widths[key]:
                col_widths[key] = val_len

    # Display header. ljust() pads the string with spaces up to specified width
    header = "  ".join(key.ljust(col_widths[key]) for key in keys)
    print(header)

    # Output data rows
    for row in data:
        row_str = "  ".join(str(row.get(key, "")).ljust(col_widths[key]) for key in keys)
        print(row_str)

def check_wordpress_sites(cms: CmsPaths):
    if len(cms.wordpress_sites) == 0:
        u.print_headline("Wordpress sites: none")
    else:
        u.print_headline("Wordpress sites:")
    for dir in cms.wordpress_sites:
        u.print_double_line()
        print("==> Wordpress website at:", dir)
        owner = str(dir.owner())  # type: ignore
        print("Owner:", owner)
        os.chdir(dir)
        if u.has_basic_auth(dir):
            print("--> WEBSITE PROTECTED BY BASIC AUTH")
        u.run_command(f"{wp_cli(owner)} core version")
        u.run_command(f"{wp_cli(owner)} core check-update")
        u.run_command(f"{wp_cli(owner)} core verify-checksums")
        u.run_command(f"{wp_cli(owner)} plugin verify-checksums --all")
        u.run_command(f"{wp_cli(owner)} plugin list")
        u.run_command(f"{wp_cli(owner)} theme list")
        # u.run_command(f"{wpcli(owner)} plugin status")
        report: dict[str, list[Any]] = check_wp_plugins_status(dir)

        if len(report['closed_org']):
            print("\n🔴 Geschlossene / Gefährdete Plugins (wordpress.org) ---")
            print_as_table(report["closed_org"])
        if len(report['not_on_org']):
            print("\n🟡 Kauf-Plugins / Nicht auf wordpress.org ---")
            print_as_table(report["not_on_org"])
        if len(report['active_org']):
            print(f"\n🟢 Aktive wordpress.org Plugins: {len(report['active_org'])} ---")
            print_as_table(report['active_org'])
        if len(report['errors']):
            print_as_table(report['errors'])

        if settings.show_cms_users:
            u.print_dots()
            value = u.get_shell_command_output(f"{wp_cli(owner)} user list --format=count")
            if value and value[0].isdigit():
                num_users = int(value[0])
                max_users = 50
                print("Number of users:", num_users)
                if num_users > max_users:
                    print(f"Over {max_users} Wordpress users: Only show administrators")
                    u.run_command(f"{wp_cli(owner)} user list --role=administrator")
                else:
                    u.run_command(f"{wp_cli(owner)} user list")           
        if settings.wordfence_cli != "none":
           u.run_command(f"{settings.wordfence_cli} vuln-scan --no-banner .")

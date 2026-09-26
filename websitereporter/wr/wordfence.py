import os
import datetime
import sqlite3
from pathlib import Path
from typing import Any
from wr.utils import print_dots
from wr.release import Release

LEN_TITLE = 65
LEN_LINE = 130
# Set to True for detailed output, False for minimal output
_VERBOSE2 = False 
_VERBOSE1 = False 

def is_wordfence_db_ok(db_file: Path) -> bool:
    print_dots()
    print(f"Test the database file at: {db_file.absolute()}")
    if not os.path.exists(db_file):
        print(f"Error: Database '{db_file}' missing.")
        return False
    mtime_timestamp = os.path.getmtime(db_file)
    mtime_readable = datetime.datetime.fromtimestamp(mtime_timestamp)
    print(f"Database '{db_file}' last modified: {mtime_readable:%Y-%m-%d %H:%M}")

    try:
        with sqlite3.connect(db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM plugin_vulns")
            num_cve_lines = cursor.fetchone()[0]
            print(f"Number of CVE lines in database: {num_cve_lines}")
    except Exception as e:
        print("error", f"Fehler: {e}")
        return False
    return True

def check_wp_components_status(installed_components: list[dict[str, Any]], 
                               comp_type: str,
                               db_file: Path) -> None:
    if not installed_components:
        print(f"No installed {comp_type}s found")
        return

    conn = sqlite3.connect(db_file)
    # row_factory ensures that we can access data using column names rather than just indices
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    vuln: list[dict[str, Any]] = []

    #--------------------------------------------------------------
    # Function to check each plugin's version against the database
    #--------------------------------------------------------------
    def check_component(slug: str, version: str) -> None:
        if _VERBOSE2:
            print(f"Prüfe Plugin: '{slug}' (Version: {version})")
        if not slug:
            return
        comp_version = Release(version)
        if comp_version.is_nonnumeric:
            if _VERBOSE1:
                print(f"Non-numeric version for plugin '{slug}': {repr(comp_version)}")
            return
        cursor.execute("SELECT * FROM plugin_vulns WHERE slug = ?", (slug,))
        rows = cursor.fetchall()
        if _VERBOSE2:
            num_selected = len(rows)
            print(f"Found {num_selected} CVEs for plugin '{slug}'")
        if not rows:
            if _VERBOSE2:
                print(f"No CVEs for Plugin '{slug}' found.")
            return

        for row in rows:
            patch_version = Release(row['patched_version'])
            add_warning = False
            if patch_version.is_nonnumeric:
                if comp_version.is_greater_than(row['patched_version']):
                    continue  # CVE already fixed.
                else:
                    add_warning = True
                    if _VERBOSE1:
                        print(f"{repr(patch_version)} of component '{slug}' patched {row['cve']}.")
                        print(f"{repr(comp_version)} is the installed version.")
                continue
            if patch_version > comp_version:
                add_warning = True

            if add_warning:    
                title = row['title'][:LEN_TITLE] + ".." if len(row['title']) > LEN_TITLE else row['title']

                vuln.append({"slug": slug, "version": version, "cve": row['cve'], "severe": row['cvss_severity'],
                             "published": row['published'], "type": row['software_type'], 
                             "patch": row['patched_version'], "title": title})
                if _VERBOSE1:
                    print(f"Plugin '{slug}' version {version} vulnerable to: {row['cve']} (patched in {row['patched_version']})")
    # end check_component

    for plugin_data in installed_components:
        slug: str = str(plugin_data.get("name"))
        version: str = str(plugin_data.get("version"))
        check_component(slug, version)
    if not vuln:
        print(f"No vulnerabilities found in wordfence for {comp_type}s")
        return
    print("-" * LEN_LINE)
    print(f"{'Slug':<15} | {'Version':<7} | {'Severe':<8} | {'Published':10} | {'Patch':<9} | {'Title'}")
    print("-" * LEN_LINE)
    for v in vuln:
        # omitted {v['cve']:<15}  {v['type']}
        print(f"{v['slug']:<15} | {v['version']:<7} | {v['severe']:<8} | {v['published']:10} | "
              f"{v['patch']:<9} | {v['title']}")
    return

def check_vulnerabilities_from_wordfence(db_file: Path, path_to_wp: Path = Path(".")):
    from wr.wordpress import get_component_json
    if not is_wordfence_db_ok(db_file):
        return
    print("Looking for vulnerabilities of WordPress components in Wordfence DB...")
    installed_components = get_component_json("plugin", path_to_wp)
    check_wp_components_status(installed_components, "plugin", db_file)
    installed_components = get_component_json("theme", path_to_wp)
    check_wp_components_status(installed_components, "theme", db_file)

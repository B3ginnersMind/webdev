import os
import datetime
import sqlite3
from pathlib import Path
from typing import Any
from wr.utils import print_dots
from wr.release import Release

LEN_TITLE = 65
LEN_LINE = 130

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
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    vuln: list[dict[str, Any]] = []

    def check_component(slug: str, version: str) -> None:
        if not slug:
            return
        comp_version = Release(version)
        if comp_version.is_nonnumeric:
            return
        
        cursor.execute("SELECT * FROM plugin_vulns WHERE slug = ?", (slug,))
        rows = cursor.fetchall()
        if not rows:
            return

        # Helper function for creating the warning entry
        def append_vuln_entry(r: sqlite3.Row):
            t = r['title'][:LEN_TITLE] + ".." if len(r['title']) > LEN_TITLE else r['title']
            vuln.append({
                "slug": slug, "version": version, "cve": r['cve'], 
                "severe": r['cvss_severity'], "published": r['published'], 
                "type": r['software_type'], "patch": r['patched_version'], "title": t
            })

        # 1. Group database rows by CVE (or ID, if the CVE is None)
        cve_groups: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            # Some vulnerabilities do not have a CVE; in such cases, we use the ID as the key
            cve_key = row['cve'] if row['cve'] else f"NO_CVE_{row['id']}"
            if cve_key not in cve_groups:
                cve_groups[cve_key] = []
            cve_groups[cve_key].append(row)

        # 2. Process each CVE group
        for cve_key, cve_rows in cve_groups.items():
            
            # --- CASE A: There is only ONE patched version for this CVE ---
            if len(cve_rows) == 1:
                row = cve_rows[0]
                patch_version = Release(row['patched_version'])
                
                if patch_version.is_nonnumeric:
                    # Handling of non-numeric patch versions
                    if not comp_version.is_greater_than(row['patched_version']):
                        append_vuln_entry(row)
                else:
                    if patch_version > comp_version:
                        append_vuln_entry(row)

            # --- CASE B: There are SEVERAL patched versions for the same CVE (e.g. Free & Pro) ---
            else:
                # Filter comparable release objects from the rows
                comparable_patches: list[tuple[Release, sqlite3.Row]] = []
                nonnumeric_patches: list[tuple[Release, sqlite3.Row]] = []
                for r in cve_rows:
                    rel = Release(r['patched_version'])
                    if rel.is_nonnumeric:
                        nonnumeric_patches.append((rel, r))
                    else:
                        comparable_patches.append((rel, r))
                
                if not comparable_patches:
                    for rel, r in nonnumeric_patches:
                        if not comp_version.is_greater_than(r['patched_version']):
                            append_vuln_entry(r)
                    continue

                # Sort by release object to determine the minimum and maximum
                comparable_patches.sort(key=lambda item: item[0])
                
                patch_version_min, row_min = comparable_patches[0]
                patch_version_max, row_max = comparable_patches[-1]

                # comp_version < patch_version_min -> 1 warning entry (min)
                if comp_version < patch_version_min:
                    append_vuln_entry(row_min)

                # comp_version >= patch_version_max -> no warning entry
                elif comp_version >= patch_version_max:
                    pass  # system has been patched securely

                # patch_version_min <= comp_version < patch_version_max 
                # -> 2 warning entries (min & max)
                # also check non-numeric patches for additional warnings
                elif patch_version_min <= comp_version < patch_version_max:
                    append_vuln_entry(row_min)
                    append_vuln_entry(row_max)
                    for rel, r in nonnumeric_patches:
                        if not comp_version.is_greater_than(r['patched_version']):
                            append_vuln_entry(r)

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

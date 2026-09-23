#!/usr/bin/env python
"""
--------------------------------------------------------------------------------
Update the Wordfence vulnerability database in JSON format and convert it into a
memory-optimized SQLite database. The JSON file is downloaded from the Wordfence
API. The SQLite database is used for fast lookups of plugin vulnerabilities.
--------------------------------------------------------------------------------
The HTTP caching header `ETag` ist stored, which is an identifier for 
a specific version of a resource. This is sent along with the next request, 
so that the web server can check whether there is a new version of the resource
at all. The server then responds either with the new file or with an empty 
HTTP status 304 (Not Modified). By setting
  headers[“If-None-Match”] = etag 
in
  response = requests.get(FEED_URL, headers=headers, stream=True, timeout=30)
this header is included in the request.

Note: This may not prevent us from exceeding the Wordfence rate limit!

Setting 'stream=True' and 'iter_content' causes the script to download the 
file in chunks of 8-kilobyte blocks and write it directly to the hard drive. 
If one were to use 'response.json()' instead, Python would first have to 
store the entire huge document in memory (RAM), which, on 
small web servers, would quickly cause your script to crash.
--------------------------------------------------------------------------------
"""
import gc # Garbage Collector
import json, os, requests, sqlite3, time
from pathlib import Path
from wr.config import read_config, settings

def update_vulnerability_database():
    currenttime = time.strftime('%d.%m.%Y %H:%M:%S')
    print(f"Attempting to refresh the Wordfence vulnerability data as JSON file at {currenttime}")

    # 1. Always include the Token with every request
    headers = {'Authorization': f'Bearer {settings.wf_api_token}' }
    
    # 2. Add ETag for caching
    if os.path.exists(settings.wf_etag_file) and os.path.exists(settings.wf_json_file):
        with open(settings.wf_etag_file, 'r') as f:
            etag = f.read().strip()
            headers['If-None-Match'] = etag
            print(f"Cached version found (ETag: {etag}). Checking for updates...")

    try:
        # Send the request (Headers are passed, stream=True is important)
        response = requests.get(settings.wf_feed_url, headers=headers, stream=True, timeout=30)
        if response.status_code == 304:
            print("[OK] Status 304: Local data is up to date.")
            return True
            
        elif response.status_code == 200:
            print("[OK] Status 200: Downloading new JSON file...")
            new_etag = response.headers.get('ETag')

            with open(settings.wf_json_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if new_etag:
                with open(settings.wf_etag_file, 'w') as f:
                    f.write(new_etag)
            return True
            
        elif response.status_code == 429:
             print("[Error] Rate limit reached. Too many requests have been made.")
             return False
             
        else:
            print(f"[Error] Unexpected HTTP status: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[Error] Network problem: {e}")
        return False

# ------------------------------------------------------------------------------
def build_flat_sqlite_memory_optimized():
    if not os.path.exists(settings.wf_json_file):
        print(f"JSON file missing: {settings.wf_json_file}")
        return

    # 1. setup database
    conn = sqlite3.connect(settings.wf_db_file)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS plugin_vulns")
    
    # Flat table: everything in a single row.
    cursor.execute('''
        CREATE TABLE plugin_vulns (
            id TEXT,
            cve TEXT,
            title TEXT,
            cvss_score REAL,
            cvss_severity TEXT,
            published TEXT,
            software_type TEXT,
            slug TEXT,
            patched_version TEXT
        )
    ''')

    print("Read JSON into memory...")
    # This is the only time we load the large file.
    with open(settings.wf_json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("Start a memory-efficient import in small batches...")
    
    batch: list[tuple[str, str, str, float, str, str, str, str, str]] = []
    batch_size = 2000  # Alle 2000 Einträge wird in die DB geschrieben
    total_inserted = 0

    # 2. Iterate through the dictionary
    for vuln_id, vuln_data in data.items():
        title = vuln_data.get("title", "Unknown")
        cve = vuln_data.get("cve")
        published = vuln_data.get("published")
        
        cvss_score = 0.0
        cvss_severity = "Unknown"
        if "cvss" in vuln_data and vuln_data["cvss"]:
            cvss_score = float(vuln_data["cvss"].get("score", 0.0))
            cvss_severity = vuln_data["cvss"].get("rating", "Unknown")

        # Unpack the vector: there is a new line for each plugin concerned.
        for sw in vuln_data.get("software", []):
            sw_type = sw.get("type")
            slug = sw.get("slug")
            
            patched_version = "Unpatched"
            if "patched_versions" in sw and sw["patched_versions"]:
                patched_version = sw["patched_versions"][0]

            # We only include it if a slug exists
            if slug:
                batch.append((
                    vuln_id, cve, title, cvss_score, cvss_severity, 
                    published[:10], sw_type, slug, patched_version
                ))

        # --- RAM protection: Batch insert ---
        # As soon as we've collected 2000 lines, let's pop them into the database.
        if len(batch) >= batch_size:
            cursor.executemany('''
                INSERT INTO plugin_vulns 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', batch)
            conn.commit()  # Write to disc.
            total_inserted += len(batch)
            batch.clear()  # Clear list in RAM.

    # 3. Insert the remainder 
    if batch:
        cursor.executemany('''
            INSERT INTO plugin_vulns 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', batch)
        conn.commit()
        total_inserted += len(batch)
        batch.clear()

    # 4.  Create a search index for efficient database queries.
    print("Create an index for fast searches...")
    cursor.execute("CREATE INDEX idx_slug ON plugin_vulns (slug)")
    cursor.execute("CREATE INDEX idx_type ON plugin_vulns (software_type)")

    # 5. Tidying up.
    conn.commit()
    conn.close()
    
    # Delete the large JSON object and call the garbage colletion.
    del data
    gc.collect()

    print(f"Finished: {total_inserted} entries written into the database.")

if __name__ == "__main__":
    read_config(Path(__file__).parent / "website_reporter_config.ini")
    if settings.run_as_root and os.getuid() != 0: # type: ignore
        print(f"Skript not run as root. Exiting...")
        quit()

    # Update the Feed (or download initially)
    success = update_vulnerability_database()
    if success:
        currenttime = time.strftime('%d.%m.%Y %H:%M:%S')
        print(f"Database JSON downloaded successfully at {currenttime}")
        build_flat_sqlite_memory_optimized()
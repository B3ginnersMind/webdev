#!/usr/bin/env python
"""
----------------------------------------------------------------------------------
Update the Wordfence vulnerability database in JSON format and convert it into a
memory-optimized SQLite database. The JSON file is downloaded from the Wordfence
API and is then processed to reduce its size. The SQLite database is used for fast
lookups of plugin vulnerabilities.
----------------------------------------------------------------------------------
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
----------------------------------------------------------------------------------
"""
import gc # Garbage Collector
import json, os, requests, sqlite3, time
from enum import Enum
from pathlib import Path
from wr.config import read_config, settings

class Return(Enum):
    NEW = 1
    UP_TO_DATE = 2
    ERROR = 3

#-------------------------------------------------------------------------------
def update_vulnerability_database(json_file: Path, etag_file: Path) -> Return:
    currenttime = time.strftime('%d.%m.%Y %H:%M:%S')
    print(f"Attempting to refresh the Wordfence vulnerability JSON at {currenttime}")

    # 1. Always include the Token with every request
    headers = {'Authorization': f'Bearer {settings.wf_api_token}' }
    
    # 2. Add ETag for caching
    if os.path.exists(etag_file) and os.path.exists(json_file):
        with open(etag_file, 'r') as f:
            etag = f.read().strip()
            headers['If-None-Match'] = etag
            print(f"Cached version found (ETag: {etag}). Checking for updates...")

    try:
        # Send the request (Headers are passed, stream=True is important)
        response = requests.get(settings.wf_feed_url, headers=headers, 
                                stream=True, timeout=30)
        if response.status_code == 304:
            print("[OK] Status 304: Local data is up to date.")
            return Return.UP_TO_DATE
            
        elif response.status_code == 200:
            print("[OK] Status 200: Downloading new JSON file...")
            new_etag = response.headers.get('ETag')

            with open(json_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if new_etag:
                with open(etag_file, 'w') as f:
                    f.write(new_etag)
            return Return.NEW
            
        elif response.status_code == 429:
             print("[Error] Rate limit reached. Too many requests have been made.")
             return Return.ERROR
             
        else:
            print(f"[Error] Unexpected HTTP status: {response.status_code}")
            return Return.ERROR
            
    except requests.exceptions.RequestException as e:
        print(f"[Error] Network problem: {e}")
        return Return.ERROR

#-------------------------------------------------------------------------------
def downsize_wordfence_json(json_full: Path, json_reduced: Path, 
                            keys_to_remove: set[str]):
    """
    Reads a large JSON file line by line to keep memory footprint extremely low.
    Extracts top-level objects (vulnerabilities), removes specified keys, 
    and streams them to the output file with a 2-space indentation format.
    """
    
    if not os.path.exists(json_full):
        print(f"Error: Input file '{json_full}' not found.")
        return

    print(f"Starting streaming minification. Reading from '{json_full}'...")
    
    # Open input file for reading and output file for writing
    with open(json_full, 'r', encoding='utf-8') as infile, \
         open(json_reduced, 'w', encoding='utf-8') as outfile:
         
        # Write the opening brace of the root JSON dictionary
        outfile.write("{\n")
        
        buffer: list[str] = []
        depth = 0
        in_string = False
        escape = False
        
        is_first_item = True
        items_processed = 0

        # Read the file strictly line by line (blocks) to save RAM
        for line in infile:
            line_depth_change = 0
            
            # Character scan to track structural JSON depth
            # We must ignore braces that are inside string literals
            for char in line:
                if escape:
                    escape = False
                    continue
                    
                if char == '"':
                    in_string = not in_string
                elif char == '\\' and in_string:
                    escape = True
                elif not in_string:
                    if char == '{':
                        line_depth_change += 1
                    elif char == '}':
                        line_depth_change -= 1
            
            # Calculate the depth after processing this line
            new_depth = depth + line_depth_change
            
            # If we are inside the root object (depth >= 1), we buffer the lines.
            # We explicitly ignore the very first root '{' and the very last root '}'
            if new_depth >= 1 and depth >= 1:
                # Prevent adding the final closing '}' of the entire file to the buffer
                if not (new_depth == 0 and '}' in line): 
                    buffer.append(line)
            
            # Update the global depth state
            depth = new_depth
            
            # If depth returns to 1, one complete vulnerability object is in the buffer
            if depth == 1 and buffer:
                # 1. Join buffer into a single string
                object_str = "".join(buffer).strip()
                
                # 2. Remove trailing comma if it exists (JSON standard strictly forbids it at the end)
                if object_str.endswith(','):
                    object_str = object_str[:-1]
                
                # 3. Wrap the string in braces to make it a valid, parseable JSON dictionary
                # Example: { "UUID": { "title": "..." } }
                valid_json_str = "{" + object_str + "}"
                
                try:
                    # Parse the single vulnerability into a Python dict (takes almost no RAM)
                    parsed_obj = json.loads(valid_json_str)
                    
                    # Iterate over the root key (which is the UUID)
                    for _, vuln_data in parsed_obj.items():
                        # Remove the heavy/unwanted keys
                        for key in keys_to_remove:
                            vuln_data.pop(key, None) # pop(..., None) avoids KeyError if key is missing
                            
                    # Serialize the cleaned object back to JSON string with 2-space indentation
                    minified_str = json.dumps(parsed_obj, indent=2)
                    
                    # json.dumps() returns a fully wrapped string: "{\n  'UUID': { ... }\n}"
                    # We need to strip the outer braces so it fits smoothly into our file stream
                    minified_str = minified_str.strip()
                    if minified_str.startswith("{"):
                        minified_str = minified_str[1:]
                    if minified_str.endswith("}"):
                        minified_str = minified_str[:-1]
                        
                    # Remove any resulting empty lines at the boundaries
                    minified_str = minified_str.strip("\n\r")
                    
                    # Write the cleaned object to the file
                    # Add a comma and newline BEFORE the item, unless it's the very first one
                    if not is_first_item:
                        outfile.write(",\n")
                        
                    outfile.write(minified_str)
                    
                    is_first_item = False
                    items_processed += 1
                    
                    # Optional: Progress output for large files
                    if items_processed % 5000 == 0:
                        print(f"Processed {items_processed} vulnerabilities...")
                        
                except json.JSONDecodeError as e:
                    print(f"Error parsing item at line: {e}")
                
                # IMPORTANT: Clear the buffer to free up RAM for the next item
                buffer.clear()

        # Write the final closing brace of the root JSON dictionary
        outfile.write("\n}\n")
        
    print(f"Downsized file created at '{json_reduced}'. Total items: {items_processed}")

#-------------------------------------------------------------------------------
def build_flat_sqlite_memory_optimized(json_file: Path, db_file: Path):
    if not os.path.exists(json_file):
        print(f"JSON file missing: {json_file}")
        return

    # 1. setup database
    conn = sqlite3.connect(db_file)
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
    with open(json_file, 'r', encoding='utf-8') as f:
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

#-------------------------------------------------------------------------------
if __name__ == "__main__":
    read_config(Path(__file__).parent / "website_reporter_config.ini")
    if settings.run_as_root and os.getuid() != 0: # type: ignore
        print(f"Skript not run as root. Exiting...")
        quit()

    # Update the Feed (or download initially)
    json_file = settings.wf_folder / settings.wf_json_file
    etag_file = settings.wf_folder / settings.wf_etag_file
    print(f"JSON file: {json_file}")
    print(f"ETag file: {etag_file}")
    currenttime = time.strftime('%d.%m.%Y %H:%M:%S')
    print(f"Attempting to refresh the Wordfence vulnerability JSON at {currenttime}")
    if update_vulnerability_database(json_file, etag_file) == Return.NEW:
        print(f"New Wordfence JSON downloaded successfully at {currenttime}")
        json_reduced_file = settings.wf_folder / settings.wf_json_reduced_file
        keys_to_drop = {"description", "references", "copyrights", "researchers"}
        downsize_wordfence_json(json_file, json_reduced_file, keys_to_drop)
        currenttime = time.strftime('%d.%m.%Y %H:%M:%S')
        print(f"New Wordfence JSON downsized successfully at {currenttime}")
        print(f"Downsized JSON file: {json_reduced_file}")
        db_file = settings.wf_folder / settings.wf_db_file
        build_flat_sqlite_memory_optimized(json_reduced_file, db_file)
        print(f"Created SQlite database: {db_file}")
        print(f"Database created successfully at {currenttime}")
 
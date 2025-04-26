#!/usr/bin/env python
"""
Load backup archive from server and overwrite local website with it.
"""
# =====================================================================
# module paramiko necessary
# Ubuntu package python3-paramiko
# apt list --installed | grep python3-paramiko
# sudo apt install python3-paramiko
# =====================================================================
import argparse,paramiko, getpass, os, tempfile, shutil
import wm.website_manager_utils as u
import subprocess

def get_names(siteName : str):
    script_folder = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_folder)
    paramsfile = script_folder + '/website_manager_params.txt'
    u.is_file_or_abort(paramsfile)
    params = u.Parameters(paramsfile)
    wwwroot = params.get('wwwroot')
    local_snapshot_dir = params.get('snapshotdir')
    # 'none': do nothing    
    www_user_group  = params.get('wwwusergroup') 

    websitesfile = script_folder + '/website_table.txt'
    u.is_file_or_abort(websitesfile)
    websites = u.WebSiteTable(websitesfile)
    site = websites.getSite(siteName)
    return wwwroot, site.wwwSubdir, local_snapshot_dir, www_user_group

def download(hostname, port, username, remote_archive_path, local_archive_path):
    # Passwort sicher abfragen
    password = getpass.getpass("Passwort eingeben: ")
    try:
        # SSH-Client initialisieren
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, port, username, password)

        # SFTP-Client erstellen
        sftp = ssh.open_sftp()

        # Prüfen, ob Datei existiert
        try:
            sftp.stat(remote_archive_path)
            print(f"Datei '{remote_archive_path}' gefunden. Wird heruntergeladen...")

            # Datei herunterladen
            sftp.get(remote_archive_path, local_archive_path)
            print(f"Datei wurde erfolgreich heruntergeladen nach: {local_archive_path}")

        except FileNotFoundError:
            print(f"Datei '{remote_archive_path}' wurde nicht gefunden.")

        # Verbindung schließen
        sftp.close()
        ssh.close()
        print("Verbindung geschlossen.")

    except Exception as e:
        print(f"Fehler: {e}")

# =====================================================================
p = argparse.ArgumentParser(description=__doc__,
               # formatter used to preserve the raw doc format
               formatter_class=argparse.RawTextHelpFormatter)

p.add_argument("host",
               help="ssh and sftp host name")
p.add_argument("user",
               help="sftp and ssh user")
p.add_argument("sshPort",
               help="ssh port")
p.add_argument("remoteDir",
               help="remote directory")
p.add_argument("remoteSiteName",
               help="remote site name of the downloaded archive")
p.add_argument("localSiteName",
               help="remote site name of the downloaded archive")

p.add_argument('-c', '--config', type=str,
               help='relative path of config file to be preserved')
p.add_argument('-t', '--timestamp', type=str,
               help='timestamp of archive to be downloaded')
args = p.parse_args()

u.print_line()
# Verbindungsparameter
hostname = args.host
username = args.user
port = args.sshPort
remote_dir = args.remoteDir
remote_site_name = args.remoteSiteName
tag = args.timestamp
if not tag:
    tag = u.get_date_tag()
print(remote_site_name, tag)
remote_archive_filename = remote_site_name + '.' + tag + '.tar.gz'
remote_archive_path = f"{remote_dir}/{remote_archive_filename}"

local_site_name = args.localSiteName
local_archive_site_name = local_site_name + '.' + tag + '.tar.gz'
names = get_names(local_site_name)
wwwroot = names[0]
wwwsubdir = names[1]
local_snapshot_dir = names[2]
local_archive_path = os.path.join(local_snapshot_dir, local_archive_site_name)  
www_user_group = names[3]

config_path = 'none'
tempdir = 'none'
if args.config:
    config_path = os.path.join(wwwroot, wwwsubdir, args.config)
    tempdir = tempfile.mkdtemp()
    print('Temporäres Verzeichnis erstellt:', tempdir)
    config_temp_path = os.path.join(tempdir, args.config)

u.print_line()
print('hostname:', hostname)
print('username:', username)
print('port:', port)
print('remote directory:', remote_dir)
print('remote website name:', remote_site_name)
print('remote archive path:', remote_archive_path)
print('local site name:', local_site_name)
print('webfiles root directory:', wwwroot)
print('website subdirectory:', wwwsubdir)
print('local snapshot directory:', local_snapshot_dir)
print('local website name:', local_site_name)
print('local archive path ', local_archive_path)
print('temporary directory:', tempdir)
print('configuration path:', config_path)
print('configuration temp path:', config_temp_path)
print('user:group for webfiles:', www_user_group)
u.print_line()
u.is_file_or_abort(config_path)

download(hostname, port, username, remote_archive_path, local_archive_path)

if args.config:
    print('save', args.config, 'to temp directory')
    shutil.copy2(config_path, config_temp_path)

subprocess.run(['python', 'website_manager.py', 'scitemporg', '--timestamp', tag])

if args.config:
    print('restore local config file')
    os.remove(config_path)
    shutil.move(config_temp_path, config_path)
    os.system('chown -R ' + www_user_group + ' ' + config_path)
    shutil.rmtree(tempdir)

print('... finished')

#!/usr/bin/env python
"""
Load backup archive from server and overwrite local website with it.
Optionally, preserve a local configuration file during the process.
Optionally, a time stamp can be given to load an older archive.
Requires paramiko module for SFTP transfer.
The downloaded archive is stored in the local snapshot folder.
Depends on website_manager.py to restore the website from the downloaded archive.
"""
# =====================================================================
# module paramiko necessary
# Ubuntu package python3-paramiko
# apt list --installed | grep python3-paramiko
# sudo apt install python3-paramiko
# =====================================================================
import argparse, paramiko, getpass, os, tempfile, shutil
from wm.websites import WebSiteTable
from wm.config import Parameters
from wm.timeutils import get_date_tag
import wm.utils as u
import subprocess
__version__ = "1.1.0"

def get_names(siteName : str):
    """
    Get important names and paths from parameter and website table files. Returns:
    wwwroot            from the parameter file 
    site.wwwSubdir     from the website table file using siteName
    local_snapshot_dir from the parameter file
    www_user_group     from the parameter file
    """
    script_folder = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_folder)
    paramsfile = script_folder + '/website_manager_config.ini'
    u.is_file_or_abort(paramsfile)
    params = Parameters(paramsfile)
    wwwroot = params.get('wwwroot')
    local_snapshot_dir = params.get('snapshotdir')
    # www_user_group == 'none': do nothing    
    www_user_group = params.get('wwwusergroup') 

    websitesfile = script_folder + '/website_table.txt'
    u.is_file_or_abort(websitesfile)
    websites = WebSiteTable(websitesfile)
    site = websites.getSite(siteName)
    if site.owner != "default":
        www_user_group = site.owner + ":" + site.owner
    return wwwroot, site.wwwSubdir, local_snapshot_dir, www_user_group

def download(hostname: str, port: int, username: str, 
             remote_archive_path: str, local_archive_path: str):
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

p.add_argument("--host", required=True,
               help="name of remote ssh and sftp host")
p.add_argument("--user", required=True,
               help="sftp and ssh user on remote host")
p.add_argument("--sshPort", required=True,
               help="ssh port on remote host")
p.add_argument("--remoteDir", required=True,
               help="remote directory")
p.add_argument("--remoteSiteName", required=True,
               help="remote site name of the downloaded archive")
p.add_argument("--localSiteName", required=True,
               help="local site name of the downloaded archive")

p.add_argument('--configSaved', type=str,
               help='relative path of local website config file to be preserved')
p.add_argument('--timestamp', type=str,
               help='timestamp (date) of archive to be downloaded')
p.add_argument("-v", "--version", action='version', 
               version='%(prog)s version {version}'.format(version=__version__))
args = p.parse_args()

u.print_line()
# Verbindungsparameter
hostname = args.host
username = args.user
port = args.sshPort
remote_dir = args.remoteDir
remote_site_name = args.remoteSiteName
tag = args.timestamp
# if no tag given, use current date tag
if not tag:
    tag = get_date_tag()
remote_archive_filename = remote_site_name + '.' + tag + '.tar.gz'
remote_archive_path = f"{remote_dir}/{remote_archive_filename}"

local_site_name = args.localSiteName
local_archive_site_name = local_site_name + '.' + tag + '.tar.gz'
wwwroot, wwwsubdir, local_snapshot_dir, www_user_group = get_names(local_site_name)
local_archive_path = os.path.join(local_snapshot_dir, local_archive_site_name)

config_path = 'none'
tempdir = 'none'
config_temp_path = 'none'
if args.configSaved:
    config_path = os.path.join(wwwroot, wwwsubdir, args.configSaved)
    tempdir = tempfile.mkdtemp()
    print('Temporäres Verzeichnis erstellt:', tempdir)
    config_temp_path = os.path.join(tempdir, args.configSaved)

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
print('local website config path:', config_path)
print('cached config file:', config_temp_path)
print('user:group for webfiles:', www_user_group)
u.print_line()
u.is_file_or_abort(config_path)

download(hostname, port, username, remote_archive_path, local_archive_path)

if args.configSaved:
    print('save', args.configSaved, 'to temp directory')
    shutil.copy2(config_path, config_temp_path)

subprocess.run(['python', 'website_manager.py', local_site_name, '--timestamp', tag])

if args.configSaved:
    print('restore local config file')
    os.remove(config_path)
    shutil.move(config_temp_path, config_path)
    subprocess.run(['chown', '-R', www_user_group, config_path], check=True)
    # os.system('chown -R ' + www_user_group + ' ' + config_path)
    shutil.rmtree(tempdir)

print('... finished')

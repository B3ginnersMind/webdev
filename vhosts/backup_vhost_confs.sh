#!/usr/bin/env bash
#----------------------------------------------------------------------------saekulare-sozis.de
# Create a timestamped backup of all vhost confs
#----------------------------------------------------------------------------
CONF_FOLDER="/etc/apache2/sites-available"
TIMESTAMP="$(date +%Y-%m-%d-%H-%S)"
BACKUP_DIR="/Backup/archive/apache2-confs"
BACKUP_FILE="${BACKUP_DIR}/${TIMESTAMP}-all-vhost-confs.tar"

# -cf ...: Erstelle das Archiv am angegebenen Zielort.
# -C  ...: Wechselt das Arbeitsverzeichnis für den Befehl intern in diesen Ordner.
# .      : alles im Verzeichnis, in das wir gerade mit `-C` gesprungen, einpacken.
sudo tar -cf $BACKUP_FILE -C $CONF_FOLDER .
echo "====== show backup tarball content ======"
tar -tf $BACKUP_FILE
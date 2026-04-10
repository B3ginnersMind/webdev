#!/usr/bin/env bash
#----------------------------------------------------------------------------
# Testet die Erneuerung eines Zertifikats mit Certbot.
# conf-Dateien der vhosts        : /etc/apache2/sites-available
# conf-Dateien aktivierter vhosts: /etc/apache2/sites-enabled
# Zertifikat-Renewal-configs     : /etc/letsencrypt/renewal
# Webordner                      : /var/www# Das Skript prüft die notwendigen Dateien und Verzeichnisse, 
# erstellt ein Backup der Apache-Konfiguration,
# bearbeitet die Konfiguration, testet sie und 
# führt einen Certbot Dry-Run durch, um die Erneuerung zu simulieren.
#----------------------------------------------------------------------------
# Strenge Fehlerbehandlung aktivieren
set -euo pipefail

if [ "$#" -ne 4 ]; then
    echo "Fehler: Es werden genau 4 Parameter benötigt."
    echo "Anwendung: $0 <Config-Name> <Renewal-Config-Name> <Webordner> <Domain>"
    echo "Die Configs ohne die Erweiterung .conf und der Ordner ohne ganzen Pfad."
    echo "Beispiel: $0 sarma.me sarma.me sarmame sarma.me"
    exit 1
fi

echo "Genau 4 Parameter wurden übergeben."
# Variablen definieren.
# Apache Config Name (ohne .conf)
CONFIG="$1"
# Certbot Renewal Config Name (ohne .conf)  
CERTNAME="$2"
# Web-Ordnername für die Challenge.
FOLDERNAME="$3"
# Domain für die Challenge.
DOMAIN="$4"
echo "1: CONFIG     : $1"
echo "2: CERTNAME   : $2"
echo "3: FOLDERNAME : $3"
echo "4: DOMAIN     : $3"

APACHE_CONF="/etc/apache2/sites-available/${CONFIG}.conf"
CERT_CONF="/etc/letsencrypt/renewal/${CERTNAME}.conf"
ENABLED_LINK="/etc/apache2/sites-enabled/${CONFIG}.conf"
WEB_ROOT="/var/www/${FOLDERNAME}"

TIMESTAMP="$(date +%Y-%m-%d-%H-%S)"
BACKUP_DIR="/Backup/archive/${CONFIG}"
BACKUP_FILE="${BACKUP_DIR}/${TIMESTAMP}-${CONFIG}.conf"

# Parameter prüfen
if [[ -z "$CONFIG" || -z "$CERTNAME" ]]; then
    echo "Usage: $0 CONFIG CERTNAME"
    exit 1
fi

# root prüfen
if [[ "$EUID" -ne 0 ]]; then
    echo "Fehler: Script muss mit sudo ausgeführt werden."
    exit 1
fi

# Web-Ordner prüfen
if [[ ! -d "$WEB_ROOT" ]]; then
    echo "Fehler: Web-Ordner nicht gefunden:"
    echo "  $WEB_ROOT"
    exit 1
fi

# Apache Config vorhanden?
if [[ ! -f "$APACHE_CONF" ]]; then
    echo "Fehler: Apache Config nicht gefunden:"
    echo "  $APACHE_CONF"
    exit 1
fi

# Certbot Renewal Config vorhanden?
if [[ ! -f "$CERT_CONF" ]]; then
    echo "Fehler: Certbot Renewal Config nicht gefunden:"
    echo "  $CERT_CONF"
    exit 1
fi

# Prüfen, ob Site enabled ist
if [[ ! -e "$ENABLED_LINK" ]]; then
    echo "Fehler: Apache Site nicht enabled:"
    echo "  $ENABLED_LINK"
    echo "Aktivieren mit:"
    echo "  a2ensite ${CONFIG}"
    exit 1
fi

# Backup anlegen
mkdir -p "$BACKUP_DIR"
cp "$APACHE_CONF" "$BACKUP_FILE"

echo "Backup erstellt:"
echo "  $BACKUP_FILE"

# Config bearbeiten
nano "$APACHE_CONF"

# Apache Config testen
echo "Teste Apache Konfiguration..."
if ! apache2ctl configtest; then
    echo "Fehler in Apache-Konfiguration. Abbruch."
    exit 1
fi

# Apache neu starten
echo "Starte Apache neu..."
apache2ctl restart

# Teste per curl, ob die Challenge erreichbar ist
mkdir -p /var/www/$FOLDERNAME/.well-known/acme-challenge
echo OK > /var/www/$FOLDERNAME/.well-known/acme-challenge/token1
curl -fsS http://$DOMAIN/.well-known/acme-challenge/token1\ 
  && echo "Challenge erreichbar" \
  || echo "Challenge NICHT erreichbar"
rm -rf /var/www/$FOLDERNAME/.well-known

# Certbot Dry-Run
echo "Teste Zertifikatserneuerung..."
certbot renew --cert-name "$CERTNAME" --dry-run

echo "Test abgeschlossen."

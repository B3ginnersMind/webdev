#!/bin/bash

# Das Skript muss als root ausgeführt werden
if [ "$EUID" -ne 0 ]; then
  echo "❌ Bitte führe dieses Skript mit sudo oder als root aus!"
  exit 1
fi

# Hilfe-Anzeige, falls zu wenige Parameter übergeben wurden
if [ "$#" -ne 5 ]; then
  echo "-------------------------------------------------------------------------------------------"
  echo "Usage: $0 <WEB_USER> <PHP_REL> <POOL_NAME> <DOCROOT> <VHOST_PATH>"
  echo "Example: $0 web-scitemp 8.4 scitemp /var/www/scitemp /etc/apache2/sites-available/scitemp.conf"
  echo "-------------------------------------------------------------------------------------------"
  echo "<WEB_USER>: The new user under which the PHP pool runs."
  echo "<PHP_REL>: PHP release"
  echo "<POOL_NAME>: Name of the pool"
  echo "<DOCROOT>: Root of the vhost webfiles"
  echo "<VHOST_PATH>: Path to the vhost config file"
  echo "-------------------------------------------------------------------------------------------"
  echo "Create a new PHP-FPM pool. Use this pool to isolate an Apache vhost."
  echo "- Set up <WEB_USER> if it does not already exist."
  echo "- Create a new PHP pool called <POOL_NAME> for PHP version <PHP_REL> using the user <WEB_USER>."
  echo "- Adapt the specified vhost configuration to the new PHP pool."
  echo "- Restart the PHP-FPM release <PHP_REL>."
  echo "- Assign the the web file permissions under <DOCROOT> to the user <WEB_USER>."
  echo "- Restart Apache."
  echo "-------------------------------------------------------------------------------------------"
  exit 1
fi

# Parameter den Variablen zuweisen
WEB_USER="$1"
PHP_REL="$2"
POOL_NAME="$3"
DOCROOT="$4"
VHOST="$5"

echo "=== Starte vHost- und PHP-FPM-Konfiguration ==="
echo "User:      $WEB_USER"
echo "PHP-Rel:   $PHP_REL"
echo "Pool:      $POOL_NAME"
echo "Docroot:   $DOCROOT"
echo "vHost-File:$VHOST"
echo "==============================================="

# 1. User $WEB_USER anlegen
echo "-> Erzeuge Systembenutzer und -gruppe..."
if id "$WEB_USER" &>/dev/null; then
    echo "ℹ️ User $WEB_USER existiert bereits. Überspringe Erstellung."
else
    adduser --system --group --disabled-login --shell /bin/false "$WEB_USER"
fi

echo "-> Füge www-data zur Gruppe $WEB_USER hinzu..."
usermod -aG "$WEB_USER" www-data


# 2. Pool-Konfiguration erzeugen
POOL_CONF="/etc/php/$PHP_REL/fpm/pool.d/$POOL_NAME.conf"
echo "-> Erzeuge Pool-Konfiguration unter $POOL_CONF..."

# Prüfen, ob das Verzeichnis überhaupt existiert (falls PHP-Version nicht installiert ist)
if [ ! -d "/etc/php/$PHP_REL/fpm/pool.d" ]; then
    echo "❌ Fehler: Verzeichnis /etc/php/$PHP_REL/fpm/pool.d existiert nicht!"
    echo "Ist PHP $PHP_REL installiert?"
    exit 1
fi

cat <<EOF > "$POOL_CONF"
[$POOL_NAME]
user = $WEB_USER
group = $WEB_USER
listen = /run/php/php$PHP_REL-fpm-$POOL_NAME.sock
listen.owner = www-data
listen.group = www-data
listen.mode = 0660
php_admin_value[open_basedir] = $DOCROOT:/tmp
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
EOF


# 3. Vhost-Konfiguration anpassen
if [ ! -f "$VHOST" ]; then
    echo "❌ Fehler: Die vHost-Datei $VHOST wurde nicht gefunden!"
    exit 1
fi

echo "-> Passe SetHandler in $VHOST an..."
# Ersetzt die gesamte Zeile, die "SetHandler" enthält, sicher durch die neue Definition.
# Wir nutzen '#' als Trenner im 'sed', da der Pfad Schrägstriche enthält.
sed -i "s#SetHandler .*#SetHandler \"proxy:unix:/run/php/php$PHP_REL-fpm-$POOL_NAME.sock|fcgi://localhost\"#g" "$VHOST"


# 4. PHP-FPM neu starten und prüfen
echo "-> Starte php$PHP_REL-fpm neu..."
systemctl restart "php$PHP_REL-fpm"

if [ $? -ne 0 ]; then
    echo "❌ Fehler: php$PHP_REL-fpm konnte nicht neu gestartet werden!"
    echo "=== Systemd Status ==="
    systemctl status "php$PHP_REL-fpm.service" --no-pager
    exit 1
fi

# Prüfen, ob der Socket erfolgreich erstellt wurde
SOCKET_PATH="/run/php/php$PHP_REL-fpm-$POOL_NAME.sock"
if [ -S "$SOCKET_PATH" ]; then
    echo "✅ PHP-FPM-Socket erfolgreich erstellt:"
    ls -la "$SOCKET_PATH"
else
    echo "❌ Fehler: Socket-Datei $SOCKET_PATH wurde nicht im Dateisystem gefunden!"
    exit 1
fi


# 5. Webverzeichnis-Permissions anpassen
if [ ! -d "$DOCROOT" ]; then
    echo "ℹ️ Verzeichnis $DOCROOT existiert nicht. Erstelle es..."
    mkdir -p "$DOCROOT"
fi

echo "-> Passe Dateiberechtigungen an..."
chown -R "$WEB_USER:$WEB_USER" "$DOCROOT"
# Ordner auf 750 (Besitzer darf alles, Apache/Gruppe darf lesen/betreten)
find "$DOCROOT" -type d -exec chmod 750 {} +
# Dateien auf 640 (Besitzer darf schreiben, Apache/Gruppe darf lesen)
find "$DOCROOT" -type f -exec chmod 640 {} +


# 6. Webserver neu starten
echo "-> Starte Apache neu..."
apache2ctl configtest
if [ $? -ne 0 ]; then
    echo "❌ Fehler: Apache-Konfiguration ist fehlerhaft! Apache-Neustart abgebrochen."
    exit 1
fi

apache2ctl restart
echo "🎉 Fertig! Virtual Host und PHP-Pool wurden erfolgreich eingerichtet."

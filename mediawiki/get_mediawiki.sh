#!/bin/bash
#
# *Funktionen:*
# - Überprüft, ob alle drei Parameter übergeben wurden
# - Erstellt das Zielverzeichnis, falls es nicht existiert
# - Wechselt in das Verzeichnis
# - Lädt das MediaWiki-Archiv herunter
# - Gibt bei Fehler eine entsprechende Meldung aus
# - Entpackt bei Erfolg das Archiv
# - Prüft nach jedem kritischen Schritt auf Fehler
# 
# *Verwendung:*
# chmod +x get_mediawiki.sh
# ./get_mediawiki.sh 43 5 /var/www/mediawiki

# Überprüfe, ob alle erforderlichen Parameter übergeben wurden
if [ $# -ne 3 ]; then
    echo "Fehler: Ungültige Anzahl an Parametern!"
    echo "Verwendung: $0 <release> <patch> <folder>"
    echo "Beispiel: $0 43 5 /home/user/mediawiki"
    exit 1
fi

# Parameter zuweisen
release=$1
patch=$2
folder=$3

# Erzeuge Verzeichnis, wenn es nicht existiert
if [ ! -d "$folder" ]; then
    echo "Erstelle Verzeichnis: $folder"
    mkdir -p "$folder"
    if [ $? -ne 0 ]; then
        echo "Fehler: Verzeichnis $folder konnte nicht erstellt werden!"
        exit 1
    fi
fi

# Wechsle in das Verzeichnis
echo "Wechsle in Verzeichnis: $folder"
cd "$folder" || {
    echo "Fehler: Kann nicht in Verzeichnis $folder wechseln!"
    exit 1
}

# Download-URL zusammensetzen
filename="mediawiki-1.$release.$patch.tar.gz"
url="https://releases.wikimedia.org/mediawiki/1.$release/$filename"

# Lade MediaWiki-Archiv herunter
echo "Lade MediaWiki herunter von: $url"
exit 0
wget "$url"

# Überprüfe, ob Download erfolgreich war
if [ $? -ne 0 ]; then
    echo "Fehler: Download von $url fehlgeschlagen!"
    exit 1
fi

echo "Download erfolgreich. Entpacke Archiv..."

# Entpacke das Archiv
tar -xzvf "$filename"

# Überprüfe, ob Entpacken erfolgreich war
if [ $? -eq 0 ]; then
    echo "MediaWiki wurde erfolgreich heruntergeladen und entpackt!"
    echo "Speicherort: $folder"
else
    echo "Fehler: Entpacken von $filename fehlgeschlagen!"
    exit 1
fi

exit 0
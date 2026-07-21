import os, re
from pathlib import Path
import wm.dbutils as db
from wm.websites import WebSiteTable, WebSiteData
from wm.config import Parameters

# Joomla configuration.php    : public $password = 'XXX';
# WordPress wp-config.php     : define('DB_PASSWORD', 'XXX');
# Mediawiki LocalSettings.php : $wgDBpassword = "XXX";

# CMS_LIST = ['joomla', 'wordpress', 'mediawiki', 'drupal']
CMS_LIST = ['joomla', 'wordpress', 'mediawiki', 'static']
CMS_CONFIG_FILE = {"joomla"   : "configuration.php", 
                   "wordpress": "wp-config.php",
                   "mediawiki": "LocalSettings.php"}
CMS_PW_VARIABLE = {"joomla"   : "$password", 
                   "wordpress": "DB_PASSWORD",
                   "mediawiki": "$wgDBpassword"}

def get_cms(site : WebSiteData) -> str:
    """
    Ermittelt das CMS anhand des Kommentarfeldes der Website.
    Gibt den CMS-Namen zurück, wenn eindeutig, sonst "none" oder "multiple".
    """
    siteComment = site.comment.lower()
    found = [cms for cms in CMS_LIST if cms in siteComment]
    
    if len(found) == 0:
        return "none"
    elif len(found) == 1:
        return found[0]
    else:
        return "multiple"

def process_dbpassword(params : Parameters, site : WebSiteData, change: bool = False):
    """
    Prüft, ob das Passwort in der CMS-Konfigurationsdatei mit dem in der Website-Table übereinstimmt.
    Wenn change=True, wird das Passwort in der CMS-Konfigurationsdatei und das in der Datenbank 
    auf das Passwort in der Website-Table geändert.
    """
    wwwRoot = params.get('wwwroot')
    wwwDir = wwwRoot + '/' + site.wwwSubdir
    cms = get_cms(site)
    conf = ""
    if cms == "none":
        print(site.siteName, "==> missing known CMS indicator")
        return
    elif cms == "static":
        print(site.siteName, "==> static website")
        return
    elif cms == "multiple":
        print(site.siteName, "==> multiple CMS indicators")
        return
    else:
        # if not checkOnly and not db.database_exists(params, site):
        if not db.dbuser_exists(params, site):
            return
        conf = wwwDir + '/' + CMS_CONFIG_FILE[cms]
        if not os.path.isfile(conf):
            print(site.siteName, "==> missing CMS configuration file", conf)
            return
        found = search_dbpassword(Path(conf), cms, site.dbPassWord)
        if found:
            msg = "password unchanged"
        else:
            msg = "==> password changed!"
        print(site.siteName, cms, conf, msg)
        if change and not found:
            print("=> Setting new password in configuration file...")
            set_dbpassword(conf, cms, site.dbPassWord)
            db.change_dbuser_pw(params, site)
        return  

def search_dbpassword(conf: Path, cms: str, password: str) -> bool:
    """
    Prüft, ob das Passwort in der CMS-Konfigurationsdatei mit dem in der Website-Table übereinstimmt.
    """
    # CMS im Dict vorhanden?
    if cms not in CMS_PW_VARIABLE:
        return False
    pw_variable = CMS_PW_VARIABLE[cms]
    config_text = conf.read_text(encoding="utf-8")

    # Zeile suchen, in der die Passwortvariable vorkommt
    matching_line = None
    for line in config_text.splitlines():
        if pw_variable in line:
            matching_line = line
            break

    if matching_line is None:
        return False
    print("Matching line ==>", matching_line)
    # Prüfen ob password in der Zeile vorkommt, begrenzt durch " oder '.
    # r bedeutet raw string, um Escape-Sequenzen zu vermeiden.
    # """ bedeuteet, dass im String sowohl ' als auch " vorkommen können, 
    # ohne dass sie escaped werden müssen.
    # re.escape(password) sorgt dafür, dass Sonderzeichen im Passwort korrekt 
    # behandelt werden.
    # ['"] bedeutet, dass das Passwort entweder in ' oder " eingeschlossen sein kann.
    # re.escape(password) falls das Passwort Sonderzeichen wie $, . oder * enthält
    pattern = re.compile(r"""['"]""" + re.escape(password) + r"""['"]""")
    return bool(pattern.search(matching_line))

def set_dbpassword(conf: str, cms: str, password: str) -> bool:
    """Ersetzt das Passwort in der Konfigurationsdatei.
    Gibt True zurück wenn erfolgreich, False wenn Zeile nicht gefunden.
    """
    if cms not in CMS_PW_VARIABLE:
        return False

    pw_variable = CMS_PW_VARIABLE[cms]
    config_path = Path(conf)
    lines = config_path.read_text(encoding="utf-8").splitlines(keepends=True)

    new_lines: list[str] = []
    replaced = False

    for line in lines:
        if pw_variable in line:
            # Dieser Regex sucht nach dem LETZTEN Anführungszeichen-Paar in der Zeile.
            # (['"])[^'"]*\1  sucht den String.
            # (?=[^'"]*$)     stellt über ein Lookahead sicher, dass danach keine weiteren 
            #                 Anführungszeichen mehr bis zum Zeilenende kommen.
            pattern = r"""(['"])[^'"]*\1(?=[^'"]*$)"""
            
            # Prüfen, ob wir überhaupt ein Match für das letzte Paar finden
            if re.search(pattern, line):
                new_line = re.sub(
                    pattern,
                    lambda m: m.group(1) + password + m.group(1),
                    line,
                    count=1
                )
                new_lines.append(new_line)
                replaced = True
                print("New line ==>", new_line)
                continue

        # Wenn die Variable nicht drin ist oder kein Match vorliegt, Zeile unverändert lassen
        new_lines.append(line)

    if not replaced:
        return False

    # Datei schreiben und mit .join() sauber formatiert ausgeben
    config_path.write_text("".join(new_lines), encoding="utf-8")
    # print("".join(new_lines))
    return True

def check_user_password_consistency(websites : WebSiteTable, singleSite : str) -> bool:
    """
    Prüft DB-User/Passwort-Kombinationen in der Website-Table.
    - Warnung, wenn der selbe DB-User verschiedene Passwörter hat. Das ist inkonsistent!
    - Warnung, wenn der selbe DB-User für mehr als eine Website genutzt.
      Wenn nur bei einer Website das Passwort geändert wird, funktionieren die anderen nicht mehr!
      Die Passwörter müssen daher für alle Websites angepasst werden, die diesen DB-User haben!
    """
    numSites = websites.getNumWebsites()
    ok = True
    password_dict = {}

    if websites.hasSite(singleSite):
        dbUserOfSingeSite = websites.getSite(singleSite).dbUser
    else:
        dbUserOfSingeSite = 'none'

    for row in range(numSites):
        site = websites.getData(row)
        if site.dbUser == 'none':
            continue
        if site.dbUser in password_dict:
            if site.dbPassWord != password_dict[site.dbUser]:
                ok = False
                print("!!! Different passwords for DB user:", site.dbUser)
            if site.dbUser == dbUserOfSingeSite:
                ok = False
                print("!!! DB user", site.dbUser, "used again")
        else:
            password_dict[site.dbUser] = site.dbPassWord
    return ok

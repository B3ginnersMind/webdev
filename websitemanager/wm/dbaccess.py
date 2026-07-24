import copy, os, re
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Union
from wm.utils import print_line
from wm.config import Parameters
import wm.dbutils as db
from wm.websites import WebSiteData

# Supported CMS types and their corresponding database credential definitions.
#--------------------------------------------------------------------------------------------
# Joomla configuration.php    | WordPress wp-config.php         | Mediawiki LocalSettings.php
#--------------------------------------------------------------------------------------------
# public $db = 'XXX';         | define('DB_NAME', 'XXX');       | $wgDBname = "XXX";
# public $user = 'XXX';       | define('DB_USER', 'XXX');       | $wgDBuser = "XXX";
# public $password = 'XXX';   | define('DB_PASSWORD', 'XXX');   | $wgDBpassword = "XXX";
# public $host = 'localhost'; | define('DB_HOST', 'localhost'); | $wgDBserver = "localhost";

@dataclass
class Options:
    adjust: bool = False
    verbose: int = 1
    dbverbose: str = "quiet"

@dataclass
class MyCmsDataBase:
    """Gemeinsame Basisklasse, die alle Funktionen bereitstellt."""

    def db_values(self) -> list[str]:
        return [str(value) for name, value in self.__dict__.items() 
                if name.startswith('db')]

    def show_values(self) -> None:
        values = ""
        for value in self.__dict__.values():
            values += " - " + value
        print(values)

    def show(self, info: str = "") -> None:
        print("------- MyData contents --------------", info)
        for name, value in self.__dict__.items():
            print(f"{name}: {value}")
        print("--------------------------------------")

@dataclass
class Joomla(MyCmsDataBase):
    cms: str = "Joomla"
    config: str = "configuration.php"
    dbname: str = "$db"
    dbuser: str = "$user"
    dbpass: str = "$password"
    dbhost: str = "$host"

@dataclass
class Wordpress(MyCmsDataBase):
    cms: str = "Wordpress"
    config: str = "wp-config.php"
    dbname: str = "DB_NAME"
    dbuser: str = "DB_USER"
    dbpass: str = "DB_PASSWORD"
    dbhost: str = "DB_HOST"

@dataclass
class Mediawiki(MyCmsDataBase):
    cms: str = "Mediawiki"
    config: str = "LocalSettings.php"
    dbname: str = "$wgDBname"
    dbuser: str = "$wgDBuser"
    dbpass: str = "$wgDBpassword"
    dbhost: str = "$wgDBserver"

JOOMLA = Joomla()
WORDPRESS = Wordpress()
MEDIAWIKI = Mediawiki()

@dataclass
class DbVar2Data:
    dbName: tuple[str, str] = ("", "")
    dbUser: tuple[str, str] = ("", "")
    dbPassWord: tuple[str, str] = ("", "")
    host: tuple[str, str] = ("", "")
    
    def show(self, msg: str = "") -> None:
        if msg:
            print(f"------ DbVar2Data: {msg} -------")
        for f in fields(self):
            name = f.name
            tpl = getattr(self, name)
            print(f"Feld '{name}' hat das Tupel: {tpl}")
        if msg:
            line = "-" * (len(msg) + 27)
            print(line)

# CMS types. 'static' means there is no CMS.
CMS_LIST = ['joomla', 'wordpress', 'mediawiki', 'static']
# Dictionary which contains CMS-specific dataclasses.
CMS_DICT : dict[str, Union[Joomla, Wordpress, Mediawiki]] =  {
    "joomla"   : JOOMLA, 
    "wordpress": WORDPRESS,
    "mediawiki": MEDIAWIKI
    }

def get_config_cms(
    params: Parameters, 
    site: WebSiteData, opt: Options,
) -> tuple[bool, str, str]:
    """
    Detect CMS type and get the corresponding config file path.
    """
    if opt.verbose > 1:
        site.show("Treated Website")
    elif opt.verbose == 1:
        print(f"Treating website '{site.siteName}' ...")
    siteComment = site.comment.lower()
    found = [cms for cms in CMS_LIST if cms in siteComment]
    if len(found) == 0:
        return (False, "no config due to unknown_cms", "none")
    elif len(found) > 1:
        return (False, "==> no config due to multiple_cms", "none")
    elif found[0] == 'static':
        return (False, "no config due to static_website", "none")
    cms_name = found[0]
    cms_attribs = CMS_DICT[cms_name]
    # cms_attribs.show("CMS data for " + cms_name)
    wwwRoot = params.get('wwwroot')
    wwwDir = wwwRoot + '/' + site.wwwSubdir
    config_path = wwwDir + '/' + cms_attribs.config
    if not os.path.isfile(config_path):
        print(f"==> Website '{site.siteName}': missing CMS config file", config_path)
        return (False, "no config due to missing_file", cms_name)
    print(f"Website '{site.siteName}' config file: {config_path}")
    return (True, config_path, cms_name)

def adjust_config_after_restore(
    params: Parameters,
    site: WebSiteData, 
    opt: Options,
) -> None:
    """"
    Adjust the database access data in the CMS configuration file after a 
    successful website restore.
    Database restore could have been only successful if the database access data 
    in the website table is valid. Therefore, it is not necessary to test database 
    access again. But the database access data in the CMS configuration file 
    might be different from the data in the website table since the website restore 
    might have been done from a backup with former database access data. Therefore,
    it is necessary to adjust the database access data in the CMS configuration file 
    to match the data in the website table. This function does that.
    """
    found, config_path, cms_name = get_config_cms(params, site, opt)
    # If the CMS config file is not found or if the CMS is unknown, nothing to adjust.
    if not found:
        print(config_path)
        return

    cms_data = CMS_DICT[cms_name]
    # Set database variables from website table
    db_table_data = DbVar2Data()
    db_table_data.dbName = (cms_data.dbname, site.dbName)
    db_table_data.dbUser = (cms_data.dbuser, site.dbUser)
    db_table_data.dbPassWord = (cms_data.dbpass, site.dbPassWord)
    db_table_data.host = (cms_data.dbhost, site.host)
    are_equal = compare_and_adjust_table2config(Path(config_path), db_table_data, opt)[0]
    print(f"Website '{site.siteName}' returned with: {are_equal}")

def compare_and_adjust_table2config(
    config_path: Path, 
    db_table_data: DbVar2Data,
    opt: Options
) -> tuple [bool, DbVar2Data]:
    """
    Compare database credentials in the config file with the entries in the website table.
    Report any differences and, optionally, set the config file values to those in the table.
    config_path: Path to the CMS config file.
    db_table_data: Database credentials from the website table.
    opt: Options relating to verbosity and the possible adjustments of the config file.
    """
    print(opt)
    db_config_data = DbVar2Data()
    for f in fields(db_table_data):
        name = f.name
        variable = getattr(db_table_data, name)[0]
        setattr(db_config_data, name, (variable, ""))
    db_config_data_new = copy.deepcopy(db_config_data)
    new_lines: list[str] = []
    # config_text = conf.read_text(encoding="utf-8")
    config_text = config_path.read_text(encoding="utf-8").splitlines(keepends=True)    
    #for line in config_text.splitlines():
    for line in config_text:
        for f in fields(db_table_data):
            name = f.name
            variable = getattr(db_table_data, name)[0]
            value = getattr(db_table_data, name)[1]
            pattern = re.compile(r"(^|['\"\s])" + re.escape(variable) + r"(?=['\"=\s]|$)")
            # Search for the variable in the line, allowing for optional quotes and whitespace
            if bool(pattern.search(line)):
                if opt.verbose > 1:
                    print("==> Matching line", line)
                pattern = re.compile(r"""['"]""" + re.escape(value) + r"""['"]""")
                # Extract the value from the matching line, allowing for optional quotes.
                pattern = r"""(['"])([^'"]*)\1(?=[^'"]*$)"""
                match = re.search(pattern, line)
                if match:
                    found_config_value = match.group(2)
                    if opt.verbose > 1:
                        print(f"Field '{name}' found: Variable '{variable}' = '{found_config_value}'")
                    setattr(db_config_data, name, (variable, found_config_value))
                    if opt.adjust:
                        value_table = str(getattr(db_table_data, name)[1])
                        if value_table != found_config_value:
                            replaced, line = adjust_value(value_table, line)
                            if replaced:
                                setattr(db_config_data_new, name, (variable, value_table))
                            else:
                                setattr(db_config_data_new, name, (variable, found_config_value))
                        else:
                            setattr(db_config_data_new, name, (variable, value_table))
                    else:
                        setattr(db_config_data_new, name, (variable, found_config_value))
        new_lines.append(line)

    if opt.verbose > 2:
        print_line()
        print("".join(new_lines))
        print_line()
    if db_table_data == db_config_data:
        print("MATCH: Database credentials from website table and config file matched.")
        db_config_data.show("Database credentials in config.")
        return (True, db_config_data)
    elif not opt.adjust:
        print("==> CONFLICT: Database credentials from website table and config file conflicting.")
        db_table_data.show("Database credentials in table.")
        db_config_data.show("Database credentials in config.")
        return (False, db_config_data)
    elif db_table_data == db_config_data_new:
        config_path.write_text("".join(new_lines), encoding="utf-8")

        print("ADJUST: Database credentials from website table inserted in config file.")
        db_config_data_new.show("Adjusted database credentials in config.")
        return (True, db_config_data_new)
    else:
        db_table_data.show("Database credentials in table.")
        db_config_data.show("Database credentials from old config.")
        db_config_data_new.show("Adjusted database credentials in config.")
        print("==> FAIL: Adjustment of database credentials in config file incomplete or failed.")
        return (False, db_config_data_new)

def adjust_value(
    value_table: str,
    line: str,
) -> tuple[bool, str]:
    pattern = r"""(['"])[^'"]*\1(?=[^'"]*$)"""
    print(f"==> Old line: {line.rstrip()}")
    if re.search(pattern, line):
        new_line = re.sub(
            pattern,
            lambda m: m.group(1) + value_table + m.group(1),
            line,
            count=1
        )
        print(f"==> New line: {new_line.rstrip()}")
        return (True, new_line)
    return (False, line)

def has_database_access(
        params: Parameters, 
        site: WebSiteData, 
        opt: Options
        ) -> bool:
    """
    Check whether the database "dbName" of webite "site" is accessible by "dbUser".
    """
    if opt.verbose > 1:
        site.show("Website configuration from config file")
    # Check if dbUser exists in the database software?
    if not db.dbuser_exists(params, site, opt.dbverbose):
        print(f"==> User '{site.dbUser}' missing in MYSQL user table")
        return False
    # Check whether the database exists and whether dbUser has access to it.
    if not db.database_exists(params, site, opt.dbverbose):
        print(f"==> Database '{site.dbName}' not accessible by user '{site.dbUser}'")
        return False
    print(f"Database '{site.dbName}' accessible by user '{site.dbUser}'")
    return True

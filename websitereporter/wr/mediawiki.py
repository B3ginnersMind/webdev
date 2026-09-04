import os, re
from wr.config import settings
from wr import utils as u
from wr.utils import CmsPaths, cms_types, Release
from wr.upload_check import sus_files
from pathlib import Path
_UNSET_RELEASE = Release()

# Important to use the pool owner to prevent damage if the site has been hacked.
def mediawiki_cli(owner: str, script: str = "run.php") -> str:
    """ Returns the Mediawiki CLI command. """
    if settings.run_as_root:
        return f"sudo -u {owner} " + settings.mediawiki_cli + script
    return settings.mediawiki_cli + script

def detect_mediawiki_version(folder: Path) -> Release:
    """
    folder is the root of a MediaWiki installation.
    Look within includes/Defines.php after:
        define( 'MW_VERSION', 'VERSION' );
    und return VERSION zurück (e.g. '1.43.6').
    """
    defines_path: Path = folder / "includes" / "Defines.php"
    if not defines_path.is_file():
        raise FileNotFoundError(f"Defines.php not found in: {defines_path}")
    pattern = re.compile(
        r"define\s*\(\s*['\"]MW_VERSION['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)\s*;"
    )
    with open(defines_path, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                release = match.group(1)
                return Release(release)
    return _UNSET_RELEASE

def check_mediawiki_sites(cms: CmsPaths):
    if len(cms.mediawiki_sites) == 0:
        u.print_headline("Mediawiki sites: none")
    else:
        u.print_headline("==> Mediawiki sites")
    for dir in cms.mediawiki_sites:
        u.print_double_line()
        print("==> Mediawiki website at:", dir)
        owner = str(dir.owner())  # type: ignore
        print("Owner:", owner)
        os.chdir(dir)
        if u.has_basic_auth(dir):
            print("--> WEBSITE PROTECTED BY BASIC AUTH")

        run_file = dir / "maintenance" / "run.php"
        show_sitestats_file = dir / "maintenance" / "showSiteStats.php"
        if not run_file.is_file():
            version = detect_mediawiki_version(dir)
            if version == _UNSET_RELEASE:
                print(f"Mediawiki version: TOO OLD!")
            else: 
                print(f"Mediawiki version: {version}")
            if show_sitestats_file.is_file():
                u.run_command(f"{mediawiki_cli(owner, 'showSiteStats.php')}")
        else:
            u.run_command(f"{mediawiki_cli(owner)} Version.php")
            u.run_command(f"{mediawiki_cli(owner)} showSiteStats.php")
            sus_files(dir, cms_types.mediawiki_checked_subdirs)

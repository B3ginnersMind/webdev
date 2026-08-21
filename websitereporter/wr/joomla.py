import os, re
from wr.config import settings
from wr.utils import CmsPaths, Release
from wr.utils import print_line, print_double_line, run_command
from pathlib import Path
_UNSET_RELEASE = Release()

def detect_joomla_version(dir: Path) -> Release:
    """
    Detects the Joomla version by running the Joomla CLI command.
    Returns the version as a string (e.g., '4.3.1').
    """
    os.chdir(dir)
    version = _UNSET_RELEASE
    joomla_xml_path: Path = Path(dir) / "administrator/manifests/files/joomla.xml"
    if not joomla_xml_path.is_file():
        print("joomla.xml not found")
        return version
    pattern = re.compile(r"<version>(.*?)</version>")
    with open(joomla_xml_path, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                version = Release(match.group(1))
                return version
    return version

# Important to use the pool owner to prevent damage if the site has been hacked.
def joomla_cli(owner: str) -> str:
    """
    Returns the Joomla CLI command.
    """
    if settings.run_as_root:
        return f"sudo -u {owner} " + settings.joomla_cli
    return settings.joomla_cli

# cli/joomla.php has been available since Joomla 4.0
# php cli/joomla.php core:version
def check_joomla_sites(cms: CmsPaths):
    print_double_line()
    if len(cms.joomla_sites) == 0:
        print("==> Joomla sites: none")
    print("==> Joomla sites:")
    for dir in cms.joomla_sites:
        print_line()
        print("==> Joomla website at:", dir)
        owner = str(dir.owner())  # type: ignore
        print("Owner:", owner)
        os.chdir(dir)
        version = detect_joomla_version(dir)
        if version == _UNSET_RELEASE:
            print("Joomla version could not be detected.")
        elif version <= Release("4.0.0"):
            print(f"Found Joomla version {version}")
            print("Joomla version < 4.0.0 still without full CLI.")
        else:
            run_command(f"{joomla_cli(owner)} core:update:check")
            run_command(f"{joomla_cli(owner)} update:extensions:check")
            if settings.show_cms_users:
                run_command(f"{joomla_cli(owner)} user:list")

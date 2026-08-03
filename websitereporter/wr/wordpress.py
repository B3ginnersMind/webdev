import os
from wr import utils as u
from wr.utils import CmsPaths
from wr.utils import print_line, print_double_line

# Important to use the pool owner to prevent damage if the site has been hacked.
def wp_cli(owner: str) -> str:
    """
    Returns the wp-cli command.
    """
    return f"sudo -u {owner} wp"

def check_wordpress_sites(cms: CmsPaths):
    print_double_line()
    if len(cms.wordpress_sites) == 0:
        print("==> Wordpress sites: none")
    print("==> Wordpress sites:")
    for dir in cms.wordpress_sites:
        print_line()
        print("==> Worpress website at:", dir)
        owner = str(dir.owner())  # type: ignore
        print("Owner:", owner)
        os.chdir(dir)
        u.run_command(f"{wp_cli(owner)} core version")
        u.run_command(f"{wp_cli(owner)} core check-update")
        u.run_command(f"{wp_cli(owner)} core verify-checksums")
        u.run_command(f"{wp_cli(owner)} plugin verify-checksums --all")
        u.run_command(f"{wp_cli(owner)} plugin list")
        # u.run_command(f"{wpcli(owner)} plugin status")



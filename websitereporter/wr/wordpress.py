import os
from wr.config import settings
from wr import utils as u
from wr.utils import CmsPaths

# Important to use the pool owner to prevent damage if the site has been hacked.
def wp_cli(owner: str) -> str:
    """
    Returns the wp-cli command.
    """
    if settings.run_as_root:
        return f"sudo -u {owner} " + settings.wp_cli
    return settings.wp_cli

def check_wordpress_sites(cms: CmsPaths):
    if len(cms.wordpress_sites) == 0:
        u.print_headline("Wordpress sites: none")
    else:
        u.print_headline("Wordpress sites:")
    for dir in cms.wordpress_sites:
        u.print_double_line()
        print("==> Wordpress website at:", dir)
        owner = str(dir.owner())  # type: ignore
        print("Owner:", owner)
        os.chdir(dir)
        if u.has_basic_auth(dir):
            print("--> WEBSITE PROTECTED BY BASIC AUTH")
        u.run_command(f"{wp_cli(owner)} core version")
        u.run_command(f"{wp_cli(owner)} core check-update")
        u.run_command(f"{wp_cli(owner)} core verify-checksums")
        u.run_command(f"{wp_cli(owner)} plugin verify-checksums --all")
        u.run_command(f"{wp_cli(owner)} plugin list")
        u.run_command(f"{wp_cli(owner)} theme list")
        # u.run_command(f"{wpcli(owner)} plugin status")
        if settings.show_cms_users:
            u.print_dots()
            value = u.get_shell_command_output(f"{wp_cli(owner)} user list --format=count")
            if value and value[0].isdigit():
                num_users = int(value[0])
                max_users = 50
                print("Number of users:", num_users)
                if num_users > max_users:
                    print(f"Over {max_users} Wordpress users: Only show administrators")
                    u.run_command(f"{wp_cli(owner)} user list --role=administrator")
                else:
                    u.run_command(f"{wp_cli(owner)} user list")           
        if settings.wordfence_cli != "none":
           u.run_command(f"{settings.wordfence_cli} vuln-scan --no-banner .")

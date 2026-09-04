import os
from wr.utils import CmsPaths
import wr.utils as u

def check_drupal_sites(cms: CmsPaths):
    if len(cms.drupal_sites) == 0:
        u.print_headline("Drupal sites: none")
    else:
        u.print_headline("Drupal sites")
    for dir in cms.drupal_sites:
        u.print_double_line()
        print("==> Drupal website at:", dir)
        owner = str(dir.owner())  # type: ignore
        print("Owner:", owner)
        os.chdir(dir)
        if u.has_basic_auth(dir):
            print("--> WEBSITE PROTECTED BY BASIC AUTH")
        # get version for Drupal 8/9/10/11
        command = 'cat core/lib/Drupal.php | grep "const VERSION"'
        u.get_shell_command_output(command, verbose=True)
        

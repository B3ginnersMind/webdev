import os
from wr.utils import CmsPaths
import wr.utils as u

def check_drupal_sites(cms: CmsPaths):
    u.print_double_line()
    if len(cms.drupal_sites) == 0:
        print("==> Drupal sites: none")
    print("==> Drupal sites:")
    for dir in cms.drupal_sites:
        u.print_line()
        print("==> Drupal website at:", dir)
        owner = str(dir.owner())  # type: ignore
        print("Owner:", owner)
        os.chdir(dir)
        # get version for Drupal 8/9/10/11
        command = 'cat core/lib/Drupal.php | grep "const VERSION"'
        u.get_command_output(command, verbose=True)

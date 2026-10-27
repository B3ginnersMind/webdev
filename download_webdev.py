#!/usr/bin/env python
import glob, importlib.util, os, requests, shutil, zipfile
__version__ = "1.1.0"
LATEST_WEBDEV_DIR = "latest_webdev"

print("\nThis is download_webdev version", __version__)
script_folder = os.path.dirname(os.path.realpath(__file__))
os.chdir(script_folder)

# download webdev archive
# curl -L -o webdev.zip https://github.com/B3ginnersMind/webdev/zipball/main/
url = 'https://github.com/B3ginnersMind/webdev/zipball/main/'
response = requests.get(url)
with open('webdev.zip', 'wb') as f:
    f.write(response.content)

# unzip webdev.zip
with zipfile.ZipFile('webdev.zip', 'r') as zip_ref:
    zip_ref.extractall('.')

# look for newest subfolder which stems from unzipping
latest_webdev_unzip = max(glob.glob(os.path.join('.', 'B3ginnersMind-webdev*/')), 
                        key=os.path.getmtime)
print('Latest folder with webdev content:', latest_webdev_unzip)

script_file = "install_webdev.py"
modul_name = "install_webdev"
script_path = os.path.join(latest_webdev_unzip, script_file)
print('webdev can be installed with:', script_path)
# Return a module spec based on a file location.
spec = importlib.util.spec_from_file_location(modul_name, script_path)
assert spec is not None
# Create a new module based on the spec.
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
# Execute the module in its own namespace.
spec.loader.exec_module(module)

print('Should the installation script be executed now?')
module.query_continue()
print('Calling installation script...')
# Call the main function of the imported module
module.main()

# Tidy up installation files
latest_dir = os.path.join(script_folder, LATEST_WEBDEV_DIR)
print("\nThe downloaded archive webdev.zip will be removed.")
print("Its content will be saved in", latest_dir)
print("Any content in this folder will be deleted.")
module.query_continue()
os.remove('webdev.zip')
if os.path.exists(latest_dir):
    print("Removing existing folder", latest_dir)
    shutil.rmtree(latest_dir)
print("Renaming", latest_webdev_unzip, "to", latest_dir)
os.rename(latest_webdev_unzip, latest_dir)

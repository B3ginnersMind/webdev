#!/usr/bin/env python
import glob, importlib.util, os, requests, zipfile

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
latest_webdev_dir = max(glob.glob(os.path.join('.', 'B3ginnersMind-webdev*/')), key=os.path.getmtime)
print('Latest folder with webdev content:', latest_webdev_dir)

script_file = "install_webdev.py"
modul_name = "install_webdev"
script_path = os.path.join(latest_webdev_dir, script_file)
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

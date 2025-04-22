#!/usr/bin/env python
"""
-----------------------------------------------------------------
Output running virtual hosts, and used PHP FPM versions
on an Ubuntu server with Apache 2.
The output is shortened for clarity.
Manfred Koerkel, 22.04.2025
"""
from subprocess import PIPE, run
from datetime import datetime
import re
__version__ = "1.00"

def get_output(command):
    """runs shell command and returns output as list of strings"""
    print("-----------------------------------------------------------------")
    print('Processing', '"'+command+'"')
    print("-----------------------------------------------------------------")
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True,
                 shell=True)
    result.stdout.strip()
    lines = result.stdout.splitlines()    
    lines = [l.strip() for l in lines]
    lines = [" ".join(l.split()) for l in lines]
    return lines

print('Run', __file__)
print('Query date:', datetime.today().strftime('%Y-%m-%d'))

vhosts = get_output("apache2ctl -S")
for l in vhosts:
    if (l.startswith('VirtualHost')):
       print(l)
    elif (l.startswith('*:')):
       print(l)
    elif (l.startswith('port')):
       l = re.sub('/etc/apache2/sites-enabled/', '', l)
       print(l)
    elif (l.startswith('alias')):
       print('     '+l)

phpversions = get_output("systemctl | grep PHP")
for l in phpversions:
    print(l)

search_used_php_versions = (
    "find /etc/apache2/sites-available -type f -name '*.conf'"
    " -exec grep 'fpm.sock' {} +"   
)
usedphp_raw = get_output(search_used_php_versions)
# shortend output
usedphp_shortened = []
for l in usedphp_raw:
    l = re.sub('/etc/apache2/sites-available/', '', l)
    l = re.sub('proxy:unix:/var/run/php/', '', l)
    l = re.sub('SetHandler ', '', l)
    l = re.sub('.sock\|fcgi://localhost/', '', l)
    usedphp_shortened.append(l)
# get max length of config name
max_len_conf = max(len(l.split()[0]) for l in usedphp_shortened)
# aliggn the output
for l in usedphp_shortened:
    conf, phpversion = l.split()
    line_aligned = f"{conf.ljust(max_len_conf)} {phpversion}"
    print(line_aligned)

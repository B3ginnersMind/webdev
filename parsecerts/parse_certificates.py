from datetime import datetime
import re
import os.path

def shape_expiry(expiry_line):
   expiry_line = re.sub(' Date', '', expiry_line)
   expiry_line = re.sub(' Name', '', expiry_line)
   expiry_line = re.sub('\:', '', expiry_line)
   expiry_line = re.sub('\d+\+\d+', '', expiry_line)
   return expiry_line

def get_valid_days(line):
   match = re.search('VALID \d+ days', line)
   substring = match.group()
   substring = re.sub('VALID ', '', substring)
   substring = re.sub(' days', '', substring)
   return int(substring)

certbot_output = 'certificates.txt'
print('Run', __file__)
print('Processing the output of "sudo certbot certificates"')
print('Output expected in file', '"' + certbot_output + '"')
print('Query date', datetime.today().strftime('%Y-%m-%d'))
if not os.path.isfile(certbot_output):
   print(certbot_output, 'is missing')
   quit()
cert_file = open(certbot_output, mode='r')
lines_read = cert_file.readlines()

for i, l in enumerate(lines_read):
    lines_read[i] = l.strip()

max_len = 0
for l in lines_read:
   if (l.startswith('Certificate Name')):
      if len(l) > max_len:
         max_len = len(l)

certs = []
cert = ''
for l in lines_read:
   if (l.startswith('Certificate Name')):
      cert = l.ljust(max_len)
   if (l.startswith('Expiry')):
      l = cert + '  ' + l
      l = shape_expiry(l)
      # certs.append(l)
      days = get_valid_days(l)
      certs.append((days, l))
      # print(days)

# data.sort(key=lambda tup: tup[1])
# data.sort(key=lambda tup: tup[1])
certs.sort(key=lambda tup: tup[0])

for l in certs:
   print(l[1])
      

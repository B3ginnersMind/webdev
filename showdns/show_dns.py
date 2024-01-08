#!/usr/bin/env python
"""
-----------------------------------------------------------------
From DNS, some records of a list of domains are queried.

The name of the file containing the domains has to be entered.
Optionally, a file with known host IP4 addresses may be entered.
These files are expected to be in the current working directory.
Optionally, the IP4 address of an alternative nameserver may be entered.
Either only the A records or A, TXT, MX, CNAME and NS records are queried.

The output is written to the current folder with filenames
show_ips_domainFile or show_dns_domainFile, respectively, where
domainFile is the filename of the entered file with the domains.

The domainFile may contain comment lines marked with # at the beginning.
After the domains, there may be a comment in each line.

The knownHosts file should contain one host on each line.
Each line should have the format:
IP4    NAME     COMMENT
where IP4 is the IP address of the host, NAME is an arbitrary name for 
the host and COMMENT is any comment. The data has to be space-separated.
IP4 and NAME must not contain spaces. COMMENT may contain spaces.

The dnspython toolkit is used for the query tasks.
Installation on Ubuntu: "sudo apt install python3-dnspython"
Manfred Koerkel, 06.01.2024
"""
import argparse, dns.resolver, os, pathlib, platform, sys, time, warnings
from subprocess import PIPE, run
__version__ = "1.0"

def is_platform_linux():
    """return True if platform is Linux"""
    return platform.system() == 'Linux'

def check_platform_ok():
    """if platform is neither Linux nor Windows quit"""
    feasible_platforms = ('Linux', 'Windows')
    p = platform.system()
    if p.endswith(feasible_platforms):
        return
    print('infeasible platform:', p)
    quit()

def get_output(command):
    """runs shell command and returns output in string"""
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    return result.stdout.strip()

def replace_byname(hosts: list, ip: str) -> str:
    """ replace IP by name if the IP is known """
    for i in range(len(hosts)):
        if hosts[i][0] == ip:
            ip = hosts[i][1]
    return ip

def is_subdomain(d):
    """return whether domain is a subdomain"""
    return d.count('.') > 1

# https://dnspython.readthedocs.io/en/latest/resolver-class.html
class MyResolver:
    """wrapper class for dns.resolver.Resolver"""
    def __init__(self, nameserver='', hostlist=[], output=sys.stdout):
        self.hosts = hostlist
        self.out = output
        self.res = dns.resolver.Resolver()
        self.rectypes = ['A', 'TXT', 'MX', 'CNAME', 'NS']
        if nameserver != '':
            used_nameservers = []
            used_nameservers.append(nameserver)
            self.res.nameservers =  used_nameservers

    def domain_nonexistent(self, name):
        """uses 'dig' on Linux to check URL existence"""
        if is_platform_linux():
            return get_output('dig +short '+ name) == ""
        try:
#           self.res.query(name, 'A')     # works with dnspython 1.16
            self.res.resolve(name, 'A')
            return False
        except:
            return True

    def query_records(self, name, comment):
        print('Domain', name)
        print('\n Domain:', name, file=self.out)
        if self.domain_nonexistent(name):
            print(' A     :', '<non-existent>', file=self.out)
            return
        if (comment != ''):
            print(' Note  :', comment, file=self.out)
        for t in self.rectypes:
            # do not look for CNAME records in case of bare domains
            replaceIp = (t == 'A')
            recordType = ' ' + t.ljust(6) + ':'
            try:
                # returns object of type dns.resolver.Answer
                # query works with dnspython 1.16
                #answers = self.res.query(name, t)           
                answers = self.res.resolve(name, t)
                for record in answers:
                    r = record.to_text()
                    if replaceIp: r = replace_byname(knownhosts, r)
                    print(recordType, r, file=self.out)
            except:
                continue
                
    def print_ip(self, domain, host, comment):
        domain = ' ' + domain.ljust(33) + ':'
        host = host.ljust(20) + ':'
        print(domain, host, comment, file=self.out)

    def query_ip(self, domain, comment):
        print('Domain', domain)
        if self.domain_nonexistent(domain):
            self.print_ip(domain, '<non-existent>', comment)
            return
        try:
            # returns object of type dns.resolver.Answer
            answers = self.res.query(domain, 'A')
            for record in answers:
                r = record.to_text()
                r = replace_byname(self.hosts, r)
                self.print_ip(domain, r, comment)
        except dns.resolver.NoAnswer:
            self.print_ip(domain, '<no answer>', comment)
        except dns.resolver.NXDOMAIN:
            self.print_ip(domain, '<non-existent>', comment)
        except dns.exception.DNSException as e:
            print(type(e))
            self.print_ip(domain, repr(e), comment)
        except:
            self.print_ip(domain, '<unexpected error>', comment)

    def get_nameservers(self):
        return self.res.nameservers

#========================================================================
# argparse will test for the required argument
#========================================================================
p = argparse.ArgumentParser(description=__doc__,
                    formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("domainFile", help="file containing domains to be queried")
p.add_argument("-ip", "--onlyip", help="query only IP from A record", 
               action="store_true")
p.add_argument("-k", "--knownHosts", 
               help="optional file containing known host's IP4 addresses")
p.add_argument("-ns", "--nameServer", default='',
               help="optional IP4 address of queried DNS server")
p.add_argument(
    "-v", "--version", action='version', 
    version='%(prog)s version {version}'.format(version=__version__))
args = p.parse_args()

#========================================================================
# Switch off deprecation warning:
# To get code which works both for dnspython 1.16 and 2.2,  query() 
# instead of resolve() has to be used with class dns.resolver.Resolver.
# query() is labelled as deprecated in dnspython 2.2.
#========================================================================
#warnings.filterwarnings("ignore", category=DeprecationWarning) 

#========================================================================
# initialize data
#========================================================================
currenttime = time.strftime('%d.%m.%Y %H:%M')

script_name = os.path.basename(__file__)
script_basename = pathlib.Path(__file__).stem
if args.onlyip:
    outputfile = 'show_ips_' + args.domainFile
else:
    outputfile = 'show_dns_' + args.domainFile

# are there known hosts?
knownhosts = []
if args.knownHosts != None:
    with open(args.knownHosts, 'r') as f:
        for line in f:
            linelist = line.split(maxsplit=2)
            if (len(linelist) > 1):
                knownhosts.append(linelist)
    f.close()    

o = open(outputfile, 'w')
# Possible nameservers: default: '', google: 8.8.8.8, cloudflare: 1.1.1.1
myResolver = MyResolver(hostlist=knownhosts, nameserver=args.nameServer, output=o)

#========================================================================
# start procedure
#========================================================================
print('== DNS-Records von GWUP-Domains ==', '\n', file=o)
print(' Records were queried by Python script "' + script_name + '"', file=o)
print(' Applied version of dnspython: ', dns.__version__, file=o)
print(' On output known IPs are replaced by its below names.', file=o)
print('\n Query time:', currenttime, file=o)
print(' Nameserver:', myResolver.get_nameservers(), file=o)

if len(knownhosts) == 0:
    print(' There were no known hosts entered.', file=o)
else:
    print(' Hosts file:', args.knownHosts, file=o)
    for i in range(len(knownhosts)):
        ip = knownhosts[i][0].ljust(16)
        host = knownhosts[i][1].ljust(20)
        comment = ''
        if (len(knownhosts[i]) > 2):
            comment = knownhosts[i][2].strip()
        print(' Known host:', ip, host, comment, file=o)

print(' ', file=o)
print(' Queried Domains:', file=o)
print(' ================', file=o)

#========================================================================
# read domain list
#========================================================================
domains = []
domain_comments = []
with open(args.domainFile, 'r') as f:
    for line in f:
        if line.isspace():         # skip empty lines
            continue
        line = line.strip(' \n')
        if line[0] == '#':         # comment line
            domains.append('')
            domain_comments.append(line)
        else:
            two_tupel = line.split(maxsplit=1)
            domains.append(two_tupel[0])
            if len(two_tupel) > 1:
                domain_comments.append(two_tupel[1])
            else:
                domain_comments.append('')
f.close()

#========================================================================
# run queries. also check all www subdomains.
#========================================================================
if args.onlyip:
    query_function = MyResolver.query_ip
else:
    query_function = MyResolver.query_records

LINE = ' ' + '-' * 79
comment = False
for n in range(0, len(domains)):
    d = domains[n]
    note = domain_comments[n]
    if d == '':                # comment line
        if comment == False:
            print(' ', file=o)
            print(LINE, file=o)
            comment = True
        print(' ' + note, file=o)
        continue
    if comment == True:
        print(LINE, file=o)
        comment = False
    query_function(myResolver, d, note)
    if not is_subdomain(d):
        query_function(myResolver, 'www.' + d, note)

print('Output file written:', outputfile)
print('Queried from nameserver:', myResolver.get_nameservers())


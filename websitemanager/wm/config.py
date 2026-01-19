import configparser, os, textwrap
from wm.utils import abort, print_line, WRAP_LENGTH

class Parameters:

    def __init__(self, config_file: str):
        self.section = "wm_config"
        print('Reading:', config_file)
        print('Section:', self.section)
        self.config_file = config_file
        if not os.path.exists(config_file):
            abort('parameter table file "' + config_file + '"is missing')  
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.params = ['runasroot', 'scp', 'sql', 'sqldump', 'sqldumpoptions', 
                       'sqlmainuser', 'sqlmainpw', 'sitedumpdir', 'snapshotdir', 
                       'logdir', 'wwwroot', 'wwwusergroup', 'wwwbanothers', 
                       'remotelocation']
        self.checkParams()

    def show(self):
        print_line()
        print('content of parameter table "' + self.config_file + '":')
        maxParamLength = 0
        for p in self.params:
            maxParamLength = max(maxParamLength, len(p))
        indent = (maxParamLength + 3) * ' '
        for p in self.params:
            v = self.config.get(self.section, p)
            line = p.ljust(maxParamLength) + ' = ' + "'" + v + "'"
            wrappedLine = textwrap.fill(line, WRAP_LENGTH, subsequent_indent=indent)
            print(wrappedLine)
        print_line()

    def checkParams(self):
        missingParams = ''
        for p in self.params:
            if not self.config.has_option(self.section, p):
                missingParams += ' ' + p
        if missingParams != '':
           abort('missing parameters in "' + self.config_file 
                 + '": ' + missingParams)
           
    def get(self, param: str) -> str:
        if not self.config.has_option(self.section, param):
            abort('===> param', param, 'missing in index')
        return self.config.get(self.section, param)

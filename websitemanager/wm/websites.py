
import csv
from dataclasses import dataclass, fields
from collections import Counter
from wm.utils import abort, print_line

@dataclass
class WebSiteData:
    siteName : str = "none"
    save : str = "0"
    wwwSubdir : str = "none"
    host : str = "none"
    dbName : str = "none"
    dbUser : str = "none"
    dbPassWord : str = "none"
    comment : str = "none"

    @classmethod
    def field_names(cls) -> list[str]:
        """Returns all attribute names as a string list."""
        return [f.name for f in fields(cls)]
    
    @classmethod
    def field_widths(cls) -> list[int]:
        """Returns length of all attribute names as an  list of ints."""
        return [len(f.name) for f in fields(cls)]
    
    def show(self, info: str="") -> None:
        print("------- WebSiteData contents ---------", info)
        for name, value in self.__dict__.items():
            print(f"{name}: {value}")
        print("--------------------------------------")


class WebSiteTable:
    def __init__(self, tablePath: str):
        print('Reading:', tablePath)
        self.columns = WebSiteData.field_names()
        self.widths = WebSiteData.field_widths()
        # header line does not count as website
        self.numWebsites = -1
        self.header: list[str] = []
        self.site2index: dict[str,int] = {}
        self.table: list[list[str]] = []
        try:
            # module csv handles newline itself!
            with open(tablePath, 'r', encoding='utf-8', newline='') as csv_datei:
                reader = csv.reader(csv_datei, delimiter=' ')
                for line in reader:
                    # remove empty columns due to muliple blanks
                    line = list(filter(('').__ne__, line))
                    # skip empty and comment lines
                    if len(line) > 0 and line[0][0] != "#":
                        self.numWebsites += 1
                        if self.numWebsites >= 1:
                            if len(line) < len(self.columns):
                                abort("too few columns in line:", str(line))
                            self.table.append(line)
                            self.site2index[line[0]] = self.numWebsites - 1
                        else:
                            self.header = line
                            self.checkheader()
                            self.col2index = {c: i for i, c in enumerate(self.header)}
        except FileNotFoundError:
            abort(f"FEHLER: Die Datei '{tablePath}' wurde nicht gefunden.")
        if self.numWebsites < 1:
            abort("no website data in table:", tablePath)
        for j in range(len(self.columns)):
            for i in range(self.numWebsites):
                self.widths[j] = max(self.widths[j], len(self.table[i][j]))
        self.checkSites()

    def checkheader(self):
        duplicateCols = {v for v, count in Counter(self.header).items() if count > 1}
        if duplicateCols:
            abort("duplicate headers in table:", str(duplicateCols))
        colSet = set(self.columns)
        headerSet = set(self.header)
        if colSet != headerSet:
            missing = colSet - headerSet
            extra = headerSet - colSet
            if missing:
                abort("missing headers in table:", str(missing))
            if extra:
                abort("extra headers in table:", str(extra))    

    def checkSites(self):
        siteCol = self.col2index['siteName']
        sitesList = [self.table[i][siteCol] for i in range(self.numWebsites)]
        duplicateSites = {v for v, count in Counter(sitesList).items() if count > 1}
        if duplicateSites:
            abort("duplicate siteName in table:", str(duplicateSites))

    def showall(self, title: str="")  -> None:
        self.show(skippedCols=[], title=title)

    def show(self, skippedCols: list[str] = ['dbUser', 'dbPassWord'], title: str=""):
        print_line()
        headline = "    "
        if title:
            print(headline + "***", title, "***")
        for j in range(len(self.header)):
            if self.header[j] not in skippedCols:
                headline += self.header[j].ljust(self.widths[j]) + "  "
        print(headline)
        skippedColIndices = [self.col2index[c] for c in skippedCols]
        for i in range(self.numWebsites):
            line = f"{i:2d}  "
            for j in range(len(self.columns)):
                if j not in skippedColIndices:
                    value = self.table[i][j]
                    line += value.ljust(self.widths[j]) + "  "
            print(line)
        print_line()

    def getNumWebsites(self) -> int:
        return self.numWebsites
    def hasSite(self, siteName: str) -> bool:
        return siteName in self.site2index
    def getSite(self, siteName: str) -> WebSiteData:
        return self.getData(self.site2index[siteName])
    def getData(self, row: int) -> WebSiteData:
        data = {col: self.table[row][self.col2index[col]] for col in self.columns}
        # ** means: take each key-value pair as a named parameter.
        return WebSiteData(**data)

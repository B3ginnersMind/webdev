import re
from functools import total_ordering
from types import NotImplementedType

def is_integer(text: str) -> bool:
    try:
        int(text)
        return True
    except ValueError:
        return False

@total_ordering
class Release:
    def __init__(self, release: str="") -> None:
        if release == "Unpatched":
            self.raw_release: str = release
            # Set to a very high version number for comparison
            self.parts: tuple[int, ...] = (9999, 0, 0)  
            self.is_nonnumeric: bool = False
            return
        elif release == "":
            self.raw_release: str = "Undefined"
            self.parts: tuple[int, ...] = (0, 0, 0)
            self.is_nonnumeric: bool = True
            return
        self.raw_release: str = release.strip()
        self.parts: tuple[int, ...] = ()
        self.is_nonnumeric: bool = False

        # Trennen am Punkt
        raw_parts = self.raw_release.split(".")
        
        parsed_parts: list[int] = []
        for part in raw_parts:
            # Prüfen, ob der Abschnitt rein numerisch ist
            if is_integer(part):
                parsed_parts.append(int(part))
            else:
                # Enthält Buchstaben oder Sonderzeichen
                self.is_nonnumeric = True
                break

        if not self.is_nonnumeric and parsed_parts:
            self.parts = tuple(parsed_parts)
        else:
            self.is_nonnumeric = True

    def __lt__(self, other: object) -> bool | NotImplementedType:
        if not isinstance(other, Release):
            return NotImplemented
        # nichtnumerische Versionen lassen sich nicht vergleichen
        if self.is_nonnumeric or other.is_nonnumeric:
            raise ValueError(
                f"Vergleich nicht möglich: Mindestens eine Version ist nichtnumerisch "
                f"('{self.raw_release}' vs. '{other.raw_release}')"
            )
        # Python vergleicht Tupel automatisch hierarchisch Element für Element
        # print(f"{self.parts} < {other.parts} = {self.parts < other.parts}")
        return self.parts < other.parts

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Release):
            return NotImplemented
        if self.is_nonnumeric or other.is_nonnumeric:
            return False
        return self.parts == other.parts

    def __str__(self) -> str:
        if self.is_nonnumeric:
            return f"{self.raw_release} (nonnumeric)"
        return ".".join(str(p) for p in self.parts)

    def __repr__(self) -> str:
        return f"Release('{self.raw_release}')"

    # Test whether current_verion > patch_version if patch_version is partially non-numeric.
    def is_greater_than(self, patch_version: str) -> bool:
        """Compares thicurrent_versions version with another and returns True if it is lower."""
        if self.is_nonnumeric:
            raise ValueError(
                f"Vergleich nicht möglich: (erste) Basis-Version ist nichtnumerisch "
                f"('{self.raw_release}' vs. '{patch_version}')"
            )
        parts = re.split(r"[._\-\s]+", patch_version)
        parsed_parts: list[int] = []
        has_nondigit = False
        for part in parts:
            if part.isdigit():
                parsed_parts.append(int(part))
            else:
                has_nondigit = True
                break
        # Cannot be decided
        if not parsed_parts:
            return False
        patch_release = Release(".".join(str(part) for part in parsed_parts))
        greater_than = self > patch_release
        if greater_than:
            return True
        if self == patch_release and has_nondigit:
            return True
        return False

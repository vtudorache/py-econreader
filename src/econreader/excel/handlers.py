import xml.parsers.expat

from enum import Enum
from typing import BinaryIO, NamedTuple


class BaseHandler:

    def start_element(self, name: str, attrs: dict[str, str]) -> None:
        pass

    def end_element(self, name: str) -> None:
        pass

    def character_data(self, data: str) -> None:
        pass

    def handle(self, f: BinaryIO) -> None:
        xp = xml.parsers.expat.ParserCreate()
        xp.StartElementHandler = self.start_element
        xp.CharacterDataHandler = self.character_data
        xp.EndElementHandler = self.end_element
        xp.ParseFile(f)


class Sheet(NamedTuple):
    name: str
    sheet_id: int
    r_id: str


class WorkbookHandler(BaseHandler):

    SHEET_TAG = "sheet"

    NAME_ATTR = "name"
    ID_ATTR = "r:id"
    SHEET_ID_ATTR = "sheetId"

    def __init__(self) -> None:
        self.sheets: list[Sheet] = []

    def start_element(self, name: str, attrs: dict[str, str]) -> None:
        if name == self.SHEET_TAG:
            sheet_name, sheet_id, r_id = None, None, None
            for attr_name, attr_value in attrs.items():
                if attr_name == self.NAME_ATTR:
                    sheet_name = attr_value
                    continue
                if attr_name == self.ID_ATTR:
                    r_id = attr_value
                    continue
                if attr_name == self.SHEET_ID_ATTR:
                    try:
                        sheet_id = int(attr_value)
                    except TypeError, ValueError:
                        pass
            if sheet_name and r_id and isinstance(sheet_id, int):
                self.sheets.append(Sheet(sheet_name, sheet_id, r_id))


class SharedStringsLevel(Enum):
    NONE = 0
    SI = 1
    TEXT = 2


class SharedStringsHandler(BaseHandler):

    SI_TAG = "si"
    T_TAG = "t"

    def __init__(self) -> None:
        self.strings: list[str] = []
        self._level: SharedStringsLevel = SharedStringsLevel.NONE
        self._text_data: list[str] = []

    def start_element(self, name: str, attrs: dict[str, str]) -> None:
        if name == self.SI_TAG:
            self._level = SharedStringsLevel.SI
            return
        if self._level == SharedStringsLevel.SI and name == self.T_TAG:
            self._level = SharedStringsLevel.TEXT

    def character_data(self, data: str) -> None:
        if self._level == SharedStringsLevel.TEXT:
            self._text_data.append(data)

    def end_element(self, name: str) -> None:
        if self._level == SharedStringsLevel.TEXT and name == self.T_TAG:
            self._level = SharedStringsLevel.SI
            return
        if self._level == SharedStringsLevel.SI and name == self.SI_TAG:
            self.strings.append(''.join(self._text_data))
            self._text_data.clear()


class RelID(NamedTuple):
    r_id: str
    path: str


class RelsHandler(BaseHandler):

    RELATIONSHIP_TAG = "Relationship"
    ID_ATTR = "Id"
    TARGET_ATTR = "Target"

    def __init__(self) -> None:
        self.rels: list[RelID] = []

    def start_element(self, name: str, attrs: dict[str, str]) -> None:
        if name == self.RELATIONSHIP_TAG:
            r_id, path = None, None
            for attr_name, attr_value in attrs.items():
                if attr_name == self.ID_ATTR:
                    r_id = attr_value
                    continue
                if attr_name == self.TARGET_ATTR:
                    path = attr_value
            if r_id and path:
                real_prefixes = ("xl/", "/")
                if not path.startswith(real_prefixes):
                    path = "xl/{}".format(path)
                path = path.lstrip("/")
                self.rels.append(RelID(r_id, path))


class SheetLevel(Enum):
    DEFAULT = 0
    CELL = 1
    VALUE = 2


class SheetValuesHandler(BaseHandler):

    CELL_TAG = "c"
    VALUE_TAG = "v"
    REF_ATTR = "r"
    TYPE_ATTR = "t"
    SI_ATTR_VALUE = "s"

    def __init__(self, strings: list[str]) -> None:
        self._strings = strings
        self._level = SheetLevel.DEFAULT
        self._cell_address = None
        self._is_shared = False
        self._value_parts = []
        self.values = {}

    def start_element(self, name: str, attrs: dict[str, str]) -> None:
        if name == self.CELL_TAG:
            self._level = SheetLevel.CELL
            for attr_name, attr_value in attrs.items():
                if attr_name == self.REF_ATTR:
                    self._cell_address = attr_value
                    continue
                if attr_name == self.TYPE_ATTR:
                    self._is_shared = (attr_value == self.SI_ATTR_VALUE)
            return
        if self._level == SheetLevel.CELL and name == self.VALUE_TAG:
            self._level = SheetLevel.VALUE

    def character_data(self, data: str) -> None:
        if self._level == SheetLevel.VALUE:
            self._value_parts.append(data)

    def end_element(self, name: str) -> None:
        if name == self.VALUE_TAG:
            self._level = SheetLevel.CELL
            return
        if name == self.CELL_TAG:
            self._level = SheetLevel.DEFAULT
            if self._cell_address:
                raw_value = ''.join(self._value_parts)
                value = raw_value
                if self._is_shared:
                    try:
                        i = int(raw_value)
                        value = self._strings[i]
                    except IndexError, TypeError, ValueError:
                        value = None
                        pass
                if value:
                    self.values[self._cell_address] = value
            self._value_parts.clear()


import zipfile

from .handlers import RelsHandler, SheetValuesHandler, SharedStringsHandler
from .handlers import WorkbookHandler


class ExcelFile:

	def __init__(self, path: str) -> None:
		self._path = path
		self._rels: list[handlers.RelID] = []
		self._sheets: list[handlers.Sheet] = []
		self._shared_strings: list[str] = []
		self._zip_file = None
		
	def __enter__(self) -> object:
		if self._zip_file is None:
			self.open()
		return self

	def __exit__(self, *args) -> bool:
		self.close()
		return False

	def open(self) -> None:
		# Open the archive
		self._zip_file = zipfile.ZipFile(self._path, "r")
		# Read the shared strings
		ssh = SharedStringsHandler()
		with self._zip_file.open("xl/sharedStrings.xml") as f:
			ssh.handle(f)
			self._shared_strings = ssh.strings
		del ssh
		# Read the workbook file list
		wbh = WorkbookHandler()
		with self._zip_file.open("xl/workbook.xml") as f:
			wbh.handle(f)
			self._sheets = sorted(wbh.sheets, key=lambda s: s.sheet_id)
		del wbh
		# Read the relationship list
		rsh = RelsHandler()
		with self._zip_file.open("xl/_rels/workbook.xml.rels") as f:
			rsh.handle(f)
			self._rels = rsh.rels
		del rsh

	def close(self) -> None:
		if self._zip_file is not None:
			self._zip_file.close()
			self._zip_file = None
			self._rels = []
			self._sheets = []
			self._shared_strings = []

	def sheets(self) -> dict[int, str]:
		if self._zip_file is not None:
			return dict((s.sheet_id, s.name) for s in self._sheets)

	def sheet_values(self, sheet: int | str) -> dict[str, str]:
		# Find r_id
		values = {}
		r_id = None
		if isinstance(sheet, int):
			for s in self._sheets:
				if s.sheet_id == sheet:
					r_id = s.r_id
					break
		elif isinstance(sheet, str):
			for s in self._sheets:
				if s.name == sheet:
					r_id = s.r_id
					break
		else:
			raise TypeError(sheet)
		# Find the path within the zip file
		path = None
		if r_id and self._rels:
			for rel in self._rels:
				if rel.r_id == r_id:
					path = rel.path
					break
		if path and self._zip_file:
			svh = SheetValuesHandler(self._shared_strings)
			with self._zip_file.open(path) as f:
				svh.handle(f)
				values.update(svh.values)
			del svh
		return values

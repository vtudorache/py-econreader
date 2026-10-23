import re

A1_RE = re.compile(r"\$?([A-Z]+)\$?([0-9]+)", re.IGNORECASE)
LETTERS = ''.join(chr(c) for c in range(ord('A'), ord('Z') + 1))
BASE = len(LETTERS)

def cs_to_value(s: str) -> int:
	"""Converts a column value given as text to the equivalent number."""
	n = 0
	for c in s.upper():
		if c not in LETTERS:
			raise ValueError(s)
		n = n * BASE + ord(c) - ord('A') + 1
	return n

def cs_from_value(n: int) -> str:
	"""Converts a column value given as number to the equivalent text."""
	s = []
	while n > 0:
		n -= 1
		n, r = divmod(n, BASE)
		s.append(chr(r + ord('A')))
	return ''.join(reversed(s))

def address_to_coordinates(s: str) -> tuple[int, int]:
	"""Converts an address given as A1 to integral coordinates (r, c)."""
	m = A1_RE.fullmatch(s)
	if not m:
		raise ValueError(s)
	cs, rs = m.group(1, 2)
	return int(rs), cs_to_value(cs)

def range_to_address_list(r: str, by_row: bool = True) -> list[str]:
	"""Converts an address range given as A1:A1 to a list of addresses."""
	try:
		ls, hs = r.split(":", 1)
	except ValueError:
		ls, hs = r, ""
	if not hs:
		# Adapt to addresses given as "A1:"
		hs = ls
	lr, lc = address_to_coordinates(ls)
	hr, hc = address_to_coordinates(hs)
	result = []
	if by_row:
		for rn in range(lr, hr + 1):
			for cn in range(lc, hc + 1):
				result.append('{}{}'.format(cs_from_value(cn), str(rn)))
	else:
		for cn in range(lc, hc + 1):
			for rn in range(lr, hr + 1):
				result.append('{}{}'.format(cs_from_value(cn), str(rn)))
	return result

def values_in_range(all_values: dict[str, str], cell_range: str, 
		by_row: bool = True, merge: bool = True) -> dict[str, str]:
	"""Retrieves the values in the given range, using the last value for the
	merged cells (that is the value of the first merged cell).
	"""
	result = {}
	if merge:
		last_value = None
		last_cn, last_rn = 0, 0
		for addr in range_to_address_list(cell_range, by_row):
			value = all_values.get(addr, last_value)
			result[addr] = value
			rn, cn = address_to_coordinates(addr)
			# Reset the merged value when changing the row or the column
			if by_row and last_rn != 0 and rn != last_rn:
				last_value = None
			elif (not by_row) and last_cn != 0 and cn != last_cn:
				last_value = None
			else:
				last_value = value
			last_rn, last_cn = rn, cn
	else:
		for addr in range_to_address_list(cell_range, by_row):
			value = all_values.get(addr, None)
			result[addr] = value
	return result

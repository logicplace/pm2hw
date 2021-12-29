# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import gettext
from typing import Literal, Optional

from ..config import config

base = os.path.dirname(__file__)
def split_ietf_tag(*langs: str):
	ret = []
	for x in langs:
		while x:
			ret.append(x)
			x = f"-{x}".rsplit("-", 1)[0]
	ret.append("en")
	return ret

default_lang = gettext.translation(
	"pm2hw",
	localedir=base,
	languages=split_ietf_tag(*config["general"]["language"].split(","))
)
current_lang = default_lang
available_languages = {"en", "ja"}


class FailInPlace(dict):
	def __init__(self, d={}, *, pfx: str = ""):
		super().__init__(d)
		self._pfx = pfx
		self._fmt = ""

	def __missing__(self, key): 
		return FailInPlace(pfx=f"{self._pfx}.{key}" if self._pfx else key)

	def __getattr__(self, attr):
		return self[attr]

	def __str__(self):
		if self._fmt:
			return f"{{{self._pfx}:{self._fmt}}}"
		return self._pfx.join("{}")

	def __format__(self, format_spec: str):
		# TODO: half-asleep and not sure how correct this is; works tho
		self._fmt = format_spec
		return super().__format__("")


class tstr(str):
	key: str
	value: str
	args: list
	data: Optional[dict]

	def __new__(self, value: str, **kw):
		return str.__new__(self, value)

	def __init__(self, value: str, *, key: str = ""):
		self.key = key or value
		self.value = value
		self.data = None

	# TODO: why isn't this enough for tk? C strings?
	def __str__(self):
		res = current_lang.gettext(self.key)
		if res == self.key:
			return str(self.value)
		if self.data is None:
			return res
		return res.format_map(self.data)

	def __add__(self, __s: str) -> str:
		return __s + str(self)

	def format(self, **kwargs):
		self.data = FailInPlace(kwargs)
		if isinstance(self.value, tstr):
			self.value.data.update(kwargs)
		return self

_ = tstr


def natural_size(size: int, out: Literal["bits", "bytes"] = "bytes"):
	""" Convert size in bytes to a more human-readable number. """
	# TODO: lozalized, for any languages that prefer it.
	if out == "bits":
		size *= 8
		if size < 1024:
			return f"{size} Bits"
	elif size < 1024:
		return f"{size} Bytes"
	
	# We only really need to MB, so just unrolling any loop
	si1 = size / 1024
	sx1 = size / 1000
	si2 = si1 / 1024
	sx2 = sx1 / 1000
	isi1 = int(si1)
	isx1 = int(sx1)
	isi2 = int(si2)
	isx2 = int(sx2)

	# Check if they divided evenly
	suffix = "iB" if out == "bytes" else "Bit"
	if si1 == isi1:
		if si2 == isi2:
			return f"{isi2} M{suffix}"
		return f"{isi1} K{suffix}"
	elif out == "bytes" and sx1 == isx1:
		if sx2 == isx2:
			return f"{isx2} MB"
		return f"{isx1} MB"
	
	if si2 >= 3:
		return f"~{isi2} M{suffix}"
	return f"~{isi1} K{suffix}"

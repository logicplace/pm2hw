# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import re
import gettext as m_gettext
from types import ModuleType
from typing import Any, Dict, List, Literal, Tuple

from pm2hw.config import config

_base = os.path.dirname(__file__)
_domains: Dict[str, Tuple[m_gettext.NullTranslations, str]] = {}
available_languages = {"en", "ja"}

# TODO: consider making this not delayed, and moving that to gui.i18n

def translation(domain: str, localedir: str = _base):
	lang_pref = config["general"]["language"]
	if domain in _domains:
		ret, lang = _domains[domain]
		if lang == lang_pref:
			ret._fallback = None  # Remove fallback for consistency
			return ret
		# Reload if the language preference changed

	languages: List[str] = []
	for x in lang_pref.split(","):
		while x:
			languages.append(x)
			x = f"-{x}".rsplit("-", 1)[0]
	
	if "en" not in languages:
		languages.append("en")
	
	try:
		ret = m_gettext.translation(domain, localedir=localedir, languages=languages)
	except OSError:
		ret = m_gettext.NullTranslations()
	_domains[domain] = (ret, lang_pref)
	return ret


def dgettext(domain: str, message: str):
	t = translation(domain)
	current = t.gettext(message)
	return SafeFormatString(current)


def dngettext(domain: str, msgid1: str, msgid2: str, n: int):
	t = translation(domain)
	current = t.ngettext(msgid1, msgid2, n)
	return SafeFormatString(current)


def gettext(message: str):
	return dgettext("pm2hw", message)


def delayed_dgettext(domain: str, message: str, *, fallback: str = ""):
	if not fallback:
		fallback = translation(domain).gettext(message)
	return DelayedLocalization(message, fallback=fallback, domain=domain, fn="gettext")


def delayed_gettext(message: str, *, fallback: str = ""):
	return delayed_dgettext("pm2hw", message, fallback=fallback)


class bind_domain:
	def __init__(self, domain: str, localedir: str = _base):
		self.domain = domain
		self.localedir = localedir

	def gettext(self, message: str):
		t = translation(self.domain, self.localedir)
		current = t.gettext(message)
		return SafeFormatString(current)

	def ngettext(self, msgid1: str, msgid2: str, n: int):
		t = translation(self.domain, self.localedir)
		current = t.ngettext(msgid1, msgid2, n)
		return SafeFormatString(current)

	def install_to_module(self, module: ModuleType, *args, **kwargs):
		for x in args:
			setattr(module, x, getattr(self, x))

		for x, y in kwargs.items():
			setattr(module, x, getattr(self, y))


class FailInPlace(dict):
	"""
	Class to return a formatting request as-is if the key doesn't exist.
	Example: "{foo} {bar}!".format_map(FailInPlace({"foo": "Hello"}))
	         == "Hello {bar}!"
	"""
	def __init__(self, d={}, *, pfx: str = ""):
		super().__init__(d)
		self._pfx = pfx

	def __missing__(self, key): 
		return FailInPlace(pfx=f"{self._pfx}.{key}" if self._pfx else key)

	def __getattr__(self, attr):
		return self[attr]

	def __format__(self, format_spec: str = ""):
		if format_spec:
			return f"{{{self._pfx}:{format_spec}}}"
		# Surround with braces
		return self._pfx.join("{}") if self._pfx else ""

	__str__ = __format__
	__repr__ = __format__


class SafeFormatString(str):
	def format(self, **kwargs):
		return self.format_map(FailInPlace(kwargs))


class DelayedLocalization:
	def __init__(self, *args, fallback: str, domain: str, fn: str):
		self.args = args
		self.fallback_text = fallback
		self.domain = domain
		self._fn = fn

		self.post_process: List[Tuple[str, List[Any]]] = []

	def _process(self, s: str) -> str:
		for fn, args in self.post_process:
			s = getattr(s, fn)(*args)
		return s

	def __str__(self) -> str:
		t = translation(self.domain)
		t.add_fallback(self)
		res: str = getattr(t, self._fn)(*self.args)
		return self._process(res)

	def gettext(self, message: str) -> str:
		return self._process(self.fallback_text)

	# Can add ngettext if needed

	def format(self, **kwargs):
		self.post_process.append(("format_map", [FailInPlace(kwargs)]))

	def replace(self, old: str, new: str, count=-1):
		self.post_process.append(("replace", [old, new, count]))


## Utility functions
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


def _m(m, *args):
	return {a: m for a in args}


natural_size_format = re.compile(r"(\d+) *(\S+)")
units_to_multiplier = {
	**_m(1, "bit", "bits"),
	**_m(8, "byte", "bytes"),
	**_m(1000, "kilobit", "kilobits"),
	**_m(1024, "kbit", "kbits", "kibibit", "kibibits"),
	**_m(1000 * 8, "kb", "kilobyte", "kilobytes"),
	**_m(1024 * 8, "k", "kib", "kbyte", "kbytes", "kibibyte", "kibibytes"),
	**_m(1000 ** 2, "megabit", "megabits"),
	**_m(1024 ** 2, "mbit", "mbits", "mebibit", "mebibits"),
	**_m(1000 ** 2 * 8, "mb", "megabyte", "megabytes"),
	**_m(1024 ** 2 * 8, "m", "mib", "mbyte", "mbytes", "mebibyte", "mebibytes"),
}


def parse_natural_size(s):
	n, units = natural_size_format.match(s).groups()
	units = units.lower()
	if units in units_to_multiplier:
		ret = int(n) * units_to_multiplier[units]
		tmp = ret / 8
		ret //= 8
		if tmp != ret:
			raise ValueError("number of bits must be divisible by 8")
		return ret
	raise ValueError(f"unknown units {units}")

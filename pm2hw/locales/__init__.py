import os
import gettext
from typing import Literal

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
	"pm2hw.gui",
	localedir=base,
	languages=split_ietf_tag(*config["general"]["language"].split(","))
)
current_lang = default_lang
available_languages = {"en"}


# https://stackoverflow.com/a/21754294/734170
class FailInPlace(dict):
	def __missing__(self, key): 
		return key.join("{}")


class tstr(str):
	key: str
	value: str
	args: list
	data: dict

	def __new__(self, value: str, **kw):
		return str.__new__(self, value)

	def __init__(self, value: str, *, key: str = ""):
		self.key = key or value
		self.value = value
		self.data = FailInPlace()

	# TODO: why isn't this enough for tk? C strings?
	def __str__(self):
		res = current_lang.gettext(self.key)
		if res == self.key:
			return str(self.value)
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

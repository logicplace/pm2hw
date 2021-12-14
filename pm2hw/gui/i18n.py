import os
import gettext
import tkinter as tk
from typing import List

from .. import locales
from ..config import config
from ..locales import _, available_languages, base, split_ietf_tag
from ..info.games import ROM

string_vars: List["TStringVar"] = []

class TStringVar(tk.StringVar):
	def __init__(self, value: str, *, master: tk.Widget = None):
		self._value = value
		if isinstance(value, _):
			value, name = str(value), value.key
		else:
			name = None
		super().__init__(master, value, name)
		string_vars.append(self)

	def __del__(self):
		string_vars.remove(self)
		super().__del__()

	def set(self, value):
		self._value = value
		super().set(str(value))

	def update(self):
		# Should only be called when the language changes
		if isinstance(self._value, _):
			super().set(str(self._value))

def init(r: tk.Tk):
	global root
	root = r

def change_language(*langs: str):
	s_langs = set(langs)
	diff = s_langs - available_languages
	if diff:
		missing = ", ".join(diff)
		raise ValueError(f"language(s) {missing} don't exist")

	locales.current_lang = gettext.translation(
		"pm2hw.gui",
		localedir=base,
		languages=split_ietf_tag(*langs)
	)
	config["general"]["language"] = ",".join(langs)
	for s in string_vars:
		s.update()

def localized_game_name(rom: ROM, fallback: str = ""):
	lookup = f"library.list.rom.{rom.acode}.{rom.internal}.{rom.crc32:08X}"
	
	value = fallback.format(rom=rom) if fallback else rom.internal
	ret = (_)(value, key=lookup)
	return ret

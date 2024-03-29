# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import tkinter as tk
import weakref
from typing import TYPE_CHECKING

from pm2hw.gui.util import WeakMethod
from pm2hw.info.games import ROM
from pm2hw.config import config
from pm2hw.locales import DelayedLocalization, available_languages, delayed_gettext


string_vars = (
	weakref.WeakValueDictionary[str, "TStringVar"]
	if TYPE_CHECKING else
	weakref.WeakValueDictionary
)() 


class TStringVar(tk.StringVar):
	def __init__(self, value: str, *, master: tk.Widget = None):
		self._value = value
		self._cb_name = ""
		if isinstance(value, DelayedLocalization):
			value, name = str(value), value.args[0]
			n, i = name, 2
			while name in string_vars:
				name = f"{n}#{i}"
				i += 1
		else:
			name = None
		super().__init__(master, value, name)
		string_vars[name] = self

	def __hash__(self):
		return hash(self._name)

	def __del__(self):
		if self._cb_name:
			self.trace_remove("write", self._cb_name)
		super().__del__()

	def set(self, value):
		self._value = value
		super().set(str(value))

	def update(self):
		# Should only be called when the language changes
		if isinstance(self._value, DelayedLocalization):
			super().set(str(self._value))

	def _on_update_handler(self, varname, idx, mode):
		if mode == "write":
			if self._as_text_kwarg:
				return self._fun(text=str(self._value))
			return self._fun(str(self._value))

	def on_update(self, fun, *, now=False, as_text_kwarg=False):
		self._fun = fun
		self._as_text_kwarg = as_text_kwarg
		if self._cb_name:
			self.trace_remove("write", self._cb_name)
		self._cb_name = self.trace_add("write", WeakMethod(self._on_update_handler))
		if now:
			fun(str(self._value))

def init(r: tk.Tk):
	global root
	root = r

def change_language(*langs: str):
	langs_used = []
	missing = set()
	for lang in langs:
		parts = lang.split("_")
		used_lang = lang
		while used_lang and used_lang not in available_languages:
			parts.pop()
			used_lang = "_".join(parts)
		if used_lang:
			if used_lang not in langs_used:
				langs_used.append(used_lang)
		else:
			missing.add(lang)

	if missing:
		missing = ", ".join(missing)
		raise ValueError(f"language(s) {missing} don't exist")

	config["general"]["language"] = ",".join(langs_used)
	for s in string_vars.values():
		s.update()

def localized_game_name(rom: ROM, fallback: str = ""):
	lookup = f"library.list.rom.{rom.acode}.{rom.internal}.{rom.crc32:08X}"
	
	value = fallback.format(rom=rom) if fallback else rom.internal
	ret = delayed_gettext(lookup, fallback=value)
	return ret

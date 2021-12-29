# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import gettext
import tkinter as tk
import weakref
from typing import TYPE_CHECKING

from .util import WeakMethod
from .. import locales
from ..config import config
from ..locales import _, available_languages, base, split_ietf_tag
from ..info.games import ROM


string_vars = (weakref.WeakSet["TStringVar"] if TYPE_CHECKING else weakref.WeakSet)()


class TStringVar(tk.StringVar):
	def __init__(self, value: str, *, master: tk.Widget = None):
		self._value = value
		self._cb_name = ""
		if isinstance(value, _):
			value, name = str(value), value.key
		else:
			name = None
		super().__init__(master, value, name)
		string_vars.add(self)

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
		if isinstance(self._value, _):
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
	s_langs = set(langs)
	diff = s_langs - available_languages
	if diff:
		missing = ", ".join(diff)
		raise ValueError(f"language(s) {missing} don't exist")

	locales.current_lang = gettext.translation(
		"pm2hw",
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

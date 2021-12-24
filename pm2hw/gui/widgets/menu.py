# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import tkinter as tk
from typing import Tuple
from tkinter import ttk
from functools import partial

from ..i18n import TStringVar

# TODO: ::tk::SetAmpText / ::tk::AmpMenuArgs

class Menu(tk.Menu):
	valid_button_cnf = {
		"accelerator", "activebackground", "activeforeground",
		"background", "bitmap", "columnbreak", "compound",
		"font", "foreground", "hidemargin", "image",
		"label", "selectimage", "state", "underline"
	}
	count = 0

	_themeable_config_options = (
		"activebackground", "activeborderwidth", "activeforeground",
		"background", "borderwidth", "cursor", "disabledforeground",
		"font", "foreground", "relief", "selectcolor",
	)

	_themeable_button_config_options = (
		"activebackground", "activeforeground",
		"background", "font", "foreground", "selectcolor"
	)

	def __init__(self, master=None, cnf: dict = {}, *, altkey = "_", style="Menu", **kw):
		self.altkey = altkey
		self.label_vars = []
		self._style = style

		cnf = cnf.copy()
		cnf.update(kw)
		bc = {
			k: v
			for k, v in cnf.items()
			if k in self.valid_button_cnf
		}
		for k in self.valid_button_cnf:
			cnf.pop(k, None)
		cnf.pop("menu", None)
		cnf.setdefault("tearoff", 0)

		super().__init__(master, cnf)
		if isinstance(master, tk.Tk):
			master.config(menu=self)
		elif isinstance(master, tk.Menu):
			master.add_cascade(menu=self, **bc)

		self.bind("<<ThemeChanged>>", self._update_styling)
		self._update_styling()

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		pass

	# Hook add to convert marker to Alt navigation
	def add(self, itemType, cnf: dict, *, label: str = "", **kw):
		cfg = self._button_config.copy()
		if itemType == "separator":
			self.count += 1
			return super().add(itemType, {})
		elif itemType not in {"checkbutton", "radiobutton"}:
			cfg.pop("selectcolor", None)

		if not label and "label" in cnf:
			cnf = cnf.copy()
			label = cnf.pop("label")
		insert = kw if kw or not cnf else cnf
		var = TStringVar(label, master=self)
		var.index = self.count
		self.count += 1
		var.args = (itemType, cnf, kw)
		var.on_update(partial(self._updater, var))  # TODO: might be a problem if menus are destroyed
		insert["label"], insert["underline"] = self._get_underline(var.get())
		super().add(itemType, cnf, **kw, **cfg)

	def replace(self, index, itemType, cnf: dict, *, label: str = "", **kw):
		insert = kw if kw or not cnf else cnf
		insert["label"], insert["underline"] = self._get_underline(label)
		self.delete(index)
		super().insert(index, itemType, cnf, **kw)

	def _get_underline(self, label: str) -> Tuple[str, int]:
		idx = label.find(self.altkey)
		if idx >= 0:
			label = label[:idx] + label[idx+1:]
		return label, idx

	def _updater(self, var: TStringVar, value):
		#self.delete(var.index)
		it, cnf, kw = var.args
		self.replace(var.index, it, cnf, label=value, **kw, **self._button_config)

	def _update_styling(self, e: tk.Event = None):
		s = ttk.Style()
		config = {
			k: v
			for k, v in zip(
				self._themeable_config_options,
				map(
					lambda x: s.configure(self._style, x),
					self._themeable_config_options
				)
			)
			if v
		}
		self.configure(config)

		end = self.index(tk.END)

		self._button_config = {
			k: v
			for k, v in zip(
				self._themeable_button_config_options,
				map(
					lambda x: s.configure(f"{self._style}.entry", x) or config.get(x),
					self._themeable_button_config_options
				)
			)
			if v
		}
		cfg = self._button_config.copy()
		cfg.pop("selectcolor", None)

		if end is not None:
			for i in range(end):
				try:
					self.entryconfigure(i, **self._button_config)
				except tk.TclError:
					self.entryconfigure(i, **cfg)

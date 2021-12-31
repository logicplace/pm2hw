# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import tkinter as tk
from time import sleep
from typing import Tuple
from tkinter import ttk
from functools import partial
from threading import Lock

# TODO: ::tk::SetAmpText / ::tk::AmpMenuArgs

class Menu(tk.Menu):
	valid_button_cnf = {
		"accelerator", "activebackground", "activeforeground",
		"background", "bitmap", "columnbreak", "compound",
		"font", "foreground", "hidemargin", "image",
		"label", "labelvar", "selectimage", "state", "underline"
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
		self._style = style
		self.replacing = Lock()
		self.label_vars = {}

		opts = tk._cnfmerge((cnf, kw))
		bc = {
			k: v
			for k, v in opts.items()
			if k in self.valid_button_cnf
		}
		for k in self.valid_button_cnf:
			opts.pop(k, None)
		opts.pop("menu", None)
		opts.setdefault("tearoff", 0)

		super().__init__(master, opts)
		if isinstance(master, tk.Tk):
			master.config(menu=self)
			master.menu = self
		elif isinstance(master, tk.Menu):
			if isinstance(master, Menu):
				self.replacing = master.replacing
			elif "labelvar" in bc:
				bc["label"] = str(bc.pop("labelvar").get())
			master.add_cascade(menu=self, **bc)

		self.bind("<<ThemeChanged>>", self._update_styling)
		self._update_styling()

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		return False

	# Hook add to convert marker to Alt navigation
	def add(self, itemType, cnf: dict, **kw):
		cfg = self._button_config.copy()
		if itemType == "separator":
			self.count += 1
			return super().add(itemType, {})
		elif itemType not in {"checkbutton", "radiobutton"}:
			cfg.pop("selectcolor", None)

		opts = tk._cnfmerge((cnf, kw))
		if "labelvar" in opts:
			var: tk.StringVar = opts.pop("labelvar")
			var.index = self.count
			var.args = (itemType, opts)
			# TODO: might be a problem if menus are destroyed
			var.trace_add("write", partial(self._updater, var))
			self.label_vars[self.count] = var  # TODO: insufficient for dynamic menus
		self.count += 1
		opts["label"], opts["underline"] = self._get_underline(var.get())
		super().add(itemType, **opts, **cfg)

	def replace(self, index, itemType, cnf: dict, *, label: str = "", **kw):
		opts = tk._cnfmerge((cnf, kw))
		opts["label"], opts["underline"] = self._get_underline(label)
		with self.replacing:
			self.delete(index)
			sleep(0.005)
			super().insert(index, itemType, **opts)
			sleep(0.005)

	def _get_underline(self, label: str) -> Tuple[str, int]:
		idx = label.find(self.altkey)
		if idx >= 0:
			label = label[:idx] + label[idx+1:]
			return label, idx
		return label, None

	def _updater(self, var: tk.StringVar, *args):
		it, opts = var.args
		self.replace(var.index, it, opts, label=var.get())

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

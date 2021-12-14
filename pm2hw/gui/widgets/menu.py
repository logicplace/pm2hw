import tkinter as tk
from typing import Tuple

from ..i18n import TStringVar

# TODO: ::tk::SetAmpText / ::tk::AmpMenuArgs

class Menu(tk.Menu):
	valid_button_cnf = {
		"accelerator", "activebackground", "activeforeground",
		"background", "bitmap", "columnbreak", "compound",
		"font", "foreground", "hidemargin", "image",
		"label", "state", "underline"
	}
	count = 0

	def __init__(self, master=None, cnf: dict = {}, *, altkey = "_", **kw):
		self.altkey = altkey
		self.label_vars = []

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

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		pass

	# Hook add to convert marker to Alt navigation
	def add(self, itemType, cnf: dict, *, label: str = "", **kw):
		if itemType == "separator":
			return super().add(itemType, cnf, **kw)
		if not label and "label" in cnf:
			cnf = cnf.copy()
			label = cnf.pop("label")
		insert = kw if kw or not cnf else cnf
		var = TStringVar(label, master=self)
		var.index = self.count
		var.args = (itemType, cnf, kw)
		self._add_trace(var)
		insert["label"], insert["underline"] = self._get_underline(var.get())
		super().add(itemType, cnf, **kw)

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

	def _add_trace(self, var: TStringVar):
		def updater(varname, idx, mode):
			if mode == "write":
				self.delete(var.index)
				it, cnf, kw = var.args
				self.replace(var.index, it, cnf, label=var.get(), **kw)

		var.trace_add("write", updater)

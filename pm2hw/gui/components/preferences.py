import tkinter as tk
from tkinter import ttk, simpledialog
from typing import List

from ..i18n import TStringVar
from ..util import WeakMethod
from ..themes import themes, select_theme
from ...config import config, save as save_config
from ...locales import _, available_languages
from pm2hw.gui import i18n

class PreferencesDialog(simpledialog.Dialog):
	def body(self, master: tk.Frame):
		frm = ttk.Frame(master)
		frm.grid(column=0, row=0, sticky=tk.NSEW)

		var = TStringVar(_("preferences.language.title"))
		lg_frm = ttk.LabelFrame(frm, text=var.get())
		var.on_update(WeakMethod(lg_frm.configure), as_text_kwarg=True)
		for i, (label, fn) in enumerate([
			(_("preferences.language.interface"), self.add_language_selector),
			(_("preferences.language.release"), self.add_release_selector),
		]):
			var = TStringVar(label)
			lbl = ttk.Label(lg_frm, textvariable=var)
			lbl.var = var
			lbl.grid(column=0, row=i, sticky=tk.NW)
			fn(lg_frm).grid(column=1, row=i, sticky=tk.NW)

		theme_frm = ttk.Frame(frm)
		var = TStringVar(_("preferences.theme.title"))
		lbl = ttk.Label(theme_frm, textvariable=var)
		lbl.var = var

		theme = self.initial_theme = ttk.Style().theme_use()
		ts = self.theme_select = ttk.Combobox(theme_frm, values=list(themes.keys()))
		ts.set(theme)
		ts.bind("<<ComboboxSelected>>", self.update_theme)
		
		lbl.pack(side=tk.LEFT)
		ts.pack(side=tk.LEFT)

		lg_frm.pack(side=tk.TOP, expand=True, fill=tk.X)
		theme_frm.pack(side=tk.TOP, expand=True, fill=tk.X)

	def add_language_selector(self, parent: ttk.LabelFrame):
		top = OrderedList(parent, rows=2)
		lgs = self.initial_lgs = config.getstrlist("general", "language")
		active, inactive = top.rows()
		self.active_lgs = active
		for x in lgs:
			active.add(text=x)

		for x in available_languages - set(lgs):
			inactive.add(text=x)

		active.bind("<<OrderChanged>>", self.update_language)

		top.update_buttons()
		return top

	def add_release_selector(self, parent: ttk.LabelFrame):
		top = OrderedList(parent)
		row = top.rows()[0]
		self.initial_releases = config.get("general", "box-languages")

		added = set()
		for x in config.getstrlist("general", "box-languages"):
			if x not in added:
				row.add(text=x)
				added.add(x)

		row.bind("<<OrderChanged>>", self.update_release_order)
		top.update_buttons()
		return top

	def update_language(self, event: tk.Event):
		lgs = list(event.widget.values())
		if lgs:
			i18n.change_language(*lgs)

	def update_release_order(self, event: tk.Event):
		box_languages = ", ".join(event.widget.values())
		config["general"]["box-languages"] = box_languages

	def update_theme(self, event: tk.Event):
		select_theme(self.theme_select.get())

	def validate(self):
		return bool(self.active_lgs.items())

	def apply(self):
		save_config()

	def cancel(self, event=None):
		i18n.change_language(*self.initial_lgs)
		config["general"]["box-languages"] = self.initial_releases
		select_theme(self.initial_theme)
		super().cancel(event)


class OrderedList(ttk.Frame):
	def __init__(self, master, *, rows=1, **kw):
		super().__init__(master, style="OrderedList.TFrame", **kw)

		for i in range(rows):
			row = OrderedListRow(self, index=i)
			row.pack(side=tk.TOP, expand=True, fill=tk.X)
		self.n_rows = i + 1

	def update_buttons(self):
		for row in self.rows():
			row.update_buttons()

	def rows(self) -> List["OrderedListRow"]:
		return self.pack_slaves()

	def values(self):
		for row in self.rows():
			yield row.values()


class OrderedListRow(ttk.Frame):
	def __init__(self, master, *, index, **kw):
		super().__init__(master, style="OrderedListRow.TFrame", **kw)
		self.index = index

	def is_first(self):
		return self.index == 0

	def is_last(self):
		return self.index == self.master.n_rows - 1

	def add(self, index=-1, **kw):
		pack_kw = {}
		if index != -1:
			test = self.pack_slaves()[index:]
			if test:
				pack_kw["before"] = test[0]
				for child in test:
					child.index += 1
		else:
			index = len(self.pack_slaves())

		child = OrderedListItem(self, index=index, **kw)
		child.pack(side=tk.LEFT, **pack_kw)
		return child

	def reindex(self):
		self.update()
		for i, child in enumerate(self.items()):
			child.index = i
			child.update_buttons()

	def update_buttons(self):
		for child in self.items():
			child.update_buttons()

	def items(self) -> List["OrderedListItem"]:
		return self.pack_slaves()

	def values(self):
		for item in self.items():
			yield item.kw["text"]


class OrderedListItem(ttk.Frame):
	def __init__(self, master, *, index, **kw):
		self.kw = kw.copy()
		label_kw = {
			k: kw.pop(k)
			for k in ["text", "textvariable"]
			if k in kw
		}
		super().__init__(master, style="OrderedListItem.TFrame", padding=2, **kw)
		self.index = index

		label = self.label = ttk.Label(
			self,
			style="OrderedListItem.TLabel",
			takefocus=True,
			**label_kw
		)
		label.grid(column=1, row=1)
		self.rowconfigure(1, weight=1)
		self.columnconfigure(1, weight=1)

		# Make four-way buttons
		def button(key, text, command):
			label.bind(key, command)
			return ttk.Button(
				self,
				text=text,
				command=command,
				style="OrderedListItem.TButton",
				takefocus=False,
			)

		self.up = button("<Up>", "⏶", self.move_up)
		self.down = button("<Down>", "⏷", self.move_down)
		self.left = button("<Left>", "⏴", self.move_left)
		self.right = button("<Right>", "⏵", self.move_right)

	def is_first(self):
		return self.index == 0

	def is_last(self):
		return self.index == len(self.master.items()) - 1

	def update_buttons(self):
		row: OrderedListRow = self.master
		show_up = not row.is_first()
		show_down = not row.is_last()
		show_left = not self.is_first()
		show_right = not self.is_last()

		if show_left:
			self.left.grid(column=0, row=1, sticky="nws")
		else:
			self.left.grid_forget()
		if show_right:
			self.right.grid(column=2, row=1, sticky="nes")
		else:
			self.right.grid_forget()

		left = 0 if show_left else 1
		span = 1 + int(show_left) + int(show_right)
		if show_up:
			self.up.grid(column=left, row=0, columnspan=span, sticky="wne")
		else:
			self.up.grid_forget()
		if show_down:
			self.down.grid(column=left, row=2, columnspan=span, sticky="wse")
		else:
			self.down.grid_forget()

	def move_up(self, event=None):
		row: OrderedListRow = self.master
		top: OrderedList = row.master
		rows = top.rows()

		# Have to remake
		if not row.is_first():
			new_row: OrderedListRow = rows[row.index-1]
			new_row.add(**self.kw).update_buttons()
			self.destroy()
			row.reindex()
			new_row.update_buttons()
			row.event_generate("<<OrderChanged>>")
			new_row.event_generate("<<OrderChanged>>")

	def move_down(self, event=None):
		row: OrderedListRow = self.master
		top: OrderedList = row.master
		rows = top.rows()

		# Have to remake
		if not row.is_last():
			new_row: OrderedListRow = rows[row.index+1]
			new_row.add(**self.kw)
			self.destroy()
			row.reindex()
			new_row.update_buttons()
			row.event_generate("<<OrderChanged>>")
			new_row.event_generate("<<OrderChanged>>")

	def move_left(self, event=None):
		if self.index > 0:
			self.index -= 1
			row: OrderedListRow = self.master
			before: OrderedListItem = row.items()[self.index]
			self.pack(side=tk.LEFT, before=before)
			before.index += 1
			before.update_buttons()
			self.update_buttons()
			row.event_generate("<<OrderChanged>>")

	def move_right(self, event=None):
		if self.index < len(self.master.children) - 1:
			self.index += 1
			row: OrderedListRow = self.master
			after: OrderedListItem = row.items()[self.index]
			self.pack(side=tk.LEFT, after=after)
			after.index -= 1
			after.update_buttons()
			self.update_buttons()
			row.event_generate("<<OrderChanged>>")

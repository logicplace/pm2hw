# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import glob
import weakref
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, cast
from threading import Lock

import tkinter as tk
from tkinter import ttk, font, filedialog

from ..i18n import _, TStringVar
from ..util import WeakMethod, filetypes_min
from ...info import games
from ...config import config
from ...logger import warn
from ...locales import natural_size

from ..resources import graphic

def item_updater(library: "Library", iid: str):
	library = weakref.ref(library)

	def handler(value: str):
		library().tree.item(iid, text=value)

	return handler

class Entry:
	iid: str  # set by Library
	name: str
	title: str

	icon: Optional[str] = None
	preview: Optional[str] = None

	num_buttons = 0

	# Sort of internal stuff
	pi_icon: Optional[tk.PhotoImage] = None
	pi_preview: Optional[tk.PhotoImage] = None
	parent_iid: str

	def __init__(self, parent: "Library"):
		self._parent = weakref.ref(parent)
		self.lock = Lock()

	@property
	def parent(self):
		return self._parent()

	def render_to(self, target: ttk.Frame):
		raise NotImplementedError

	def cleanup(self):
		pass


class Library(ttk.Frame):
	vars: Dict[str, TStringVar]
	entries: Dict[str, Entry]
	library_name: ClassVar[str]
	library_class: ClassVar[type]

	def __init__(self, master, *, theight=None, disabled=False, **kw):
		super().__init__(master, **kw)
		self.frames = weakref.WeakValueDictionary()
		self.vars = {}
		self.entries = {}
		self.disabled = disabled

		tkw = {} if theight is None else {"height": theight}
		self.tree = ttk.Treeview(self,
			#columns=("Name",),
			show="tree",
			selectmode="extended",
			takefocus=True,
			**tkw
		)

		f = font.nametofont("LibraryListEntryFont")
		self.tree.tag_configure("LibraryListEntryFont", font=f)
		f = font.nametofont("LibraryListCategoryFont")
		self.tree.tag_configure("LibraryListCategoryFont", font=f)

		scroll_x = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
		scroll_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
		self.tree.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)

		tree_actions = ttk.Frame(self)
		ai = self.action_images = [
			tk.PhotoImage(
				master=tree_actions,
				file=graphic("remove_file.gif")
			),
			tk.PhotoImage(
				master=tree_actions,
				file=graphic("add_file.gif")
			),
			tk.PhotoImage(
				master=tree_actions,
				file=graphic("add_folder.gif")
			),
		]
		for (name, cmd), im in zip([
			("remove", self.remove_entry),
			("add-file", self.add_file),
			("add-folder", self.add_folder)
		], ai):
			kw = {} if disabled else {"command": cmd}
			btn = ttk.Button(tree_actions, image=im, **kw)
			btn.pack(side=tk.RIGHT)
			self.frames[name] = btn

		self.tree.grid(column=0, row=0, sticky=tk.NSEW)
		scroll_y.grid(column=1, row=0, sticky="nes")
		tree_actions.grid(column=0, row=1, sticky=tk.NSEW)
		scroll_x.grid(column=0, row=2, sticky="esw")
		self.columnconfigure(0, weight=1)
		self.rowconfigure(0, weight=1)

		if not disabled:
			self.tree.bind("<<TreeviewSelect>>", self.on_select)

	def __del__(self):
		self.cleanup()

	def cleanup(self):
		for k in list(self.entries.keys()):
			self.entries[k].cleanup()
		self.vars.clear()

	def destroy(self):
		super().destroy()
		self.cleanup()

	def make(self, text: str, *, tags="LibraryListEntryFont", parent="", **kw):
		var = TStringVar(text)
		iid = self.tree.insert(parent, "end", text=var.get(), tags=tags, **kw)
		var.on_update(item_updater(self, iid))
		self.vars[iid] = var
		return iid

	def add(self, entry: Entry):
		kw = {}
		if entry.icon:
			kw["image"] = entry.pi_icon = tk.PhotoImage(
				master=self,
				file=graphic(entry.icon)
			)
		elif entry.pi_icon:
			kw["image"] = entry.pi_icon
		giid = self.make(entry.name, parent=entry.parent_iid, **kw)
		self.entries[giid] = entry
		entry.iid = giid
		self.tree.item(entry.parent_iid, open=True)

	def add_folder(self):
		lafd = config["GUI"].get("last-added-folder-dir")
		kw = {"initialdir": lafd} if lafd else {}
		folder = filedialog.askdirectory(mustexist=True, title=_("library.list.add.folder"), **kw)
		if folder:
			config["GUI"]["last-added-folder-dir"] = os.path.dirname(folder)
			for fn in glob.glob(os.path.join(folder, "**", "*.min"), recursive=True):
				self.add(self.library_class(self, fn), _commit=False)

	def add_file(self):
		lafd = config["GUI"].get("last-added-file-dir")
		kw = {"initialdir": lafd} if lafd else {}
		files = filedialog.askopenfilenames(filetypes=filetypes_min(), title=_("library.list.add.file"), **kw)
		if files:
			config["GUI"]["last-added-file-dir"] = os.path.dirname(files[0])
			for fn in files:
				self.add(self.library_class(self, fn))

	def remove_entry(self, *entries: Entry):
		selection = [e.iid for e in entries] if entries else self.tree.selection()
		if selection:
			config_entries = cast(List[str], config["GUI"].getlines(self.library_name, []))
			changed = False
			for iid in selection:
				entry = self.entries.get(iid)
				if entry is not None:
					self.tree.delete(iid)
					del self.vars[iid], self.entries[iid]
					if isinstance(entry, self.library_class):
						try:
							config_entries.remove(entry.filename)
							changed = True
						except ValueError:
							warn("Couldn't find {fn} while removing entry from {list} list",
								fn=entry.filename, list=self.library_name)
			if changed:
				config["GUI"][self.library_name] = "\n".join(config_entries)
				self.update_preview()

	def on_select(self, e: tk.Event):
		pass

	def update_preview(self):
		pass

	def update_entry(self, entry: Entry):
		self.vars[entry.iid].set(str(entry.name))


class BaseRomEntry(Entry):
	def render_to(self, target: ttk.Frame):
		target.frames = weakref.WeakValueDictionary()
		title_var = TStringVar(self.title)
		lbl = ttk.Label(target,
			textvariable=title_var,
			font=font.nametofont("GameInfoTitleFont")
		)
		lbl.title_var = title_var
		lbl.pack()
		target.frames["title"] = lbl

		if self.preview:
			lbl = ttk.Label(target)
			lbl["image"] = self.pi_preview = tk.PhotoImage(
				master=lbl,
				file=graphic(self.preview)
			)
			lbl.pack()
			target.frames["preview"] = lbl
		
		self.render_buttons_to(target)
		self.render_details_to(target)

	def render_buttons_to(self, target: ttk.Frame):
		frm = ttk.Frame(target)
		frm.columnconfigure(0, weight=1)
		frm.pack()
		target.frames["buttons"] = frm
		return frm

	def add_button(self, frm: ttk.Frame, text: str, command=None, disabled=False):
		kw = {"command": command} if command is not None else {}
		if disabled:
			kw["state"] = tk.DISABLED
		var = TStringVar(text)
		btn = ttk.Button(frm, textvariable=var, **kw)
		btn.grid(column=0, row=self.num_buttons, sticky=tk.NSEW)
		btn._text_var = var
		self.num_buttons += 1
		return btn

	def render_details_to(self, target: ttk.Frame):
		pass

	def render_rom_details(self, target: ttk.Frame, info: games.ROM):
		var = TStringVar(_("info.rom.details.header"))
		frame = DetailPane(target, textvariable=var)

		def lhs(name):
			return (_)(name, key=f"info.rom.details.{name}")

		def rhs(value, pfx):
			if isinstance(value, Enum):
				return (_)(value.value, key=f"{pfx}.{value.name}")
			return (_)(value, key=f"{pfx}.{value}")

		if info.game:
			if info.game.developer:
				frame.add(lhs("developer"), rhs(info.game.developer, "game.developer"))
			if info.game.genre:
				frame.add(lhs("genre"), rhs(info.game.genre, "game.genre"))
		if info.size:
			frame.add(lhs("size"), natural_size(info.size, "bits"))
		if info.modes:
			frame.add(lhs("players"), "{}~{}".format(*info.players))
			# TODO: collapsible detailed play mode info
		if info.features:
			# TODO: localized lists
			frame.add(lhs("features"), ", ".join(
				rhs(x, "info.rom.details.features")
				for x in info.features
			))
		if info.save_slots:
			frame.add(lhs("save slots"), str(info.save_slots))
		for version in info.versions:
			frame.add(lhs(version.of), version.number)
		if info.crc32 >= 0:
			frame.add(lhs("crc32"), f"{info.crc32:08x}")
		frame.pack()
		target.frames["details"] = frame


class DetailPane(ttk.LabelFrame):
	current_row = 0

	def __init__(self, *args, textvariable=None, **kw):
		if textvariable is not None:
			textvariable.on_update(WeakMethod(self.configure), as_text_kwarg=True)
			kw["text"] = textvariable.get()
		elif "text" in kw:
			kw["text"] = str(kw["text"])
		super().__init__(*args, **kw)
		self.columnconfigure(1, weight=1)

	def add(self, name: str, value: Any):
		name_label = ttk.Label(self, style="Header.TLabel", text=str(name) + ":")
		value_label = ttk.Label(self, text=str(value))

		name_label.grid(column=0, row=self.current_row, sticky=tk.NSEW)
		value_label.grid(column=1, row=self.current_row, sticky=tk.NSEW)
		self.current_row += 1

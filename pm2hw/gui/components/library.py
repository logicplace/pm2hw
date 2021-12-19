import os
import glob
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, cast
from threading import Lock

import tkinter as tk
from tkinter import ttk, font, filedialog

from pm2hw_icons import graphic
from ..i18n import _, TStringVar
from ..util import filetypes_min
from ...info import games
from ...config import config
from ...logger import warn
from ...locales import natural_size

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
		self.parent = parent
		self.lock = Lock()

	def render_to(self, target: ttk.Frame):
		raise NotImplementedError

	def cleanup(self):
		pass


class Library(ttk.Frame):
	vars: Dict[str, TStringVar]
	entries: Dict[str, Entry]
	library_name: ClassVar[str]
	library_class: ClassVar[type]

	def __init__(self, master, **kw):
		super().__init__(master, **kw)
		self.vars = {}
		self.entries = {}

		self.tree = ttk.Treeview(self,
			#columns=("Name",),
			show="tree",
			selectmode="extended",
			takefocus=True,
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
		ttk.Button(tree_actions, command=self.remove_entry, image=ai[0]).pack(side=tk.RIGHT)
		ttk.Button(tree_actions, command=self.add_file, image=ai[1]).pack(side=tk.RIGHT)
		ttk.Button(tree_actions, command=self.add_folder, image=ai[2]).pack(side=tk.RIGHT)

		self.tree.grid(column=0, row=0, sticky=tk.NSEW)
		scroll_y.grid(column=1, row=0, sticky="nes")
		tree_actions.grid(column=0, row=1, sticky=tk.NSEW)
		scroll_x.grid(column=0, row=2, sticky="esw")
		self.columnconfigure(0, weight=1)
		self.rowconfigure(0, weight=1)

		self.tree.bind("<<TreeviewSelect>>", self.on_select)

	def make(self, text: str, *, tags="LibraryListEntryFont", parent="", **kw):
		var = TStringVar(text)
		iid = self.tree.insert(parent, "end", text=var.get(), tags=tags, **kw)
		var.on_update(lambda v: self.tree.item(iid, text=v))
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
		files = filedialog.askopenfilenames(filetypes=filetypes_min, title=_("library.list.add.file"), **kw)
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
		ttk.Label(target,
			textvariable=TStringVar(self.title),
			font=font.nametofont("GameInfoTitleFont")
		).pack()
		if self.preview:
			lbl = ttk.Label(target)
			lbl["image"] = self.pi_preview = tk.PhotoImage(
				master=lbl,
				file=graphic(self.preview)
			)
			lbl.pack()
		
		self.render_buttons_to(target)
		self.render_details_to(target)

	def render_buttons_to(self, target: ttk.Frame):
		frm = ttk.Frame(target)
		frm.columnconfigure(0, weight=1)
		frm.pack()
		return frm

	def add_button(self, frm: ttk.Frame, text: str, command=None, disabled=False):
		kw = {"command": command} if command is not None else {}
		if disabled:
			kw["state"] = tk.DISABLED
		btn = ttk.Button(frm, textvariable=TStringVar(text), **kw)
		btn.grid(column=0, row=self.num_buttons, sticky=tk.NSEW)
		self.num_buttons += 1
		return btn

	def render_details_to(self, target: ttk.Frame):
		pass

	def render_rom_details(self, target: ttk.Frame, info: games.ROM):
		frame = DetailPane(target, text=_("info.rom.details.header"))

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


class DetailPane(ttk.LabelFrame):
	current_row = 0

	def __init__(self, *args, **kw):
		if "text" in kw:
			# TODO: variable
			kw["text"] = str(kw["text"])
		super().__init__(*args, **kw)
		self.columnconfigure(1, weight=1)

	def add(self, name: str, value: Any):
		name_label = ttk.Label(self, style="Header.TLabel", text=str(name) + ":")
		value_label = ttk.Label(self, text=str(value))

		name_label.grid(column=0, row=self.current_row, sticky=tk.NSEW)
		value_label.grid(column=1, row=self.current_row, sticky=tk.NSEW)
		self.current_row += 1

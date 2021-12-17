from typing import List, Optional, cast
from functools import partial

import tkinter as tk
from tkinter import ttk

from pm2hw_icons import graphic
from ..i18n import _, localized_game_name
from .linker import Linker
from .library import Entry, Library, BaseRomEntry
from ...info import games
from ...config import config

class ROM(BaseRomEntry):
	def __init__(self, parent: "GameList", fn: str):
		super().__init__(parent)
		self.filename = fn
		with open(fn, "rb") as f:
			self.info = games.lookup(f, True)

		# TODO: name updates on lang change
		self.name = str(localized_game_name(self.info, fallback=_("library.list.rom.name.unknown")))
		self.title = str(localized_game_name(self.info, fallback=_("info.rom.name.unknown")))

		# TODO: select by preferences
		if self.info.boxings:
			self.icon = self.info.boxings[0].icon
			self.preview = self.info.boxings[0].preview

	def render_buttons_to(self, target: ttk.Frame):
		frm = super().render_buttons_to(target)
		for x in self.parent.entries.values():
			if isinstance(x, Linker):
				if x.flashing:
					msg = _("info.button.flash.in-progress")
					disabled = True
				else:
					msg = (
						_("info.button.flash.card").format(name=x.flashable.name)
						if x.connected else
						_("info.button.flash.linker").format(name=x.linker.name)
					)
					disabled = x.reading
				self.add_button(frm, msg, partial(self.flash_to, x), disabled=disabled)
		return frm
			
	def render_details_to(self, target: ttk.Frame):
		if self.info is not None:
			self.render_rom_details(target, self.info)

	def flash_to(self, linker: Linker):
		linker.do_flash(self.filename)


# TODO: Multicarts


class GameList(Library):
	library_name = "library-games"
	library_class = ROM

	def __init__(self, master, info_view: ttk.Frame, **kw):
		super().__init__(master, **kw)
		self.info_view = info_view
		self.updating_info = False  # thread safety

		self.iids = {
			Linker: self.make(_("library.list.header.linkers"), tags="GameListCategoryFont"),
			ROM: self.make(_("library.list.header.games"), tags="GameListCategoryFont"),
		}
		self._no_linkers_message = ""

		self.unknown_game_icon = tk.PhotoImage(
			master=self,
			file=graphic("unknown_game_icon.gif")
		)

	def reload(self):
		""" Reload library from config file. """
		for iid, entry in list(self.entries.items()):
			if isinstance(entry, ROM):
				self.tree.delete(iid)
				del self.vars[iid], self.entries[iid]

		games = cast(List[str], config["GUI"].getlines("library-games", []))
		config["GUI"]["library-games"] = ""
		for game in games:
			self.add(ROM(self, game))

	def add(self, entry: Entry):
		for c, iid in self.iids.items():
			if isinstance(entry, c):
				if c is ROM:
					# Ensure this file isn't already added
					for game in self.entries.values():
						if isinstance(game, ROM):
							if entry.filename == game.filename:
								return
					config["GUI"].setdefault("library-games", "") 
					config["GUI"]["library-games"] += f"\n{entry.filename}"

					if not entry.icon:
						entry.pi_icon = self.unknown_game_icon
				elif c is Linker:
					if self._no_linkers_message:
						self.tree.delete(self._no_linkers_message)
						self._no_linkers_message = ""
				entry.parent_iid = iid
				super().add(entry)
				return
		raise ValueError("entry")
	
	def add_no_linkers_message(self):
		if not self._no_linkers_message:
			self._no_linkers_message = self.make(_("library.list.no-linkers"), parent=self.iids[Linker])
			self.tree.item(self.iids[Linker], open=True)

	def add_rom(self, filename: str):
		self.add(ROM(self, filename))

	def on_select(self, e: tk.Event):
		self.update_preview()

	def update_preview(self):
		if self.updating_info:
			return
		self.updating_info = True

		for x in list(self.info_view.children.values()):
			x.destroy()

		selected = []
		iids = set(self.iids.values())
		if self._no_linkers_message:
			iids.add(self._no_linkers_message)
		for item in self.tree.selection():
			if item in iids:
				self.tree.selection_remove(item)
			else:
				selected.append(item)
		if selected:
			if len(selected) == 1:
				game = self.entries[selected[0]]
				game.render_to(self.info_view)
			elif len(selected) > 1:
				# TODO: multicart
				pass

		self.updating_info = False

# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
from io import BytesIO
from typing import TYPE_CHECKING, Optional

from tkinter import ttk, filedialog

from pm2hw.locales import natural_size

from .status import prepare_progress, set_status
from .library import BaseRomEntry
from ..i18n import _, localized_game_name
from ..util import filetypes_min, threaded
from ... import get_connected_linkers
from ...base import BaseFlashable
from ...info import games
from ...logger import error, exception, log, verbose
from ...linkers import BaseLinker
from ...exceptions import DeviceError, DeviceNotSupportedError

if TYPE_CHECKING:
	from .gamelist import GameList


class Linker(BaseRomEntry):
	def __init__(self, parent: "GameList", linker: BaseLinker):
		super().__init__(parent)
		self.linker = linker
		self.flashable: Optional[BaseFlashable] = None
		self.connected = False
		self.data = BytesIO()
		self.info: Optional[games.ROM] = None
		
		# Action statuses
		self.reading = False
		self.dumping = False
		self.flashing = False
		self.erasing = False

	def cleanup(self):
		self.linker.cleanup()

	@property
	def name(self):
		if self.info:
			return _("library.list.linker.name.with-rom").format(
				game=localized_game_name(self.info),
				name=self.flashable.name
			)
		elif not self.connected:
			return _("library.list.linker.name.unconnected").format(name=self.linker.name)
		return _("library.list.linker.name.no-rom").format(name=self.flashable.name)

	@property
	def title(self):
		if self.flashable is not None:
			return self.flashable.name
		return ""

	def ensure_connected(self):
		# TODO: check for disconnections
		if not self.connected:
			verbose(_("log.connect.in-progress"), linker=self.linker)
			try:
				self.flashable = self.linker.init()
			except DeviceNotSupportedError as err:
				error(str(err))
				set_status("log.connect.failed")
				return
			except DeviceError as err:
				exception(str(err), err)
				set_status("log.connect.failed")
				return
			try:
				size = self.flashable.memory
				log(_("log.connect.complete.with-size"),
					name=self.flashable.name, size=natural_size(size))
			except AttributeError:
				log(_("log.connect.complete"), name=self.flashable.name)
			self.info = games.lookup(self.flashable)
			self.connected = True
			self.parent.update_entry(self)

	def render_to(self, target: ttk.Frame):
		self.ensure_connected()
		if self.flashable:
			super().render_to(target)
		# TODO: render error screen, not just log

	def render_buttons_to(self, target: ttk.Frame):
		disabled = self.parent.disabled
		def dcmd(cmd):
			if disabled:
				return ()
			return (cmd,)

		frm = super().render_buttons_to(target)
		if self.reading:
			self.add_button(frm, _("info.button.read.in-progress"), disabled=True)
		elif not (self.dumping or self.flashing or self.data.seek(0, os.SEEK_END)) and self.info:
			self.add_button(frm, _("info.button.read"), *dcmd(self.read_to_memory))
		if self.dumping:
			self.add_button(frm, _("info.button.dump.in-progress"), disabled=True)
		else:
			self.add_button(frm, _("info.button.dump"), *dcmd(self.dump), disabled=self.flashing or self.erasing)
		if self.flashable.can_flash:
			if self.flashing:
				self.add_button(frm, _("info.button.flash.in-progress"), disabled=True)
			else:
				self.add_button(frm, _("info.button.flash"), *dcmd(self.flash), disabled=self.reading)
		if self.flashable.can_erase:
			if self.erasing:
				self.add_button(frm, _("info.button.erase.in-progress"), disabled=True)
			else:
				self.add_button(frm, _("info.button.erase"), *dcmd(self.erase), disabled=self.reading)
		return frm
			
	def render_details_to(self, target: ttk.Frame):
		# TODO: render linker and card info
		if self.connected and self.info:
			self.render_rom_details(target, self.info)

	@threaded
	def read_to_memory(self, bypass=False):
		# TODO: disable buttons, switch to throbber, whatever
		if not bypass:
			self.lock.acquire()
			self.reading = True
			self.parent.update_preview()
			prepare_progress(self.flashable, "reading")
		else:
			self.reading = True

		self.data.seek(0)
		# TODO: status updates
		self.flashable.dump(self.data)
		self.data.truncate()
		self.info = games.lookup(self.data, check_crc=True)

		self.reading = False
		self.parent.update_preview()
		self.parent.update_entry(self)
		if not bypass:
			self.lock.release()


	@threaded
	def dump(self):
		# Get location to dump to
		out = filedialog.asksaveasfile(
			mode="wb",
			defaultextension=".min",
			filetypes=filetypes_min(),
			# TODO: initialdir
			title=_("select-location.linker.dump")
		)

		if out is not None:
			# TODO: disable buttons, switch to throbber, whatever
			self.lock.acquire()
			self.dumping = True
			self.parent.update_preview()

			# Check if it's already been read into memory
			# TODO: status updates
			if self.data.seek(0, os.SEEK_END):
				self.data.seek(0)
				out.write(self.data.read())
			else:
				prepare_progress(self.flashable, "dumping")
				self.read_to_memory(bypass=True)
				self.data.seek(0)
				out.write(self.data.read())
			out.close()

			self.dumping = False
			self.lock.release()

			# Add to library
			self.parent.add_rom(out.name)

	@threaded
	def flash(self):
		if not self.flashable.can_flash:
			set_status(_("status.flash.unsupported").format(name=self.flashable.name))
			return

		fn = filedialog.askopenfilename(
			defaultextension=".min",
			filetypes=filetypes_min(),
			# TODO: initialdir
			title=_("select-location.linker.flash")
		)

		if fn is not None:
			self.do_flash(fn)

	@threaded
	def do_flash(self, fn: str):
		self.ensure_connected()
		self.lock.acquire()
		self.flashing = True
		self.parent.update_preview()
		prepare_progress(self.flashable, "erasing", "flashing")

		with open(fn, "rb") as f:
			self.data.seek(0)
			self.data.write(f.read())
			self.data.truncate()

		self.data.seek(0)
		self.info = games.lookup(self.data, check_crc=True)
		self.data.seek(0)
		self.flashable.flash(self.data)

		self.flashing = False
		self.parent.update_preview()
		self.parent.update_entry(self)
		self.lock.release()

	@threaded
	def erase(self):
		if not self.linker.can_erase:
			set_status(_("status.erase.unsupported").format(name=self.flashable.name))
			return

		self.lock.acquire()
		self.erasing = True
		self.parent.update_preview()
		prepare_progress(self.flashable, "erasing")

		self.flashable.erase()
		self.data.seek(0)
		self.data.truncate()
		self.info = None

		self.erasing = False
		self.parent.update_preview()
		self.parent.update_entry(self)
		self.lock.release()


class PokeFlash(Linker):
	icon = "pokecard_icon.gif"
	preview = "pokecard512-210_preview.gif"


class DittoFlash(Linker):
	icon = "ditto_icon.gif"
	preview = "ditto_preview.gif"

	def render_buttons_to(self, target: ttk.Frame):
		frm = super().render_buttons_to(target)
		# TODO: don't add command if parent is disabled
		self.add_button(frm, _("info.button.eeprom"))


label2entry_cls = {
	"PokeFlash": PokeFlash,
	"DITTO mini Flasher": DittoFlash,
}


def refresh_linkers(game_list: "GameList"):
	try:
		linkers = {(l.name, l.serial): l for l in get_connected_linkers()}
	except DeviceError:
		return
	entries = {
		(e.linker.name, e.linker.serial): e
		for e in game_list.entries.values()
		if isinstance(e, Linker)
	}

	# Delete removed linkers
	for k in list(entries.keys()):
		if k not in linkers:
			entry = entries.pop(k)
			log(_("log.linker.removed"), linker=entry.linker)
			game_list.remove_entry(entry)

	# Update existing ones & add new ones
	for k, linker in linkers.items():
		if k in entries:
			game_list.update_entry(entries[k])
		else:
			cls = label2entry_cls[linker.name]
			e = entries[k] = cls(game_list, linker)
			game_list.add(e)
			log(_("log.linker.found"), linker=linker)

	# If there are no entries, add a message
	if not entries:
		game_list.add_no_linkers_message()

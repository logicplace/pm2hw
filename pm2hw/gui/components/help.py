# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import tkinter as tk
from sys import version
from typing import Dict, Union
from urllib.parse import urlparse
from tkinter import ttk, messagebox, simpledialog
from tkinter.font import Font

from .linker import DittoFlash
from .status import _make_status
from .gamelist import GameList, ROM
from ..widgets import RichText, ScrollFrame
from ..i18n import _
from ... import __version__ as main_version
from ...linkers import BaseLinker

try:
	from pm2hw_icons import __version__ as icons_version
except ImportError:
	icons_version = _("help.plugin.not-installed")

def open_about(root: tk.Tk):
	messagebox.showinfo(
		str(_("help.about.title")), 
		str(_("help.about.message").format(
		authors="Sapphire Becker",
		license="Mozilla Public License, version 2.0",
		version=main_version,
		icons_version=icons_version,
		py_version=version,
		tcl_version=tk.TclVersion,
		tk_version=tk.TkVersion,
		tk_windowing=root._windowingsystem,
	)))


class DummyLinker(BaseLinker):
	name = "DITTO mini Flasher"

	def __init__(self):
		...

	def __del__(self):
		...

	def init(self):
		return self

	def seek(self, *args):
		...

	def read(self, size: int):
		return b"\xff" * size

class DummyROM(ROM):
	def get_info(self, code, name, crc):
		from ...info import games

		for info in games.games_by_rom.get((code, name), []):
			if info.crc32 == crc:
				return info
		return games.ROM(games.Status.unidentified, code, name, crc)

class HelpDialog(simpledialog.Dialog):
	def body(self, master: tk.Frame):
		self.topics: Dict[str, RichText] = {}
		self.html_handlers = {
			"a": self.link_handler,
			"str": self.translation_handler,
			"widget": self.widget_handler,
		}

		master.pack_configure(fill=tk.BOTH, expand=True)
		self.window = ttk.PanedWindow(master, orient=tk.HORIZONTAL)
		self.window.pack(fill=tk.BOTH, expand=True)
		

		self.tree = ttk.Treeview(self.window,
			show="tree",
			selectmode="browse",
			takefocus=True,
		)
		self.text = RichText(self.window, state="readonly", style_tags=RichText.markdown_tags)

		self.window.add(self.tree)
		self.window.add(self.text.top, weight=1)

		self.tree.bind("<<TreeviewSelect>>", self.show_topic)

		for topic, parent in [
			("welcome", ""),
			("basics", ""),
			("gui", "basics"),
			("linker", "gui"),
			("game", "gui"),
			("flashing", "basics"),
			("dumping", "basics"),
			("reference", ""),
		]:
			self.add_topic(
				topic,
				(_)(f"help.topic.{topic}.title"),
				(_)(f"help.topic.{topic}.content"),
				parent=parent
			)

		self.show_topic("welcome")

	def buttonbox(self):
		# Disable buttons
		pass

	def add_topic(self, iid, name, content, *, parent="", index=tk.END):
		iid = self.tree.insert(parent, index, iid, text=str(name), open=True)
		hparent = self.topics.get(parent, self)
		ret = self.topics[iid] = HelpTopic(hparent, iid, name, content)
		return ret

	def show_topic(self, topic: Union[str, tk.Event] = ""):
		if isinstance(topic, str) and topic:
			self.tree.selection_set(topic)
			return
		sel = self.tree.selection()
		if not sel:
			return
		topic = sel[0]
		self.text.clear()
		self.topics[topic].render_to(self.text)

	def link_handler(self, renderer, attrs):
		if "href" in attrs and "$end" in attrs:
			# Not a block element, requested from renderer.link
			parsed = urlparse(attrs["href"])
			if parsed.scheme:
				handler = attrs["href"]
			else:
				def handler():
					if parsed.path:
						self.show_topic(parsed.path)
					if parsed.fragment:
						res = self.text.tag_nextrange("anchor-" + parsed.fragment, "1.0")
						if res:
							self.text.see(res[0])

			start, end = renderer.index, attrs["$end"]
			renderer.target.hyperlink_add(handler, start, end)
			renderer.index = end
			return start, end

		return renderer.noop

	def translation_handler(self, renderer, attrs):
		if "name" in attrs:
			s = str((_)(attrs["name"]))
			if "del" in attrs:
				s = s.replace(attrs["del"], "")
			return renderer.text(s)
		return renderer.noop

	def widget_handler(self, renderer, attrs):
		name = attrs.get("name")
		if name == "gui-overview":
			frm = ttk.Frame(self.text)
			frm.columnconfigure(1, weight=1)
			frm.rowconfigure(1, weight=1)
			menu = tk.Frame(frm)
			for x in ["main", "view", "help"]:
				mb = tk.Menubutton(
					menu,
					text=str((_)(f"window.menu.{x}")).replace("_", ""),
					state=tk.DISABLED
				)
				mb.pack(side=tk.LEFT)
			menu.configure(background=mb.cget("background"))
			menu.grid(column=1, row=0, columnspan=2, stick=tk.NSEW)

			info = ScrollFrame(frm, width=200, height=200, orient=tk.VERTICAL)
			info.grid(column=2, row=1, sticky=tk.NSEW)

			game_list = GameList(frm, info, width=300, height=200, theight=4, disabled=True)
			game_list.add(DittoFlash(game_list, DummyLinker()))
			rom = DummyROM(game_list, b"MRCJ", "ﾎﾟｹﾓﾝﾚｰｽ", 0x4433B736)
			game_list.add(rom)
			rom.render_to(info)
			game_list.grid(column=1, row=1, sticky=tk.NSEW)

			status = _make_status(frm)
			status.grid(column=1, row=2, columnspan=2, stick=tk.NSEW)

			# Draw numbers
			def place_under_gl_button(lbl, name):
				btn: ttk.Button = game_list.frames[name]
				x = btn.winfo_rootx() - frm.winfo_rootx() + btn.winfo_width() / 2 - num_width / 2
				y = btn.winfo_rooty() - frm.winfo_rooty() + btn.winfo_height() + 3
				lbl.place(x=x, y=y)
				#lbl.lift()

			left_frm = ttk.Frame(frm)
			lbl = ttk.Label(left_frm, text="①", style="HelpNumber.TLabel")
			lbl.pack()

			# Size the left column
			left_frm.grid(column=0, row=0, rowspan=3, sticky=tk.NSEW)
			ret = renderer.widget(frm)
			num_width = lbl.winfo_width()
			num_height = lbl.winfo_height()

			# Continue drawing numbers
			lbl = ttk.Label(left_frm, text="②", style="HelpNumber.TLabel")
			lbl.pack()
			lbl = ttk.Label(left_frm, text="➂", style="HelpNumber.TLabel")
			# TODO: use start of game folder in tree list
			y = game_list.winfo_rooty() - frm.winfo_rooty() + 75
			lbl.place(x=0, y=y)
			lbl = ttk.Label(frm, text="④", style="HelpNumber.TLabel")
			place_under_gl_button(lbl, "add-folder")
			lbl = ttk.Label(frm, text="⑤", style="HelpNumber.TLabel")
			place_under_gl_button(lbl, "add-file")
			lbl = ttk.Label(frm, text="⑥", style="HelpNumber.TLabel")
			place_under_gl_button(lbl, "remove")
			lbl = ttk.Label(info, text="⑦", style="HelpNumber.TLabel")
			lbl.place(x=5, y=35)
			lbl = ttk.Label(left_frm, text="⑧", style="HelpNumber.TLabel")
			y = status.winfo_rooty() - frm.winfo_rooty() + status.winfo_height() - num_height
			lbl.place(x=0, y=y)
			return ret
		elif name == "gui-linker":
			frm = ttk.Frame(self.text)
			frm.columnconfigure(0, weight=1)
			right_frm = ttk.Frame(frm)
			game_list = GameList(right_frm, right_frm, width=0, height=0, theight=0, disabled=True)
			linker = DittoFlash(game_list, DummyLinker())
			game_list.add(linker)
			linker.render_to(right_frm)
			right_frm.grid(column=1, row=0, sticky=tk.NSEW)

			# Draw numbers
			def place_at_height_of(lbl, name):
				w: ttk.Widget = right_frm.frames[name]
				y = w.winfo_rooty() - frm.winfo_rooty() + w.winfo_height() / 2 - num_height / 2
				lbl.place(x=0, y=y)

			left_frm = ttk.Frame(frm)
			lbl = ttk.Label(left_frm, text="①", style="HelpNumber.TLabel")
			lbl.pack()

			# Size the left column
			left_frm.grid(column=0, row=0, sticky=tk.NSEW)
			ret = renderer.widget(frm)
			num_height = lbl.winfo_height()

			# Continue drawing numbers
			lbl = ttk.Label(left_frm, text="②", style="HelpNumber.TLabel")
			place_at_height_of(lbl, "preview")
			lbl = ttk.Label(left_frm, text="➂", style="HelpNumber.TLabel")
			place_at_height_of(lbl, "buttons")
			# lbl = ttk.Label(left_frm, text="④", style="HelpNumber.TLabel")
			# place_at_height_of(lbl, "details")
			return ret
		elif name == "gui-game":
			frm = ttk.Frame(self.text)
			frm.columnconfigure(0, weight=1)
			right_frm = ttk.Frame(frm)
			game_list = GameList(right_frm, right_frm, width=0, height=0, theight=0, disabled=True)
			game_list.add(DittoFlash(game_list, DummyLinker()))
			rom = DummyROM(game_list, b"MRCJ", "ﾎﾟｹﾓﾝﾚｰｽ", 0x4433B736)
			rom.render_to(right_frm)
			right_frm.grid(column=1, row=0, sticky=tk.NSEW)

			# Draw numbers
			def place_at_height_of(lbl, name):
				w: ttk.Widget = right_frm.frames[name]
				y = w.winfo_rooty() - frm.winfo_rooty() + w.winfo_height() / 2 - num_height / 2
				lbl.place(x=0, y=y)

			left_frm = ttk.Frame(frm)
			lbl = ttk.Label(left_frm, text="①", style="HelpNumber.TLabel")
			lbl.pack()

			# Size the left column
			left_frm.grid(column=0, row=0, sticky=tk.NSEW)
			ret = renderer.widget(frm)
			num_height = lbl.winfo_height()

			# Continue drawing numbers
			lbl = ttk.Label(left_frm, text="②", style="HelpNumber.TLabel")
			place_at_height_of(lbl, "preview")
			lbl = ttk.Label(left_frm, text="➂", style="HelpNumber.TLabel")
			place_at_height_of(lbl, "buttons")
			lbl = ttk.Label(left_frm, text="④", style="HelpNumber.TLabel")
			place_at_height_of(lbl, "details")
			return ret
		else:
			raise ValueError("widget name")


class HelpTopic:
	def __init__(self, parent, iid: str, name: str, content: str):
		self.parent = parent
		self.html_handlers = parent.html_handlers
		self.iid = iid
		self.name = name
		self.content = content

	def add_topic(self, *args, **kw):
		if "parent" not in kw:
			kw["parent"] = self.iid
		return self.parent.add_topic(self.iid, *args, **kw)

	def render_to(self, parent: RichText):
		parent.insert_markdown(tk.END, str(self.content), html_handlers=self.html_handlers)

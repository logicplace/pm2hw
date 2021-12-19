from sys import version
from urllib.parse import urlparse

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, Union

import pm2hw_icons
from .linker import DittoFlash
from .status import _make_status
from .gamelist import GameList, ROM
from ..widgets import RichText, ScrollFrame
from ..i18n import _
from ...linkers import BaseLinker

def open_about(root: tk.Tk):
	messagebox.showinfo(
		str(_("help.about.title")), 
		str(_("help.about.message").format(
		authors="Sapphire Becker",
		license="Mozilla Public License, version 2.0",
		version="0.0.1",
		icons_version=pm2hw_icons.version,
		py_version=version,
		tcl_version=tk.TclVersion,
		tk_version=tk.TkVersion,
		tk_windowing=root._windowingsystem,
	)))


class DummyLinker(BaseLinker):
	name = "DITTO mini Flasher"

	def __init__(self):
		...

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
				_(f"help.topic.{topic}.title"),
				_(f"help.topic.{topic}.content"),
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
		if "href" not in attrs:
			return renderer.noop

		parsed = urlparse(attrs["href"])
		if parsed.scheme:
			return attrs["href"]

		def handler():
			if parsed.path:
				self.show_topic(parsed.path)
			if parsed.fragment:
				self.text.see("anchor-" + parsed.fragment)

		# TODO: clean this up later
		return handler

	def translation_handler(self, renderer, attrs):
		if "name" in attrs:
			return renderer.text(str((_)(attrs["name"])))
		return renderer.noop

	def widget_handler(self, renderer, attrs):
		name = attrs.get("name")
		if name == "gui-overview":
			frm = ttk.Frame(self.text)
			frm.columnconfigure(0, weight=1)
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
			menu.grid(column=0, row=0, columnspan=2, stick=tk.NSEW)

			info = ttk.Frame(frm, width=200, height=200)#, orient=tk.VERTICAL)
			info.grid(column=1, row=1, sticky=tk.NSEW)

			game_list = GameList(frm, info, width=300, height=200, theight=4, disabled=True)
			# game_list.add(DittoFlash(game_list, DummyLinker()))
			# rom = DummyROM(game_list, b"MRCJ", "ﾎﾟｹﾓﾝﾚｰｽ", 0x4433B736)
			# game_list.add(rom)
			# rom.render_to(info)
			game_list.grid(column=0, row=1, sticky=tk.NSEW)

			status = _make_status(frm)
			status.grid(column=0, row=2, columnspan=2, stick=tk.NSEW)

			# TODO: draw numbers
			return renderer.widget(frm)
		elif name == "gui-linker":
			return renderer.noop
		elif name == "gui-game":
			return renderer.noop
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

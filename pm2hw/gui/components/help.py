from sys import version
from urllib.parse import urlparse

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, Union

import pm2hw_icons
from ..widgets.richtext import RichText
from ..i18n import _

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


class HelpDialog(simpledialog.Dialog):
	def body(self, master: tk.Frame):
		self.topics: Dict[str, RichText] = {}
		self.html_handlers = {
			"a": self.link_handler,
			"str": self.translation_handler,
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
		self.window.add(self.text.frame, weight=1)

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
		self.text.delete("1.0", tk.END)
		self.topics[topic].render_to(self.text)

	def link_handler(self, renderer, attrs):
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
			return renderer.text(str(_(attrs["name"])))
		return renderer.noop


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

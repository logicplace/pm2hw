# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
import json
import tkinter as tk
import webbrowser
from tkinter import ttk
from functools import partial

try:
	from mistune.renderers import BaseRenderer
except ImportError:
	BaseRenderer = object

class RichText(tk.Text):
	_themeable_config_options = (
		"background", "borderwidth", "cursor", "font",
		"foreground", "highlightbackground",
		"highlightcolor", "highlightthickness",
		"inactiveselectbackground",
		"insertbackground", "insertborderwidth",
		"insertwidth", "padx", "pady", "relief",
		"selectbackground", "selectborderwidth",
		"selectforeground", "spacing1", "spacing2", "spacing3",
		"tabs", "tabstyle", "wrap",
	)

	_themeable_tag_config_options = (
		"background", "bgstipple", "borderwidth", "fgstipple",
		"font", "foreground", "justify", "lmargin1", "lmargin2",
		"offset", "overstrike", "relief", "rmargin", "spacing1",
		"spacing2", "spacing3", "tabs", "underline", "wrap",
	)

	markdown_tags = (
		"p", "em", "strong", "em+strong", "del", "ins", "u",
		"h1", "h2", "h3", "h4", "h5", "h6", "h7",
		"kbd", "tt", "code", "a", "a:normal",
		"a:hover", "a:active", "a:visited",
		"ol", "ul", "li", "ol.listmark", "ul.listmark",
		"widget",
	)

	def __init__(self, master=None, cnf={}, *, style="RichText", style_tags=(), orient=(), **kw):
		self.top = ttk.Frame(master, style=f"{style}.TFrame")
		self._state = kw.get("state")
		if self._state == "readonly":
			kw.pop("state")
		super().__init__(self.top, cnf, **kw)
		self.grid(column=0, row=0, sticky=tk.NSEW)

		self._orig = self._w + "_orig"
		self._readonly = False
		self._insertwidth = 2
		if self._state == "readonly":
			self._set_readonly()

		cmd = {}
		orient = {orient} if isinstance(orient, str) else set(orient)
		scroll_x = ttk.Scrollbar(
			self.top,
			orient=tk.HORIZONTAL,
			command=self.xview,
			style=f"{style}.Horizontal.TScrollbar"
		)
		cmd["xscrollcommand"] = scroll_x.set
		scroll_y = ttk.Scrollbar(
			self.top,
			orient=tk.VERTICAL,
			command=self.yview,
			style=f"{style}.Vertical.TScrollbar"
		)
		cmd["yscrollcommand"] = scroll_y.set
		if tk.HORIZONTAL in orient:
			scroll_x.grid(column=0, row=1, sticky="sew")
		if tk.VERTICAL in orient:
			scroll_y.grid(column=1, row=0, sticky="nse")
		self.configure(**cmd)
		self.top.rowconfigure(0, weight=1)
		self.top.columnconfigure(0, weight=1)

		self._style = style
		self._style_tags = style_tags
		self.bind("<<ThemeChanged>>", self._update_styling)
		self._update_styling()

		self._currently_hovering_over_link = ""
		self.tag_bind("a:normal", "<Enter>", self._hyperlink_enter)
		self.tag_bind("a:normal", "<Leave>", self._hyperlink_leave)
		self.tag_bind("a:normal", "<Button-1>", self._hyperlink_click)

		# For debugging tags
		# self.bind_all("<Button-1>", lambda e: print(self.tag_names(tk.CURRENT)))

		self.links = {}
		self.grid = self.top.grid
		self.pack = self.top.pack
		self.place = self.top.place

	def configure(self, cnf=None, **kw):
		set_readonly = False
		if "state" in kw:
			self._state = kw.get("state")
			set_readonly = self._state == "readonly"
			if set_readonly:
				kw["state"] = "normal"
		super().configure(cnf, **kw)
		if set_readonly:
			self._set_readonly()

	config = configure

	def _set_readonly(self):
		if not self._readonly:
			self._insertwidth = self.cget("insertwidth")
			self.tk.call("rename", self._w, self._orig)
			self.tk.createcommand(self._w, self._dispatch)
			self.configure(insertwidth=0)
			self._readonly = True
			return True
		return False

	def _unset_readonly(self):
		if self._readonly:
			self.tk.deletecommand(self._w)
			self.tk.call("rename", self._orig, self._w)
			self.configure(insertwidth=self._insertwidth)
			self._readonly = False
			return True
		return False

	def _dispatch(self, operation, *args):
		# Called from tcl for operations on this widget, to shim readonly
		# This is only enabled in readonly mode, so we don't need to check for it
		if operation in {"insert", "delete"}:
			return "break"
		return self.tk.call((self._orig, operation) + args)

	def _update_styling(self, e: tk.Event = None):
		s = ttk.Style()
		config = {
			k: v
			for k, v in zip(
				self._themeable_config_options,
				map(
					partial(s.configure, self._style),
					self._themeable_config_options)
				)
			if v
		}
		self.configure(config)

		for tag in self._style_tags:
			style = f"{tag}.{self._style}"
			config = {
				k: v
				for k, v in zip(
					self._themeable_tag_config_options,
					map(
						partial(s.configure, style),
						self._themeable_tag_config_options)
					)
				if v
			}
			self.tag_config(tag, config)

		self.update_idletasks()

	def insert(self, index, chars, *args) -> None:
		if self._readonly:
			self.tk.call((self._orig, "insert", index, chars) + args)
		else:
			super().insert(index, chars, *args)

	def delete(self, index1, index2=None) -> None:
		if self._readonly:
			self.tk.call(self._orig, "delete", index1, index2)
		else:
			super().delete(index1, index2)

	def clear(self):
		if self.cget("state") != "disabled":
			if self.children:
				for child in list(self.children.values()):
					child.destroy()
			self.delete("1.0", tk.END)

	def _get_hyperlink_deets(self, href_or_callable):
		link_id = f"a-{len(self.links)}"
		tags = ["a:normal", link_id]
		if isinstance(href_or_callable, str):
			handler = partial(webbrowser.open_new_tab, href_or_callable)
			tags.append(f"a-href-{hash(href_or_callable)}")
		elif callable(href_or_callable):
			handler = href_or_callable
		else:
			raise TypeError("href_or_callable")
		return link_id, handler, tags

	def insert_hyperlink(self, index, chars, href_or_callable, *tags):
		link_id, handler, ltags = self._get_hyperlink_deets(href_or_callable)
		self.insert(index, chars, *ltags, *tags)
		self.links[link_id] = handler

	def hyperlink_add(self, href_or_callable, index1, index2 = None):
		link_id, handler, tags = self._get_hyperlink_deets(href_or_callable)
		for tag in tags:
			self.tag_add(tag, index1, index2)
		self.links[link_id] = handler

	def insert_markdown(self, index, markdown, *tags, html_handlers):
		import mistune
		mistune.markdown(markdown, renderer=RichTextRenderer(self, index, html_handlers, tags))

	def _get_hyperlink(self, index=tk.CURRENT):
		names = dict(t.rsplit("-", 1) for t in self.tag_names(index) if t.startswith("a-"))
		if not names:
			return "", -1, -1, ""
		link_id = "a-" + names.pop("a")
		href = names.pop("a-href", "")
		href_tag = f"a-href-{href}" if href else ""
		start, end = self.tag_ranges(link_id)

		return link_id, start, end, href_tag

	def _hyperlink_enter(self, ev: tk.Event):
		link_id, start, end, _ = self._get_hyperlink()
		if not link_id:
			return
		self._currently_hovering_over_link = start
		self.tag_add("a:hover", start, end)
		self.tag_raise("a:hover")
		self.configure(cursor="hand2")

	def _hyperlink_leave(self, ev: tk.Event):
		if not self._currently_hovering_over_link:
			return
		ok, start, end, _ = self._get_hyperlink(self._currently_hovering_over_link)
		if not ok:
			return
		self.tag_remove("a:hover", start, end)
		self.tag_remove("a:active", start, end)
		self.configure(cursor="")

	def _hyperlink_click(self, ev: tk.Event):
		link_id, start, end, href_tag = self._get_hyperlink()
		if not link_id:
			return
		self.tag_add("a:active", start, end)
		self.tag_add("a:visited", start, end)
		if href_tag:
			ranges = self.tag_ranges(href_tag)
			for s, e in zip(ranges[::2], ranges[1::2]):
				self.tag_add("a:visited", s, e)
		self.tag_raise("a:visited")
		self.tag_raise("a:active")

		self.links[link_id]()

		def inactivate():
			if link_id in self.tag_names(start):
				self.tag_remove("a:active", start, end)

		self.after(1000, inactivate)


class RichTextRenderer(BaseRenderer):
	attr_parser = re.compile(r"(\w+)=(?:(['\"])(.*?)\2|(\S+))")

	list_types = {
		"": "• ",
		"disc": "• ",
		"circle": "◦ ",
		"square": "▪ ",
		"decimal": ("{}. ", "0123456789"),
		"lower-alpha": ("{}. ", "abcdefghijklmnopqrstuvwxyz", "repeat_0"),
	}

	def __init__(self, target: RichText, index, html_handlers, tags = []):
		super().__init__()
		self.target = target
		self.index = self.target.index(index)
		if self.index == "2.0" and self.target.index("2.0 - 1 chars") == "1.0":
			self.index = "1.0"
		self.html_handlers = html_handlers
		self.tags = list(tags)
		self.open_tags = []

	def _tag(self, children, *tags, combine=""):
		if isinstance(children, tuple):
			children = [children]  # why
		start, end = children[0][0], children[-1][1]
		for tag in tags:
			self.target.tag_add(tag, start, end)
			if combine:
				combined = "+".join(sorted((combine, tag)))
				self._combine_with(children, combine, combined)
		return start, end

	def _combine_with(self, children, child_tag, combined_tag):
		for s, e in children:
			if child_tag in self.target.tag_names(s):
				self.target.tag_add(combined_tag, s, e)
		self.target.tag_raise(combined_tag)

	@staticmethod
	def _bulletter(bullet):
		def handler(i):
			return bullet
		return handler

	@staticmethod
	def _numberer(format, seq, *opts):
		opts = set(opts)
		len_seq = len(seq)
		repeat_0 = "repeat_0" in opts

		def handler(i):
			digits = []
			digit = i % len_seq
			while i > len_seq:
				digits.append(seq[digit])
				i //= len_seq
				digit = i % len_seq - 1 if repeat_0 else i % len_seq
			digits.append(seq[digit])
			return format.format("".join(map(str, reversed(digits))))

		return handler

	@property
	def noop(self):
		return self.index, self.index

	def widget(self, window):
		start = self.index
		self.target.window_create(start, window=window)
		end = self.index = self.target.index(f"{start} + 1c")
		self.target.tag_add("widget", start, end)
		return start, self.text("\n")[1]

	# BaseRenderer methods
	def text(self, text, *tags):
		start = self.index
		self.target.insert(start, text, *tags)
		end = self.index = self.target.index(f"{start} + {len(text)} chars")
		return start, end

	def link(self, link, children=None, title=None):
		if isinstance(children, tuple):
			children = [children]  # why
		self.index, end = children[0][0], children[-1][1]
		return self.html_handlers["a"](self, {"href": link, "$end": end})

	def emphasis(self, children):
		return self._tag(children, "em", combine="strong")

	def strong(self, children):
		return self._tag(children, "strong", combine="em")

	def codespan(self, text):
		return self.text(f"\t{text}\t", "tt")

	def linebreak(self):
		return self.text("\n")

	def inline_html(self, html: str):
		cur = self.index
		if html.startswith("<") and html.endswith(">"):
			thtml = html[1:-1]
			if thtml.startswith("/"):
				if self.open_tags[-1][1] == thtml[1:]:
					start, *tags = self.open_tags.pop()
					for tag in tags:
						self.target.tag_add(tag, start, cur)
					return start, cur
			elif thtml.endswith("/"):
				return self.block_html(html)
			else:
				tag, *attrs = thtml.split(maxsplit=1)
				tags = [tag.lower()]
				if attrs:
					for mo in self.attr_parser.finditer(attrs[0]):
						name, _, v1, v2 = mo.groups()
						if name.lower() == "id":
							tags.append(f"anchor-{v1 or v2}")
							break
				self.open_tags.append((cur, *tags))
				return cur, None
		return cur, cur

	def paragraph(self, children):
		start, _ = self._tag(children, "p")
		_, end = self.text("\n")
		return start, end

	def heading(self, children, level):
		start, _ = self._tag(children, f"h{level}")
		_, end = self.text("\n")
		return start, end

	def newline(self):
		return self.noop

	def block_text(self, children):
		if isinstance(children, tuple):
			children = [children]  # haven't checked if necessary just assuming
		self.index = children[-1][1] + " lineend"
		_, end = self.text("\n")
		return children[0][0], end

	def block_code(self, text, info=None):
		start, _ = self.text(text, "code")
		_, end = self.text("\n")
		return start, end

	def block_html(self, text: str):
		if text.startswith("<") and text.endswith("/>"):
			tag, attr_str = text[1:-2].split(maxsplit=1)
			tag = tag.lower()
			if tag in self.html_handlers:
				attrs = {
					mo.group(1).lower(): mo.group(3) or mo.group(4)
					for mo in self.attr_parser.finditer(attr_str)
				}
				return self.html_handlers[tag](self, attrs)
		return self.noop

	def list(self, children, ordered, level, start=None):
		tag = "ol" if ordered else "ul"
		start_idx, end_idx = self._tag(children, tag)
		style = f"{tag}.{self.target._style}"
		s = ttk.Style()
		marker = json.loads(s.configure(style, "marker") or '""')
		if not isinstance(marker, str):
			marker = marker[(level - 1) % len(marker)]
		if isinstance(marker, str):
			if marker in self.list_types:
				marker = self.list_types[marker]
				if callable(marker):
					prefixer = marker
				elif isinstance(marker, str):
					prefixer = self._bulletter(marker)
				else:
					prefixer = self._numberer(*marker)
			else:
				prefixer = self._bulletter(marker)
		else:
			prefixer = self._numberer(*marker)

		i = start if isinstance(start, int) else 1
		tag_list_mark = f"{tag}.listmark"
		res = self.target.search("", start_idx, stopindex=end_idx)
		while res:
			m = prefixer(i)
			len_m = len(m)
			self.target.delete(res, f"{res} + 1c")
			self.target.insert(res, m, tag_list_mark)
			res = self.target.search("", f"{res} + {len_m}c", stopindex=end_idx)
			i += 1
		self.index = end_idx
		return start_idx, end_idx

	def list_item(self, children, level):
		start, end = self._tag(children, "li")
		self.target.insert(f"{start} linestart", ("\t" * level) + "")
		self.index = self.target.index(f"{end} lineend")
		return start, self.index

	# TODO: image, thematic_break, block_quote

	def finalize(self, children):
		start, end = self._tag(list(children), *self.tags, *self.open_tags)
		res = self.target.tag_nextrange("em", start, end)
		while res:
			s, em_end = res
			res = self.target.tag_nextrange("strong", s, em_end)
			while res:
				s, e = res
				self.target.tag_add("em+strong", s, e)
				res = self.target.tag_nextrange("strong", e, em_end)
			res = self.target.tag_nextrange("em", em_end, end)
		return start, end

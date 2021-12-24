# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import tkinter as tk
from tkinter import ttk
from functools import partial

# Addapted from https://gist.github.com/mp035/9f2027c3ef9172264532fcd6262f3b01
class ScrollFrame(ttk.Frame):
	def __init__(self, master=None, *, orient=None, **kw):
		ikw = {
			k[1:]: kw.pop(k)
			for k in ["iborder", "iborderwidth", "irelief", "ipadding", "istyle"]
			if k in kw
		}
		ckw = {
			k: kw[k]
			for k in ["width", "height"]
			if k in kw
		}
		ikw.update(ckw)

		if isinstance(orient, (tuple, list)):
			orient = set(orient)
		elif isinstance(orient, str):
			orient = {orient}
		elif not orient:
			orient = set()
		elif not isinstance(orient, set):
			raise ValueError("orient")
		self.has_horizontal = tk.HORIZONTAL in orient
		self.has_vertical = tk.VERTICAL in orient

		self.top = ttk.Frame(master, **kw)
		self.grid = self.top.grid
		self.pack = self.top.pack
		self.place = self.top.place

		self.canvas = tk.Canvas(self.top, **ckw)
		super().__init__(self.canvas, class_="ScrollFrame", **ikw)
		self.bind("<<ThemeChanged>>", self._update_styling)
		self._update_styling()

		# Scrollbars
		cmds = {}
		if self.has_horizontal:
			scroll_x = ttk.Scrollbar(self.top, orient=tk.HORIZONTAL, command=self.canvas.xview)
			scroll_x.grid(column=0, row=1, sticky="esw")
			cmds["xscrollcommand"] = scroll_x.set
		if self.has_vertical:
			scroll_y = ttk.Scrollbar(self.top, orient=tk.VERTICAL, command=self.canvas.yview)
			scroll_y.grid(column=1, row=0, sticky="nes")
			cmds["yscrollcommand"] = scroll_y.set
		self.canvas.configure(**cmds)

		self.canvas.grid(column=0, row=0, sticky=tk.NSEW)
		self.top.columnconfigure(0, weight=1)
		self.top.rowconfigure(0, weight=1)

		self.canvas_window = self.canvas.create_window(
			0, 0,
			window=self,
			anchor=tk.NW,
		)
		self.cget = partial(self.canvas.itemcget, self.canvas_window)
		self.config = self.configure = partial(self.canvas.itemconfigure, self.canvas_window)

		# Bind an event whenever the size of the frame changes.
		self.canvas.bind("<Configure>", self._on_canvas_configure)
		self.bind("<Configure>", self._on_frame_configure)

		self._on_frame_configure()

		if self.has_horizontal and self.has_vertical:
			self._children_bup = {}
			self.after(200, self._resize)

		if orient:
			self.top.bind("<Enter>", self._on_enter)
			self.top.bind("<Leave>", self._on_leave)

	def _update_styling(self, event=None):
		s = ttk.Style()
		bg = s.lookup("TFrame", "background")
		if not bg:
			bg = "#d9d9d9"
			s.configure("TFrame", background=bg)
		self.canvas.configure(background=bg, highlightbackground=bg)

	def _resize(self):
		# TODO: what the fuck event can I use to catch children being added
		# <Configure> doesn't work because the w/h is set so children don't resize
		# but unsetting them doesn't give any info on whether this is first call or not so
		if {k: id(v) for k, v in self._children_bup.items()} != {k: id(v) for k, v in self.children.items()}:
			self._children_bup = self.children.copy()
			w, h = self.winfo_reqwidth(), self.winfo_reqheight()
			cw, ch = self.canvas.winfo_width(), self.winfo_height()
			self.canvas.itemconfig(
				self.canvas_window,
				width=max(w, cw),
				height=max(h, ch)
			)
		self.after(200, self._resize)

	def _on_canvas_configure(self, event):
		# Reset the canvas window to encompass inner frame when required
		# TODO: optionally? hide scrollbar(s) if everything is visible
		conf = {}
		if self.has_vertical:
			conf["width"] = max(self.winfo_reqwidth(), event.width-4)
		if self.has_horizontal:
			conf["height"] = max(self.winfo_reqheight(), event.height-4)
		self.configure(**conf)

	def _on_frame_configure(self, event=None):
		# Reset the scroll region to encompass the inner frame
		self.canvas.configure(scrollregion=self.canvas.bbox("all"))

	def _on_enter_x11(self, fn, button, units):
		self.canvas.bind_all(button, lambda e: fn(units, "units"))

	def _on_enter_mousewheel(self, prefix="", divider=1):
		button = f"{prefix}-MouseWheel" if prefix else "MouseWheel"
		if self.has_vertical:
			self.canvas.bind_all(f"<{button}>",
				lambda e: self.canvas.yview_scroll(-int(e.delta / divider), "units"))
		if self.has_horizontal:
			self.canvas.bind_all(f"<Shift-{button}>",
				lambda e: self.canvas.xview_scroll(-int(e.delta / divider), "units"))

	def _on_enter(self, event):
		# https://core.tcl-lang.org/tk/artifact/991dedd4666462dd?ln=325,348
		if self._windowingsystem == "x11":
			if self.has_vertical:
				fn = self.canvas.yview_scroll
				self._on_enter_x11(fn, "<Button-4>", -5)
				self._on_enter_x11(fn, "<Button-5>", 5)
			if self.has_horizontal:
				fn = self.canvas.xview_scroll
				if not self.has_vertical:
					self._on_enter_x11(fn, "<Button-4>", -5)
					self._on_enter_x11(fn, "<Button-5>", 5)
				self._on_enter_x11(fn, "<Shift-Button-4>", -5)
				self._on_enter_x11(fn, "<Shift-Button-5>", 5)
		elif self._windowingsystem == "win32":
			self._on_enter_mousewheel(divider=120)
		elif self._windowingsystem == "aqua":
			self._on_enter_mousewheel()
			self._on_enter_mousewheel("Option", 0.1)

	def _on_leave(self, event):
		if self._windowingsystem == "x11":
			events = ["<Button-4>", "<Button-5>", "<Shift-Button-4>", "<Shift-Button-5>"]
		elif self._windowingsystem == "win32":
			events = ["<MouseWheel>", "<Shift-MouseWheel>"]
		elif self._windowingsystem == "aqua":
			events = ["<MouseWheel>", "<Shift-MouseWheel>", "<Option-MouseWheel>", "<Shift-Option-MouseWheel>"]
		else:
			return
		for name in events:
			self.canvas.unbind_all(name)

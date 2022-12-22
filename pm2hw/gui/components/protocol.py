# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import tkinter as tk
from tkinter import ttk
from typing import Dict, List

from pm2hw import logger
from pm2hw.gui.widgets import Dialog, RichText
from pm2hw.locales import natural_size

# TODO: localization

class DataFormatter(logger.Formatter):
	def __init__(self, unkfmt="", datefmt=None, *, in_fmt, out_fmt) -> None:
		super().__init__(unkfmt, datefmt)
		self._fmts = {
			"<": logger.Formatter(in_fmt, datefmt),
			">": logger.Formatter(out_fmt, datefmt)
		}

	def format(self, record: logger.LogRecord):
		# Assume all are PROTOCOL.DATA records
		record.dir, *record.bytes = record.msg.split(" ")
		record.msg = logger.SubtypedMessage("", "DATA")
		record.size = len(record.bytes)
		record.natsize = natural_size(record.size)
		formatter = self._fmts.get(record.dir, super())
		return formatter.format(record)


proto_formatter = logger.MonospacePrefixFormatter("[{asctime}] ")
data_formatter = DataFormatter(
	"[{asctime}] {dir} {natsize}",
	in_fmt="[{asctime}] Received {natsize}",
	out_fmt="[{asctime}] Sent {natsize}"
)

def filter_non_proto(record: logger.LogRecord):
	return record.levelno == logger.PROTOCOL

class ProtocolDialog(Dialog):
	record_index = 0
	records: Dict[str, logger.LogRecord]

	def body(self, master: tk.Frame):
		super().body(master)
		master.pack_configure(fill=tk.BOTH, expand=True)
		self.window = ttk.PanedWindow(master, orient=tk.HORIZONTAL)
		self.window.pack(fill=tk.BOTH, expand=True)
		
		frm = ttk.Frame(self.window)
		self.log_pane = ttk.Treeview(frm,
			show="tree",
			selectmode="browse",
			takefocus=True,
		)
		self.log_pane.bind("<<TreeviewSelect>>", self.show_info)

		scroll_x = ttk.Scrollbar(frm, orient=tk.HORIZONTAL, command=self.log_pane.xview)
		scroll_y = ttk.Scrollbar(frm, orient=tk.VERTICAL, command=self.log_pane.yview)
		self.log_pane.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)

		self.log_pane.grid(column=0, row=0, sticky=tk.NSEW)
		scroll_y.grid(column=1, row=0, sticky="nes")
		scroll_x.grid(column=0, row=1, sticky="esw")
		frm.columnconfigure(0, weight=1)
		frm.rowconfigure(0, weight=1)

		self.hex_pane = RichText(self.window,
			style="HexView.RichText",
			style_tags=["cell-even", "cell-odd", "header-even", "header-odd"],
			state="readonly",
			orient=tk.HORIZONTAL,
			spacing3=1,
		)

		self.window.add(frm, weight=3)
		self.window.add(self.hex_pane.top, weight=2)

		# Set up logger
		self.records = {}
		self.initial_level = logger.get_effective_level()
		logger.set_level(logger.PROTOCOL)

		proto_handler = logger.Handler(logger.PROTOCOL, raw_handler=self.add_proto_entry)
		proto_handler.add_filter(filter_non_proto)
		proto_handler.add_subtype_filter(logger.PROTOCOL, reject=["DATA"])
		logger.add_handler(proto_handler)

		data_handler = logger.Handler(logger.PROTOCOL, raw_handler=self.add_data_entry)
		data_handler.add_filter(filter_non_proto)
		data_handler.add_subtype_filter(logger.PROTOCOL, allow=["DATA"])
		logger.add_handler(data_handler)

		# logger.protocol("<", data=b"testing")
		# logger.protocol(">", data=b"0123456789abcdef" * 100)

	def _add_log_entry(self, record: logger.LogRecord, formatter: logger.Formatter, tag: str):
		iid = f"r{self.record_index}"
		self.log_pane.insert("", tk.END, iid, text=formatter.format(record), tags=tag)
		self.records[iid] = record
		self.record_index += 1

	def add_proto_entry(self, record: logger.LogRecord):
		self._add_log_entry(record, proto_formatter, "proto")

	def add_data_entry(self, record: logger.LogRecord):
		self._add_log_entry(record, data_formatter, "data")

	def show_info(self, *_):
		sel = self.log_pane.selection()
		if not sel:
			return
		record = self.records[sel[0]]
		data = getattr(record, "bytes", [])
		if data:
			self.display_bytes(record.bytes)
		else:
			# Non-data logs aren't selectable
			self.log_pane.selection_remove(sel)

	def display_bytes(self, b: List[str]):
		# List of two character strings, each being the hex of a byte
		hp = self.hex_pane
		hp.clear()

		size = len(b)
		width = len(f"{size:X}")
		if width % 2 != 0:
			width += 1

		hp.insert(tk.END, " " * width, "header-odd")
		for x in [
			"00", "01", "02", "03", "04", "05", "06", "07",
			"08", "09", "0A", "0B", "0C", "0D", "0E", "0F",
		][:size]:
			hp.insert(tk.END, "\u200b")
			hp.insert(tk.END, x, "header-odd")
		hp.insert(tk.END, "\n")

		for l, i in enumerate(range(0, size, 16)):
			eo = "odd" if l % 2 else "even"
			hp.insert(tk.END, f"{i:0{width}X}", f"header-{eo}")
			tag = f"cell-{eo}"
			for x in b[i:i+16]:
				hp.insert(tk.END, "\u200b")
				hp.insert(tk.END, x, tag)
			hp.insert(tk.END, "\n")

	def grab_set(self):
		# Prevent this window from preventing interaction with other windows
		pass

	def buttonbox(self):
		# Disable buttons
		pass

	def cancel(self, event=None):
		super().cancel(event)
		logger.set_level(self.initial_level)


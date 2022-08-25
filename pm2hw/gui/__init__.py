# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys
import tkinter as tk
import traceback
from tkinter import ttk
from functools import partial
from typing import  Dict, List, Tuple

from . import themes, resources
from .i18n import _, TStringVar
from .widgets import Menu, RichText, ScrollFrame
from .components import (
	add_progress, make_status, open_about, refresh_linkers, set_status,
	GameList, HelpDialog, PreferencesDialog
)
from .. import logger
from ..config import config, log_dir as error_log_dir


logger.view = "gui"


root = tk.Tk()

title_var = TStringVar(_("window.title"))
title_var.on_update(root.winfo_toplevel().title, now=True)

root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

themes.init(root, config["GUI"].get("theme", "base"))

pw1 = ttk.PanedWindow(root, orient=tk.VERTICAL)
pw2 = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
pw1.grid(column=0, row=0, sticky=tk.NSEW)

info = ScrollFrame(pw2, orient=tk.VERTICAL)
game_list = GameList(pw2, info)
game_list.reload()

pw2.add(game_list, weight=1)
pw2.add(info.top, weight=1)

log_pane = RichText(
	pw1, height=8, state="readonly", orient=tk.VERTICAL,
	style="Console.RichText", style_tags=("info", "warning", "error")
)

pw1.add(pw2, weight=1)

make_status(root).grid(column=0, row=2, sticky=tk.NSEW)

log_toggler = tk.BooleanVar(root)
log_pane_height = 0
def toggle_log_pane(varname, idx, mode):
	global log_pane_height
	if mode == "write":
		visible = log_pane.winfo_viewable()
		if log_toggler.get():
			if not visible:
				without_logs_height = pw1.cget("height")
				pw1.add(log_pane.top)
				if log_pane_height:
					pw1.configure(height=without_logs_height)
					pw1.after(30, lambda: pw1.sashpos(0, without_logs_height - log_pane_height))
		elif visible:
			pw1_sash_pos_with_logs = pw1.sashpos(0)
			log_pane_height = pw1.cget("height") - pw1_sash_pos_with_logs
			pw1.remove(log_pane.top)
log_toggler.trace_add("write", toggle_log_pane)

log_entries: List[logger.LogRecord] = []
progress_bars: Dict[logger.progress, Tuple[str, str]] = {}

def add_log_entry(record: logger.LogRecord):
	log_entries.append(record)
	insert_log_entry(record)
	# TODO: don't scroll if bar isn't at the end
	log_pane.see(tk.END)

def insert_log_entry(record: logger.LogRecord):
	msg = log_handler.format(record)
	tag = record.levelname.lower()
	if isinstance(record.msg, logger.progress):
		if record.msg in progress_bars:
			if record.msg.is_complete() or log_toggler.get():
				start, end = progress_bars[record.msg]
				log_pane.delete(start, end)
				log_pane.insert(start, f"\n{msg}", tag)
				end_line = int(start.split(".", 1)[0]) + len(msg.splitlines())
				progress_bars[record.msg] = (start, f"{end_line}.0")
			set_status()
		else:
			start = log_pane.index(tk.END)
			log_pane.insert(tk.END, f"\n{msg}", tag)
			end = log_pane.index(tk.END)
			progress_bars[record.msg] = (start, end)
			add_progress(record.msg)
	else:
		log_pane.insert(tk.END, f"\n{msg}", tag)

def update_log_entries(value):
	# Language changed
	logger.progress.config.load(value, force=True)
	pos, _ = log_pane.yview()
	log_pane.delete("1.0", tk.END)
	progress_bars.clear()
	for record in log_entries:
		insert_log_entry(record)
	log_pane.yview_moveto(pos)

progress_config = TStringVar(_("log.progress"))
progress_config.on_update(update_log_entries)

logger.set_level(logger.INFO)
log_handler = logger.Handler(logger.INFO, raw_handler=add_log_entry)
log_handler.set_formatter(logger.nice_formatter)
logger.add_handler(log_handler)

error_log_dn = os.path.join(error_log_dir, "error.log")
os.makedirs(error_log_dir, exist_ok=True)
def error_log_writer(s):
	with open(error_log_dn, "at", encoding="UTF-8") as f:
		f.write(s)
		f.write("\n")
error_handler = logger.Handler(logger.WARN, handler=error_log_writer)
logger.add_handler(error_handler)

def log_exception(self, exc, val, tb):
	stack_info = traceback.format_tb(tb)
	logger.exception(str(val), val, stack_info=stack_info)

tk.Tk.report_callback_exception = log_exception

# TODO: remember window settings in config

with Menu(root) as m:
	with Menu(m, labelvar=TStringVar(_("window.menu.main"))) as main:
		main.add_command(
			labelvar=TStringVar(_("window.menu.main.refresh")),
			command=partial(refresh_linkers, game_list)
		)
		main.add_command(
			labelvar=TStringVar(_("window.menu.main.preferences")),
			command=lambda: PreferencesDialog(
				root,
				title=str(_("window.preferences.title"))
			)
		)
		main.add_separator()
		main.add_command(
			labelvar=TStringVar(_("window.menu.main.exit")),
			command=root.destroy
		)

	with Menu(m, labelvar=TStringVar(_("window.menu.view"))) as view:
		# view.add_command(label=_("window.menu.view.multicart"))
		view.add_checkbutton(
			labelvar=TStringVar(_("window.menu.view.log")),
			variable=log_toggler
		)

	with Menu(m, labelvar=TStringVar(_("window.menu.help"))) as help:
		help.add_command(
			labelvar=TStringVar(_("window.menu.help.howto")),
			command=lambda: HelpDialog(
				root,
				title=str(_("window.help.title"))
			)
		)
		help.add_command(
			labelvar=TStringVar(_("window.menu.help.check-for-updates")),
			command=resources.prompt_update
		)
		help.add_separator()
		help.add_command(labelvar=TStringVar(_("window.menu.help.about")), command=partial(open_about, root))

def auto_refresh():
	refresh_linkers(game_list)
	root.after(5000, auto_refresh)
auto_refresh()

# Check if update script exists and delete
if getattr(sys, "frozen", False):
	from pathlib import Path
	script: Path = Path(sys.executable).absolute() / "update.ps1"
	try:
		script.unlink()
	except FileNotFoundError:
		resources.prompt_update(False)
else:
	resources.prompt_update(False)

# from .linker import DittoFlash
# from .. import BaseLinker

# class DittoTest(BaseLinker):
# 	name = "Ditto tester"
# 	serial = 0x101af

# 	can_flash = True
# 	can_erase = True

# 	def __init__(self, fn):
# 		from io import BytesIO
# 		with open(fn, "rb") as f:
# 			self.f = BytesIO(f.read())

# 	def __del__(self):
# 		pass

# 	def init(self):
# 		return self

# 	def seek(self, *args):
# 		return self.f.seek(*args)

# 	def read(self, *args):
# 		return self.f.read(*args)

# 	def write(self, *args):
# 		self.f.write(*args)

# 	def seek(self, *args):
# 		return self.f.seek(*args)

# 	def dump(self, stream, size: int = 0):
# 		self.f.seek(0)
# 		stream.write(self.f.read(size or None))

# 	def flash(self, stream):
# 		self.f.seek(0)
# 		self.f.write(stream.read())
# 		self.f.truncate()

# 	def erase(self):
# 		self.f.seek(0)
# 		self.f.truncate()

# game_list.add(DittoFlash(game_list, DittoTest(r"C:\dev\pokemini_060_windev\roms\Pokemon Race Mini (J).min")))

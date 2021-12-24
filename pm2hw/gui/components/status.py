# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import tkinter as tk
from typing import Dict, Optional
from tkinter import ttk
from collections import OrderedDict

from ...base import BaseFlashable
from ...logger import progress
from ...locales import _

root: tk.Tk
status: ttk.Label
active: Dict[BaseFlashable, Dict[str, Optional[progress]]] = {}

retained_value = ""

def _make_status(parent: tk.Misc):
	return ttk.Label(
		parent,
		style="Status.TLabel",
		relief=tk.RIDGE,
		borderwidth=2,
		text="...",
		padding=(5, 2)
	)

def make_status(r: tk.Tk):
	global root, status
	root = r
	status = _make_status(r)
	return status

def set_status(value: str = ""):
	global retained_value

	flashable: BaseFlashable
	action: str
	bar: progress
	msgs = []
	for flashable, activities in active.items():
		acts = list(activities.items())
		action, bar = acts[0]
		for a, b in acts:
			if b is None:
				break
			action, bar = a, b

		if bar.is_complete():
			msgs.append(
				str((_)(f"status.{action}.complete").format(
					name=flashable.name,
					secs=bar.time_taken()
				))
			)
			if bar is acts[-1][1]:
				deactivate(flashable)
		else:
			msgs.append(
				str((_)(f"status.{action}.in-progress").format(
					name=flashable.name,
					pc=bar.percent
				))
			)

	if value:
		retained_value = value
	msgs.append(retained_value)
	status.configure(text="  ".join(msgs))

def prepare_progress(flashable: BaseFlashable, *actions: str):
	flashable.is_being_removed = False
	active[flashable] = OrderedDict((a, None) for a in actions)

def add_progress(bar: progress):
	flashable = next(x for x in bar.kwargs.values() if isinstance(x, BaseFlashable))
	activities = active[flashable]
	for key, p in activities.items():
		if p is None:
			activities[key] = bar
			break
	set_status()

def deactivate(flashable: BaseFlashable):
	if not flashable.is_being_removed:
		flashable.is_being_removed = True

		def delete_it():
			del active[flashable]
			if active or retained_value:
				set_status()

		root.after(3000, delete_it)

# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from tkinter import ttk
from typing import ClassVar, NamedTuple

from .base import BaseTheme, themes

class Color(NamedTuple):
	bg: str
	fg: str

class LinkColor(NamedTuple):
	normal: str = ""
	hover: str = ""
	active: str = ""
	visited: str = ""

class ColorizedTheme(BaseTheme):
	parent = "base"

	outside: ClassVar[Color]
	inside: ClassVar[Color]
	inset: ClassVar[Color]
	console: ClassVar[Color]
	selected: ClassVar[Color]
	link: ClassVar[LinkColor]

	disabled: ClassVar[str]
	warning: ClassVar[str]
	error: ClassVar[str]

	overrides: ClassVar[dict] = {}

	@property
	def settings(self):
		parent_settings = themes[self.parent].settings
		overrides = self.overrides.copy()

		def ovr(name, settings):
			current = parent_settings.get(name, {}).copy()
			if "configure" in settings:
				current.setdefault("configure", {}).update(settings["configure"])
			if "map" in settings:
				current.setdefault("map", {}).update(settings["map"])
			if "layout" in settings:
				current["layout"] = settings["layout"]

			ov = overrides.pop(name, {})
			if "configure" in ov:
				current.setdefault("configure", {}).update(ov["configure"])
			if "map" in ov:
				current.setdefault("map", {}).update(ov["map"])
			if "layout" in ov:
				current["layout"] = ov["layouy"]
			return name, current

		ret = parent_settings.copy()
		ret.update(dict([
			ovr("RichText", {
				"configure": {
					"background": self.inside.bg,
					"foreground": self.inside.fg,
					"selectbackground": self.selected.bg,
					"selectforeground": self.selected.fg,
				}
			}),
			ovr("tt.RichText", {
				"configure": {
					"background": self.inset.bg,
					"foreground": self.inset.fg,
				}
			}),
			ovr("code.RichText", {
				"configure": {
					"background": self.inset.bg,
					"foreground": self.inset.fg,
				}
			}),
			ovr("Console.RichText", {
				"configure": {
					"background": self.console.bg,
					"foreground": self.console.fg,
					"selectbackground": self.selected.bg,
					"selectforeground": self.selected.fg,
				}
			}),
			ovr("warn.Console.RichText", {
				"configure": {
					"background": self.console.bg,
					"foreground": self.warning,
				}
			}),
			ovr("error.Console.RichText", {
				"configure": {
					"background": self.console.bg,
					"foreground": self.error,
				}
			}),
			ovr("TButton", {
				"configure": {
					"background": self.inside.bg,
					"highlightbackground": self.inside.bg,
				},
				"map": {
					"foreground": [
						("disabled", self.disabled),
						("!disabled", self.inside.fg),
					],
				},
			}),
			ovr("TFrame", {
				"configure": {
					"background": self.outside.bg,
					"highlightbackground": self.outside.bg,
				}
			}),
			ovr("TLabel", {
				"configure": {
					"background": self.outside.bg,
					"foreground": self.outside.fg,
					"highlightbackground": self.outside.bg,
				}
			}),
			ovr("TLabelframe", {
				"configure": {
					"background": self.outside.bg,
					"foreground": self.outside.fg,
					"highlightbackground": self.outside.bg,
				}
			}),
			ovr("TLabelframe.Label", {
				"configure": {
					"background": self.outside.bg,
					"foreground": self.outside.fg,
					"highlightbackground": self.outside.bg,
				}
			}),
			ovr("Menu", {
				"configure": {
					"activebackground": self.selected.bg,
					"activeforeground": self.selected.fg,
					"background": self.outside.bg,
					"disabledforeground": self.disabled,
					"foreground": self.outside.fg,
					"selectcolor": self.outside.fg,
				}
			}),
			ovr("Menu.entry", {
				"configure": {
					# "activebackground": self.selected.bg,
					"activeforeground": self.selected.fg,
					"background": self.outside.bg,
					# "foreground": self.outside.fg,
					"selectcolor": self.outside.fg,
				}
			}),
			ovr("TPanedwindow", {
				"configure": {
					"background": self.outside.bg,
					"highlightbackground": self.outside.bg,
				},
			}),
			ovr("Treeview", {
				"configure": {
					"background": self.outside.bg,
					"foreground": self.outside.fg,
					"fieldbackground": self.outside.bg,
				},
				"map": {
					"background": [
						("selected", self.selected.bg),
					],
					"foreground": [
						("disabled", self.disabled),
						("selected", self.selected.fg),
					],
				},
			}),
			ovr("TScrollbar", {
				"configure": {
					"background": self.inside.bg,
					"highlightbackground": self.outside.bg,
					"troughcolor": self.outside.bg,
				},
			}),
			*[
				(f"a{'' if k == 'normal' else ':' + k}.RichText", {
					"configure": {
						"foreground": v,
					}
				})
				for k, v in self.link._asdict().items()
				if v
			],
		]))
		ret.update(overrides)
		return ret

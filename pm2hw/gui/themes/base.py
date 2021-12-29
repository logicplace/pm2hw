import tkinter as tk
# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from tkinter import font, ttk
from typing import ClassVar, Dict

themes: Dict[str, "BaseTheme"] = {}

class MetaTheme(type):
	def __new__(cls, name, bases, dct):
		if "name" not in dct:
			dct["name"] = ""
		if "parent" not in dct:
			if bases and isinstance(bases[0], BaseTheme):
				dct["parent"] = bases[0].name
			else:
				dct["parent"] = None
		ret = super().__new__(cls, name, bases, dct)
		if dct["name"]:
			themes[dct["name"]] = ret
		return ret

class BaseTheme(metaclass=MetaTheme):
	name: ClassVar[str] = "base"
	parent: ClassVar[str] = "default"
	settings: ClassVar[dict] = {
		".": {
			"configure": {
				"font": "BaseFont",
			}
		},
		"TLabelframe": {
			"configure": {
				"borderwidth": 1,
				"relief": tk.SOLID,
			}
		},
		"Header.TLabel": {
			"configure": {
				"font": "DetailHeaderFont",
			}
		},
		"TButton": {
			"configure": {
				"borderwidth": 2,
				"padding": 2,
			},
			"map": {
				"foreground": [
					("disabled", "#666"),
					("!disabled", "#000"),
				],
				"relief": [
					("disabled", tk.RIDGE),
					("pressed", tk.SUNKEN),
					("!pressed", tk.RAISED),
				],
			},
		},
		"Treeview": {
			"configure": {
				"indent": 3,
				"rowheight": 32,  # Do not overwrite this
			}
		},
		"p.RichText": {
			"configure": {
				"font": "BaseFont",
				"spacing1": 4,
				"spacing3": 4,
				"wrap": tk.WORD,
			}
		},
		"em.RichText": {
			"configure": {
				"font": "RichTextItalicFont",
			}
		},
		"strong.RichText": {
			"configure": {
				"font": "RichTextBoldFont",
			}
		},
		"em+strong.RichText": {
			"configure": {
				"font": "RichTextBoldItalicFont",
			}
		},
		"del.RichText": {
			"configure": {
				"overstrike": True,
			}
		},
		"ins.RichText": {
			"configure": {
				"underline": True,
			}
		},
		"u.RichText": {
			"configure": {
				"underline": True,
			}
		},
		"h1.RichText": {
			"configure": {
				"font": "RichTextH1Font",
				"spacing3": 4,
			}
		},
		"h2.RichText": {
			"configure": {
				"font": "RichTextH2Font",
				"spacing1": 12,
				"spacing3": 4,
			}
		},
		"h3.RichText": {
			"configure": {
				"font": "RichTextH3Font",
				"spacing1": 12,
				"spacing3": 4,
			}
		},
		"h4.RichText": {
			"configure": {
				"font": "RichTextH4Font",
				"spacing1": 12,
				"spacing3": 4,
			}
		},
		"h5.RichText": {
			"configure": {
				"font": "RichTextH5Font",
				"spacing1": 12,
				"spacing3": 4,
			}
		},
		"h6.RichText": {
			"configure": {
				"font": "RichTextH6Font",
				"spacing1": 12,
				"spacing3": 4,
			}
		},
		"h7.RichText": {
			"configure": {
				"font": "RichTextH7Font",
				"spacing1": 12,
				"spacing3": 4,
			}
		},
		"kbd.RichText": {
			"configure": {
				"borderwidth": 3,
				"relief": tk.RAISED,
				"spacing1": 2,
				"spacing2": 2,
				"spacing3": 2,
				"tabs": 4,
			}
		},
		"tt.RichText": {
			"configure": {
				"background": "#ccc",
				"borderwidth": 2,
				"font": "RichTextMonoFont",
				"relief": tk.GROOVE,
				"spacing1": 2,
				"spacing2": 2,
				"spacing3": 2,
				"tabs": 4,
			}
		},
		"code.RichText": {
			"configure": {
				"background": "#ccc",
				"borderwidth": 2,
				"font": "RichTextMonoFont",
				"lmargin1": 4,
				"lmargin2": 4,
				"relief": tk.GROOVE,
				"spacing1": 4,
				"spacing3": 4,
				"tabs": 20,
				"wrap": tk.NONE,
			}
		},
		"a:normal.RichText": {
			"configure": {
				"foreground": "#06c",
				"underline": True,
			}
		},
		"a:visited.RichText": {
			"configure": {
				"foreground": "#551a8b",
				"underline": True,
			}
		},
		"ol.RichText": {
			"configure": {
				"font": "BaseFont",
				"marker": '["decimal", "lower-alpha"]',
				"spacing1": 4,
				"spacing3": 4,
				"tabs": 6,
				"wrap": tk.WORD,
			}
		},
		"ul.RichText": {
			"configure": {
				"font": "BaseFont",
				"marker": '["disc", "circle"]',
				"spacing1": 4,
				"spacing3": 4,
				"tabs": 6,
				"wrap": tk.WORD,
			}
		},
		"li.RichText": {
			"configure": {
			}
		},
		"ul.listmark.RichText": {
			"configure": {
				"font": "RichTextUListMarkFont",
			}
		},
		"widget.RichText": {
			"configure": {
				"justify": tk.CENTER,
			}
		},
		"Console.RichText": {
			"configure": {
				"font": "RichTextConsoleFont",
				"wrap": tk.WORD,
			}
		},
		"warn.Console.RichText": {
			"configure": {
				"foreground": "#aa0",
			}
		},
		"error.Console.RichText": {
			"configure": {
				"foreground": "#600",
			}
		},
		"OrderedListItem.TFrame": {
			"configure": {
				"borderwidth": 2,
				"relief": tk.RAISED,
			}
		},
		"OrderedListItem.TButton": {
			"configure": {
				"anchor": tk.CENTER,
				"borderwidth": 0,
				"height": 8,
				"relief": tk.FLAT,
			}
		},
		"OrderedListItem.TLabel": {
			"configure": {
				"font": "BaseFont",
			}
		},
	}

	root: tk.Tk
	style: ttk.Style
	anti_collection: list

	def __init__(self, root: tk.Tk):
		self.root = root
		self.anti_collection = []

		self.style = ttk.Style(root)
		if self.name:
			self.style.theme_create(
				self.name,
				parent=self.parent,
				settings=self.settings
			)

	def apply(self):
		if self.name:
			self.style.theme_use(self.name)
			self.update_fonts()

	# Font management
	def fonts(self):
		for x in dir(self):
			if x.endswith("Font"):
				yield x, getattr(self, x)

	@staticmethod
	def _norm_font_config(families, config):
		if isinstance(config.get("family"), (list, tuple)):
			for family in config["family"]:
				if family in families:
					config["family"] = family
					break

	def create_fonts(self):
		families = font.families()
		for name, config in self.fonts():
			self._norm_font_config(families, config)
			f = font.Font(self.root, name=name, **config)
			self.anti_collection.append(f)

	def update_fonts(self):
		families = font.families()
		for name, config in self.fonts():
			f = font.nametofont(name)
			self._norm_font_config(families, config)
			f.configure(**config)

	# Fonts
	BaseFont = {
		"family": "Arial",
		"size": 12,
	}
	LibraryListEntryFont = {
		"family": "Arial",
		"size": 14,
		"weight": font.NORMAL,
	}
	LibraryListCategoryFont = {
		"family": "Arial",
		"size": 16,
		"weight": font.BOLD,
		"underline": True,
	}
	GameInfoTitleFont = {
		"family": "Arial",  # TODO: use pokemon mini font
		"size": 20,
		"weight": font.BOLD,
		"underline": True,
	}
	DetailHeaderFont = {
		"family": "Arial",  # TODO: use pokemon mini font
		"size": 12,
		"weight": font.BOLD,
	}

	RichTextItalicFont = {
		"family": "Arial",
		"size": 12,
		"slant": font.ITALIC,
	}
	RichTextBoldFont = {
		"family": "Arial",
		"size": 12,
		"weight": font.BOLD,
	}
	RichTextBoldItalicFont = {
		"family": "Arial",
		"size": 12,
		"weight": font.BOLD,
		"slant": font.ITALIC,
	}
	RichTextMonoFont = {
		"family": "Courier New",
		"size": 12,
	}
	RichTextConsoleFont = {
		"family": ["Consolas", "Courier New"],
		"size": 12,
	}
	RichTextH1Font = {
		"family": "Arial",
		"size": 24,
		"weight": font.BOLD,
	}
	RichTextH2Font = {
		"family": "Arial",
		"size": 20,
		"weight": font.BOLD,
	}
	RichTextH3Font = {
		"family": "Arial",
		"size": 18,
		"weight": font.BOLD,
	}
	RichTextH4Font = {
		"family": "Arial",
		"size": 16,
		"weight": font.BOLD,
	}
	RichTextH5Font = {
		"family": "Arial",
		"size": 14,
		"weight": font.BOLD,
	}
	RichTextH6Font = {
		"family": "Arial",
		"size": 12,
		"underline": True,
		"weight": font.BOLD,
	}
	RichTextH7Font = {
		"family": "Arial",
		"size": 12,
		"slant": font.ITALIC,
		"underline": True,
		"weight": font.NORMAL,
	}
	RichTextUListMarkFont = {
		"family": "Arial",
		"size": 14,
	}

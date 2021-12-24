# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from . import base, dark, light, solarized
from .base import themes

root = None

def init(root, theme: str = ""):
	for name, cls in themes.items():
		themes[name] = cls(root)
	themes["base"].create_fonts()
	if theme:
		themes[theme].apply()

def select_theme(name: str):
	if name not in themes:
		raise ValueError(f"theme {name} does not exist")
	themes[name].apply()

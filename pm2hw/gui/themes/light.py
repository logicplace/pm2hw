# Copyright (C) 2021 Sapphire Becker (logicplace.com)
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .colorized import ColorizedTheme, Color, LinkColor

class LightTheme(ColorizedTheme):
	name = "light"
	parent = "base"

	outside = Color("#f0f0f0", "#000")
	inside = Color("#e5e0e0", "#000")
	inset = Color("#ccc", "#000")
	console = Color("#d0dddd", "#000")
	selected = Color("#3390ff", "#eee")
	link = LinkColor("#06c", visited="#551a8b")

	disabled = "#666"
	warning = "#aa0"
	error = "#600"

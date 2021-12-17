from .colorized import ColorizedTheme, Color, LinkColor

text = "#586e75"

class SolarizedTheme(ColorizedTheme):
	selected = Color("#268bd2", "#eee8d5")
	link = LinkColor("#268bd2", visited="#d33682")

	disabled = "#93a1a1"
	warning = "#b58900"
	error = "#dc322f"

class SolarizedDarkTheme(SolarizedTheme):
	name = "solarized dark"
	parent = "base"

	outside = Color("#002b36", text)
	inside = Color("#073642", text)
	inset = Color("#073642", "#2aa198")
	console = Color("#002b36", text)

class SolarizedLightTheme(SolarizedTheme):
	name = "solarized light"
	parent = "base"

	outside = Color("#fdf6e3", text)
	inside = Color("#eee8d5", text)
	inset = Color("#eee8d5", "#2aa198")
	console = Color("#fdf6e3", text)

	overrides = {
		"RichText": {
			"configure": {
				"background": outside.bg,
				"foreground": outside.fg,
			}
		},
		"Status.TLabel": {
			"configure": {
				"background": inside.bg,
				"foreground": inside.fg,
				"highlightbackground": inside.bg,
			},
		},
		"Treeview": {
			"configure": {
				"background": inside.bg,
				"foreground": inside.fg,
				"fieldbackground": inside.bg,
			},
		},
	}
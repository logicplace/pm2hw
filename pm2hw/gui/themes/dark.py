from .colorized import ColorizedTheme, Color, LinkColor

class DarkTheme(ColorizedTheme):
	name = "dark"
	parent = "base"

	outside = Color("#444", "#ffe")
	inside = Color("#334", "#ddc")
	inset = Color("#222", "#ddc")
	console = Color("#1a0505", "#eee")
	selected = Color("#77a", "#544")
	link = LinkColor("#39f", visited="#9b54de")

	disabled = "#777"
	warning = "#fe3"
	error = "#f34"
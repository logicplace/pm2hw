import tkinter as tk
from tkinter import ttk
from typing import Literal, Optional, Sequence

class ScrollFrame(ttk.Frame):
	top: ttk.Frame
	canvas: tk.Canvas

	def __init__(
		self,
		master: Optional[tk.Misc] = ...,
		*,
		border: tk._ScreenUnits = ...,
		iborder: tk._ScreenUnits = ...,
		borderwidth: tk._ScreenUnits = ...,
		iborderwidth: tk._ScreenUnits = ...,
		class_: str = ...,
		cursor: tk._Cursor = ...,
		height: tk._ScreenUnits = ...,
		name: str = ...,
		padding: tk._Padding = ...,
		ipadding: tk._Padding = ...,
		relief: tk._Relief = ...,
		irelief: tk._Relief = ...,
		style: str = ...,
		istyle: str = ...,
		takefocus: tk._TakeFocusValue = ...,
		width: tk._ScreenUnits = ...,
		orient: Literal["horizontal", "vertical"] | Sequence[Literal["horizontal", "vertical"]] = ...,
	): ...

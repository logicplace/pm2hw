import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Literal, Sequence, Tuple, overload

class RichText(tk.Text):
	top: ttk.Frame
	markdown_tags: Tuple[str]

	# Commented out options are set by the style
	def __init__(
		self,
		master: tk.Misc | None = ...,
		cnf: dict[str, Any] | None = ...,
		*,
		autoseparators: bool = ...,
		# background: tk._Color = ...,
		blockcursor: bool = ...,
		# border: tk._ScreenUnits = ...,
		# borderwidth: tk._ScreenUnits = ...,
		# cursor: tk._Cursor = ...,
		endline: int | Literal[""] = ...,
		exportselection: bool = ...,
		# font: tk._FontDescription = ...,
		# foreground: tk._Color = ...,
		height: tk._ScreenUnits = ...,
		# highlightbackground: tk._Color = ...,
		# highlightcolor: tk._Color = ...,
		# highlightthickness: tk._ScreenUnits = ...,
		# inactiveselectbackground: tk._Color = ...,
		# insertbackground: tk._Color = ...,
		# insertborderwidth: tk._ScreenUnits = ...,
		insertofftime: int = ...,
		insertontime: int = ...,
		insertunfocussed: Literal["none", "hollow", "solid"] = ...,
		# insertwidth: tk._ScreenUnits = ...,
		maxundo: int = ...,
		name: str = ...,
		# padx: tk._ScreenUnits = ...,
		# pady: tk._ScreenUnits = ...,
		# relief: tk._Relief = ...,
		# selectbackground: tk._Color = ...,
		# selectborderwidth: tk._ScreenUnits = ...,
		# selectforeground: tk._Color = ...,
		setgrid: bool = ...,
		# spacing1: tk._ScreenUnits = ...,
		# spacing2: tk._ScreenUnits = ...,
		# spacing3: tk._ScreenUnits = ...,
		startline: int | Literal[""] = ...,
		state: Literal["normal", "disabled", "readonly"] = ...,
		style: str = ...,
		style_tags: Tuple[str] = ...,
		# tabs: tk._ScreenUnits | str | Tuple[tk._ScreenUnits | str, ...] = ...,
		# tabstyle: Literal["tabular", "wordprocessor"] = ...,
		takefocus: tk._TakeFocusValue = ...,
		undo: bool = ...,
		width: int = ...,
		# wrap: Literal["none", "char", "word"] = ...,
		orient: Literal["horizontal", "vertical"] | Sequence[Literal["horizontal", "vertical"]] = ...,
	) -> None: ...

	@overload
	def configure(
		self,
		cnf: dict[str, Any] | None = ...,
		*,
		autoseparators: bool = ...,
		# background: tk._Color = ...,
		blockcursor: bool = ...,
		# border: tk._ScreenUnits = ...,
		# borderwidth: tk._ScreenUnits = ...,
		# cursor: tk._Cursor = ...,
		endline: int | Literal[""] = ...,
		exportselection: bool = ...,
		# font: tk._FontDescription = ...,
		# foreground: tk._Color = ...,
		height: tk._ScreenUnits = ...,
		# highlightbackground: tk._Color = ...,
		# highlightcolor: tk._Color = ...,
		# highlightthickness: tk._ScreenUnits = ...,
		# inactiveselectbackground: tk._Color = ...,
		# insertbackground: tk._Color = ...,
		# insertborderwidth: tk._ScreenUnits = ...,
		insertofftime: int = ...,
		insertontime: int = ...,
		# insertunfocussed: Literal["none", "hollow", "solid"] = ...,
		# insertwidth: tk._ScreenUnits = ...,
		maxundo: int = ...,
		# padx: tk._ScreenUnits = ...,
		# pady: tk._ScreenUnits = ...,
		# relief: tk._Relief = ...,
		# selectbackground: tk._Color = ...,
		# selectborderwidth: tk._ScreenUnits = ...,
		# selectforeground: tk._Color = ...,
		setgrid: bool = ...,
		# spacing1: tk._ScreenUnits = ...,
		# spacing2: tk._ScreenUnits = ...,
		# spacing3: tk._ScreenUnits = ...,
		startline: int | Literal[""] = ...,
		state: Literal["normal", "disabled"] = ...,
		# tabs: tk._ScreenUnits | str | Tuple[tk._ScreenUnits | str, ...] = ...,
		# tabstyle: Literal["tabular", "wordprocessor"] = ...,
		takefocus: tk._TakeFocusValue = ...,
		undo: bool = ...,
		width: int = ...,
		# wrap: Literal["none", "char", "word"] = ...,
		xscrollcommand: tk._XYScrollCommand = ...,
		yscrollcommand: tk._XYScrollCommand = ...,
	) -> dict[str, tuple[str, str, str, Any, Any]] | None: ...

	@overload
	def configure(self, cnf: str) -> tuple[str, str, str, Any, Any]: ...

	def insert(
		self,
		index: tk._TextIndex,
		chars: str,
		*args: str | list[str] | Tuple[str, ...]
	) -> None: ...

	def insert_hyperlink(
		self,
		index: tk._TextIndex,
		chars: str,
		href_or_callable: str | Callable[[None], None],
		*tags: str,
	) -> None: ...

	def hyperlink_add(
		self,
		href_or_callable: str | Callable[[None], None],
		index1: tk._TextIndex,
		index2: tk._TextIndex | None,
	) -> None: ...

	def insert_markdown(
		self,
		index: tk._TextIndex,
		markdown: str,
		*tags: str,
		html_handlers: dict[str, Callable[[str], str | Callable[[None], None]]]
	) -> None: ...

	def clear(self) -> None: ...

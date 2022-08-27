import tkinter as tk
from tkinter import ttk, simpledialog

simpledialog.Button = ttk.Button
simpledialog.Frame = ttk.Frame
simpledialog.Label = ttk.Label

class Dialog(simpledialog.Dialog):
	def body(self, master: tk.Frame):
		self.bind("<<ThemeChanged>>", self.update_styling)
		self.update_styling()

	def update_styling(self, *_):
		s = ttk.Style()
		bg = s.configure("TFrame", "background")
		self.configure(background=bg)

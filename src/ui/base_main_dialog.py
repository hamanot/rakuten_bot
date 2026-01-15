import tkinter as tk
from ui.base_dialog import BaseDialog

class BaseMainDialog(tk.Tk, BaseDialog):
    """アプリのメインウィンドウ用。tk.Tkを継承"""
    def __init__(self, title="Main App", size="600x400"):
        super().__init__()
        self._init_base_logic()
        self.title(title)
        if size:
            self.geometry(size)
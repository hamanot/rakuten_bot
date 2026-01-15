import tkinter as tk
from ui.base_dialog import BaseDialog

class BaseSubDialog(tk.Toplevel, BaseDialog):
    """設定やデバッグなどの子ウィンドウ用。tk.Toplevelを継承"""
    def __init__(self, parent, title="Sub Dialog", size=None):
        super().__init__(parent)
        self._init_base_logic()
        self.title(title)
        if size:
            self.geometry(size)

        if parent:
            self.transient(parent)
            self.grab_set()

        self.protocol("WM_DELETE_WINDOW", self.close_dialog)

    def close_dialog(self):
        try:
            self.grab_release()
        except:
            pass
        self.destroy()
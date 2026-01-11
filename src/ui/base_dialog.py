import tkinter as tk
from tkinter import ttk
import os


class BaseDialog(tk.Toplevel):
    def __init__(self, parent, title="Dialog", size="400x300"):
        super().__init__(parent)
        self.title(title)
        self.geometry(size)
        self.protocol("WM_DELETE_WINDOW", self.close_dialog)

        # プロジェクトルートと設定ディレクトリの特定
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(os.path.dirname(current_dir))
        self.conf_dir = os.path.join(self.project_root, "conf")

        self.transient(parent)
        self.grab_set()

    def create_container(self, padding="20"):
        container = ttk.Frame(self, padding=padding)
        container.pack(fill=tk.BOTH, expand=True)
        return container

    def close_dialog(self):
        self.grab_release()
        self.destroy()
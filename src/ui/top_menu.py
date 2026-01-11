import tkinter as tk
from tkinter import ttk, messagebox
import os, sys

# パス解決
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path: sys.path.insert(0, src_dir)

from ui.user_config import UserConfigDialog
from ui.item_config import ItemConfigDialog
from component.user_manager import UserManager
from component.item_manager import ItemManager


class TopMenu(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rakuten Bot")
        self.geometry("400x500")

        self.conf_dir = os.path.join(os.path.dirname(src_dir), "conf")
        if not os.path.exists(self.conf_dir): os.makedirs(self.conf_dir)

        self.result = {"is_start": False, "debug_mode": tk.BooleanVar(value=True)}
        self._create_widgets()
        self.after(100, self._check)

    def _check(self):
        if not UserManager(self.conf_dir).is_valid():
            UserConfigDialog(self)
        elif not ItemManager(self.conf_dir).is_valid():
            ItemConfigDialog(self)

    def _create_widgets(self):
        c = ttk.Frame(self, padding="20")
        c.pack(fill="both", expand=True)
        ttk.Label(c, text="楽天Botマネージャー", font=("", 14, "bold")).pack(pady=20)

        ttk.Button(c, text="ユーザー設定", command=lambda: UserConfigDialog(self)).pack(fill="x", pady=5)
        ttk.Button(c, text="商品リスト設定", command=lambda: ItemConfigDialog(self)).pack(fill="x", pady=5)

        f = ttk.Frame(c)
        f.pack(side="bottom", fill="x", pady=20)
        ttk.Button(f, text="終了", command=self.destroy).pack(side="left", fill="x", expand=True)
        ttk.Button(f, text="開始", command=self._start).pack(side="right", fill="x", expand=True)

    def _start(self):
        if UserManager(self.conf_dir).is_valid() and ItemManager(self.conf_dir).is_valid():
            self.result["is_start"] = True
            self.destroy()
        else:
            messagebox.showerror("エラー", "設定が未完了です")


if __name__ == "__main__":
    TopMenu().mainloop()
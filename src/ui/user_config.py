import tkinter as tk
from tkinter import ttk, messagebox
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui.base_dialog import BaseDialog
from component.user_manager import UserManager


class UserConfigDialog(BaseDialog):
    def __init__(self, parent):
        super().__init__(parent, title="ユーザー情報設定", size="400x300")
        self.manager = UserManager(self.conf_dir)
        self.id_var = tk.StringVar()
        self.pass_var = tk.StringVar()

        u, p = self.manager.load()
        if u: self.id_var.set(u); self.pass_var.set(p)
        self._create_widgets()

    def _create_widgets(self):
        c = self.create_container()
        ttk.Label(c, text="楽天ID:").pack(anchor="w")
        ttk.Entry(c, textvariable=self.id_var).pack(fill="x", pady=(0, 10))
        ttk.Label(c, text="パスワード:").pack(anchor="w")
        ttk.Entry(c, textvariable=self.pass_var, show="*").pack(fill="x", pady=(0, 20))

        btn_f = ttk.Frame(c)
        btn_f.pack(fill="x")
        ttk.Button(btn_f, text="保存", command=self._save).pack(side="right", padx=5)
        ttk.Button(btn_f, text="閉じる", command=self.close_dialog).pack(side="right")

    def _save(self):
        self.manager.save(self.id_var.get(), self.pass_var.get())
        messagebox.showinfo("完了", "保存しました")
        self.close_dialog()
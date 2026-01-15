import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys

# 自作ベースクラスをインポート
from ui.base_main_dialog import BaseMainDialog
from ui.user_config import UserConfigDialog
from ui.item_config import ItemConfigDialog
from component.user_manager import UserManager
from component.item_manager import ItemManager


class TopMenu(BaseMainDialog):
    def __init__(self):
        # 1. BaseMainDialogの初期化 (ここで tk.Tk と BaseDialog の初期化が行われる)
        super().__init__(title="Rakuten Bot", size="400x520")

        self.result = {
            "is_start": False,
            "debug_mode": tk.BooleanVar(value=True)
        }

        # 2. UI構築
        self._create_widgets()

        # 起動100ミリ秒後に自動チェックを実行
        self.after(100, self._auto_check_on_launch)

    def _auto_check_on_launch(self):
        """起動時の未設定チェック"""
        u_mgr = UserManager()
        if not u_mgr.is_valid():
            messagebox.showwarning("未設定", "ユーザー情報が設定されていません。設定画面を開きます。")
            UserConfigDialog(self)

    def _create_widgets(self):
        # BaseMainDialog 継承により、将来的にスクロールが必要なら
        # self.create_scrollable_container() を呼ぶだけで対応可能
        c = ttk.Frame(self, padding="20")
        c.pack(fill="both", expand=True)

        ttk.Label(c, text="楽天自動購入マネージャー", font=("", 14, "bold")).pack(pady=20)

        mode_f = ttk.LabelFrame(c, text=" 動作モード設定 ", padding="10")
        mode_f.pack(fill="x", pady=(0, 20))
        ttk.Checkbutton(mode_f, text="デバッグモード (テスト用設定)",
                        variable=self.result["debug_mode"]).pack(anchor="w")

        ttk.Button(c, text="ユーザー設定 (ID/PASS)",
                   command=lambda: UserConfigDialog(self)).pack(fill="x", pady=5)
        ttk.Button(c, text="商品・バリエーション設定",
                   command=self._open_item_config).pack(fill="x", pady=5)

        f = ttk.Frame(c)
        f.pack(side="bottom", fill="x", pady=20)
        ttk.Button(f, text="終了", command=self.destroy).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(f, text="実行開始", command=self._start).pack(side="right", fill="x", expand=True, padx=5)

    def _open_item_config(self):
        ItemConfigDialog(self, debug_mode=self.result["debug_mode"].get())

    def _start(self):
        is_debug = self.result["debug_mode"].get()
        u_mgr = UserManager()
        i_mgr = ItemManager(debug_mode=is_debug)

        if not u_mgr.is_valid():
            messagebox.showwarning("未設定", "楽天ID・パスワードが設定されていません。\n設定画面を開きます。")
            UserConfigDialog(self)
            return

        if not i_mgr.is_valid():
            messagebox.showwarning("未設定", "商品設定または注文手続きURLが完了していません。\n設定画面を開きます。")
            self._open_item_config()
            return

        if messagebox.askyesno("確認", "自動購入処理を開始しますか？"):
            self.result["is_start"] = True
            self.destroy()


if __name__ == "__main__":
    TopMenu().mainloop()
import tkinter as tk
from tkinter import ttk, messagebox
import os

# 自作ベースクラスとダイアログのインポート
from ui.base_main_dialog import BaseMainDialog
from ui.user_config import UserConfigDialog
from ui.item_config import ItemConfigDialog
from ui.toggle_button_parts import ToggleButton

# マネージャー（シングルトン）とコンポーネントのインポート
from component.chrome_driver_manager import ChromeDriverManager
from component.user_manager import UserManager
from component.item_manager import ItemManager
from bl.purchase_logic import PurchaseLogic


class TopMenu(BaseMainDialog):
    def __init__(self):
        # 1. BaseMainDialogの初期化 (リサイズを考慮して高さは目安)
        super().__init__(title="Rakuten Bot", size="400x500")

        # 2. 状態管理
        self.debug_var = tk.BooleanVar(value=True)

        # Logic インスタンスを取得
        try:
            self.logic = PurchaseLogic.get_instance(debug_mode=self.debug_var.get())
        except Exception as e:
            messagebox.showerror("初期化失敗", f"ロジックの起動に失敗しました:\n{e}")
            self.destroy()
            return

        self.result = {
            "is_start": False
        }

        # 3. UI構築
        self._create_widgets()

        # リサイズを許可
        self.resizable(True, True)

        # 起動時の自動チェック
        self.after(100, self._auto_check_on_launch)

    def _auto_check_on_launch(self):
        u_mgr = UserManager()
        if not u_mgr.is_valid():
            messagebox.showwarning("未設定", "ユーザー情報が設定されていません。設定画面を開きます。")
            UserConfigDialog(self)

    def _create_widgets(self):
        # --- スタイルの構築 ---
        self.style = ttk.Style()
        base_font = self.style.lookup("TButton", "font") or ""
        self.style.configure("Production.TButton", foreground="red", font=base_font)

        # --- A. 下部ボタンエリア（最下部に固定） ---
        bottom_f = ttk.Frame(self, padding="20")
        bottom_f.pack(side="bottom", fill="x")

        ttk.Separator(bottom_f, orient="horizontal").pack(fill="x", pady=(0, 15))

        btn_row = ttk.Frame(bottom_f)
        btn_row.pack(fill="x")

        # 終了ボタン
        ttk.Button(btn_row, text="終了", command=self.destroy).pack(side="left", fill="x", expand=True, padx=5)

        # 実行開始ボタン
        self.btn_execute = ttk.Button(btn_row, command=self._start)
        self.btn_execute.pack(side="right", fill="x", expand=True, padx=5)

        # --- B. スクロール可能なメインエリア ---
        self.scroll_f = self.create_scrollable_container()
        c = ttk.Frame(self.scroll_f, padding="20")
        c.pack(fill="both", expand=True)

        ttk.Label(c, text="楽天自動購入マネージャー", font=("", 14, "bold")).pack(pady=(0, 20))

        # --- グループ：動作モード設定 ---
        mode_f = ttk.LabelFrame(c, text=" 動作モード設定 ", padding="10")
        mode_f.pack(fill="x", pady=(0, 15))

        mode_inner = ttk.Frame(mode_f)
        mode_inner.pack(fill="x", expand=True)

        ttk.Label(mode_inner, text="デバッグモード (ON/OFF)").pack(side="left", padx=(0, 10))

        self.mode_btn = ToggleButton(
            mode_inner,
            variable=self.debug_var,
            command=self._sync_debug_mode
        )
        self.mode_btn.pack(side="right")

        # --- グループ：各種設定 ---
        config_f = ttk.LabelFrame(c, text=" 各種設定 ", padding="10")
        config_f.pack(fill="x", pady=(0, 15))

        ttk.Button(config_f, text="ユーザー設定 (ID/PASS)",
                   command=lambda: UserConfigDialog(self)).pack(fill="x", pady=5)
        ttk.Button(config_f, text="商品・バリエーション設定",
                   command=self._open_item_config).pack(fill="x", pady=5)

        # 初回のスタイル反映
        self._update_execute_button_style()

    def _sync_debug_mode(self):
        """デバッグモードの切り替えを反映"""
        new_mode = self.debug_var.get()
        self.logic = PurchaseLogic.get_instance(debug_mode=new_mode)
        self._update_execute_button_style()

    def _update_execute_button_style(self):
        """デバッグモードの状態に応じてテキストとスタイルを切り替える"""
        is_debug = self.debug_var.get()

        if not is_debug:
            self.btn_execute.config(
                text="実行開始（本番）",
                style="Production.TButton"
            )
        else:
            self.btn_execute.config(
                text="実行開始（デバッグ）",
                style=""
            )

    def _open_item_config(self):
        ItemConfigDialog(self, debug_mode=self.debug_var.get())

    def _start(self):
        is_debug = self.debug_var.get()
        self.logic = PurchaseLogic.get_instance(debug_mode=is_debug)

        if not UserManager().is_valid():
            messagebox.showwarning("未設定", "ユーザー設定が不完全です。")
            UserConfigDialog(self)
            return

        if not ItemManager(debug_mode=is_debug).is_valid():
            messagebox.showwarning("未設定", "商品設定が不完全です。")
            self._open_item_config()
            return

        # 本番モード時のみメッセージをさらに強調
        msg = "【警告：本番モード】\n実際に注文処理を開始します。本当によろしいですか？" if not is_debug else "自動購入処理を開始しますか？"

        if messagebox.askyesno("実行確認", msg):
            self.result["is_start"] = True
            self.destroy()


if __name__ == "__main__":
    TopMenu().mainloop()
import tkinter as tk
from tkinter import ttk, messagebox
# ベースクラスをインポート
from ui.base_sub_dialog import BaseSubDialog
from component.user_manager import UserManager

class UserConfigDialog(BaseSubDialog):
    def __init__(self, parent):
        # 1. BaseSubDialogの初期化 (初期サイズ指定。adjust_to_contentで再計算されます)
        super().__init__(parent, title="ユーザー設定 (暗号化保存)", size="400x400")

        # 2. データの準備
        self.manager = UserManager()
        self.current_data = self.manager.load()

        # 3. UI作成メソッドを実行
        self._create_widgets()

        # --- 復活：サイズ自動調整 ---
        # 固定エリア（下のボタンなど）を含めた高さを計算して反映します
        self.adjust_to_content(width=400)

        # 4. ユーザーによるリサイズ許可と最低サイズ制限
        self.update_idletasks()
        self.minsize(400, 385)
        self.resizable(True, True)

    def _create_widgets(self):
        # --- A. 下部ボタンエリア（最下部固定・右寄せ） ---
        bottom_f = ttk.Frame(self, padding="20")
        bottom_f.pack(side="bottom", fill="x")

        ttk.Separator(bottom_f, orient="horizontal").pack(fill="x", pady=(0, 20))

        btn_row = ttk.Frame(bottom_f)
        btn_row.pack(side="right")

        ttk.Button(btn_row, text="キャンセル", width=12, command=self.close_dialog).pack(side="left", padx=5)
        ttk.Button(btn_row, text="保存", width=12, command=self._save).pack(side="left", padx=5)

        # --- B. スクロール可能なメインエリア ---
        self.scroll_f = self.create_scrollable_container()

        # 変数作成
        self.id_var = tk.StringVar(value=self.current_data.get("rakuten_id", ""))
        self.pw_var = tk.StringVar(value=self.current_data.get("rakuten_pw", ""))

        # コンテンツ用フレーム
        main_f = ttk.LabelFrame(self.scroll_f, text=" ログイン情報 ", padding="25")
        main_f.pack(fill="both", expand=True, pady=30, padx=25)

        ttk.Label(main_f, text="楽天ユーザID:").pack(anchor="w")
        ttk.Entry(main_f, textvariable=self.id_var).pack(fill="x", pady=(5, 25), ipady=3)

        ttk.Label(main_f, text="パスワード:").pack(anchor="w")
        ttk.Entry(main_f, textvariable=self.pw_var, show="*").pack(fill="x", pady=(5, 15), ipady=3)

        # 注意文言
        notice_text = "※入力された情報は暗号化してローカルに保存されます。"
        ttk.Label(main_f, text=notice_text, font=("", 8), foreground="gray").pack(anchor="w", pady=(10, 0))

    def _save(self):
        new_data = {
            "rakuten_id": self.id_var.get().strip(),
            "rakuten_pw": self.pw_var.get().strip()
        }
        if self.manager.save(new_data):
            messagebox.showinfo("成功", "設定を保存しました。")
            self.close_dialog()
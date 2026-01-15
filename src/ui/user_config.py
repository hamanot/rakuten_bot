import tkinter as tk
from tkinter import ttk, messagebox
# 新しいベースクラスをインポート
from ui.base_sub_dialog import BaseSubDialog
from component.user_manager import UserManager

class UserConfigDialog(BaseSubDialog):
    def __init__(self, parent):
        # 1. BaseSubDialogの初期化（Toplevelとしての初期化とBaseDialogのロジックが走る）
        super().__init__(parent, title="ユーザー設定 (暗号化保存)", size="400x320")

        # 2. データの準備
        self.manager = UserManager()
        self.current_data = self.manager.load()

        # 3. UI作成メソッドを実行
        self._create_widgets()

        # 4. コンテンツに合わせてサイズを自動調整（BaseDialogのメソッド）
        self.adjust_to_content(width=400)

    def _create_widgets(self):
        # BaseDialogのメソッドでスクロール可能な土台を作る
        self.scroll_f = self.create_scrollable_container()

        # 変数作成（Entryに紐付けるStringVar）
        self.id_var = tk.StringVar(value=self.current_data.get("rakuten_id", ""))
        self.pw_var = tk.StringVar(value=self.current_data.get("rakuten_pw", ""))

        # --- ユーザー設定用フレーム ---
        main_f = ttk.LabelFrame(self.scroll_f, text=" ログイン情報 ", padding="15")
        main_f.pack(fill="x", pady=10, padx=15)

        ttk.Label(main_f, text="楽天ユーザID:").pack(anchor="w")
        ttk.Entry(main_f, textvariable=self.id_var).pack(fill="x", pady=(0, 10))

        ttk.Label(main_f, text="パスワード:").pack(anchor="w")
        ttk.Entry(main_f, textvariable=self.pw_var, show="*").pack(fill="x", pady=(0, 10))

        # ボタンエリア
        btn_area = ttk.Frame(self.scroll_f)
        btn_area.pack(pady=20)
        ttk.Button(btn_area, text="保存", width=12, command=self._save).pack(side="left", padx=10)
        ttk.Button(btn_area, text="キャンセル", width=12, command=self.close_dialog).pack(side="left", padx=10)

    def _save(self):
        new_data = {
            "rakuten_id": self.id_var.get().strip(),
            "rakuten_pw": self.pw_var.get().strip()
        }
        if self.manager.save(new_data):
            messagebox.showinfo("成功", "設定を保存しました。")
            self.close_dialog()

    # close_dialog は BaseSubDialog で定義されているため、
    # 特殊な追加処理がなければ記述不要（自動で親のメソッドが使われる）
import os
import tkinter as tk
from tkinter import ttk, messagebox
from ui.base_main_dialog import BaseMainDialog

# 必要なクラスをインポート
from component.chrome_driver_manager import ChromeDriverManager
from bl.purchase_logic import PurchaseLogic


class SessionManagerDialog(BaseMainDialog):
    """
    セッション更新専用UI
    シングルトンから driver と logic を直接取得してセッションを保存する
    """

    def __init__(self):
        # 1. 引数を廃止し、シングルトンから直接参照（この時点で driver は起動済みのはず）
        # ※もし万が一起動していなくても、get_driver() が勝手に起動してくれるので安全
        self.logic = PurchaseLogic.get_instance()

        # 2. BaseMainDialogの初期化
        super().__init__(title="セッション更新ツール", size="400x200")
        self._create_widgets()

        # 画面中央 & 最前面
        self.attributes("-topmost", True)

    def _create_widgets(self):
        frame = ttk.Frame(self, padding="20")
        frame.pack(fill="both", expand=True)

        info_text = (
            "■ 操作手順\n"
            "1. ブラウザでログインし、購入確認画面まで進む\n"
            "2. その後、このボタンを押してCookieを保存する"
        )
        ttk.Label(frame, text=info_text, justify="left").pack(pady=(0, 20))

        # 保存ボタン
        self.save_btn = ttk.Button(
            frame,
            text="現在の状態を保存",
            command=self.handle_save
        )
        self.save_btn.pack(fill="x", ipady=10)

    def handle_save(self):
        """
        PurchaseLogicの save_cookies() を実行。
        内部で ChromeDriverManager.get_driver() が呼ばれるので連携は完璧。
        """
        if self.logic.save_cookies():
            save_file = os.path.basename(self.logic.cookie_path)
            messagebox.showinfo("成功", f"以下のファイルに保存しました：\n{save_file}")
            self.destroy()
        else:
            messagebox.showerror("エラー", "保存に失敗しました。")
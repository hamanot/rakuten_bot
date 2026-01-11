import os
import tkinter as tk
from tkinter import ttk, messagebox
from ui.user_config import UserConfigDialog


class TopMenu(tk.Tk):
    """
    アプリケーションのメインメニュー（司令塔）。
    各設定ダイアログの呼び出しと、購入スクリプトの実行制御を行う。
    Python 3.6 (Windows) の Tcl/Tk 互換性のため、絵文字は使用しない。
    """

    def __init__(self):
        """
        トップメニューの初期化、ウィンドウ設定、パスの設定を行う。
        """
        super().__init__()
        self.title("Rakuten Bot Manager")
        self.geometry("400x520")
        self.minsize(380, 500)

        # プロジェクトルートと設定ディレクトリのパスを自動解決
        # rakuten_bot/src/ui/top_menu.py から見て ../../conf
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.conf_dir = os.path.join(base_dir, "conf")

        if not os.path.exists(self.conf_dir):
            os.makedirs(self.conf_dir)

        # main.pyに引き渡すための設定情報
        self.result = {
            "is_start": False,
            "debug_mode": tk.BooleanVar(value=True)
        }

        self._create_widgets()

    def _create_widgets(self):
        """
        UIコンポーネントを配置する。
        """
        container = ttk.Frame(self, padding="20")
        container.pack(fill=tk.BOTH, expand=True)

        # --- ヘッダー ---
        ttk.Label(
            container,
            text="楽天自動購入マネージャー",
            font=("Helvetica", 14, "bold")
        ).pack(pady=(0, 20))

        # --- 動作モード設定エリア ---
        debug_frame = ttk.LabelFrame(container, text="動作モード設定", padding="10")
        debug_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Checkbutton(
            debug_frame,
            text="デバッグモード (ログイン処理をスキップ)",
            variable=self.result["debug_mode"]
        ).pack(anchor=tk.W)

        # --- 各種設定ボタンエリア ---
        menu_frame = ttk.LabelFrame(container, text="各種設定メニュー", padding="10")
        menu_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Python 3.6 の TclError 回避のためテキストのみで構成
        ttk.Button(
            menu_frame,
            text="ユーザー情報設定 (ID/PASS)",
            command=self._open_user_config
        ).pack(fill=tk.X, pady=5)

        ttk.Button(
            menu_frame,
            text="購入ページ情報設定 (URL/時刻)",
            command=self._open_item_config
        ).pack(fill=tk.X, pady=5)

        ttk.Button(
            menu_frame,
            text="環境情報設定 (ドライバ/パス)",
            command=self._open_env_config
        ).pack(fill=tk.X, pady=5)

        ttk.Button(
            menu_frame,
            text="試験メニュー (デバッグ用)",
            command=self._open_test_menu
        ).pack(fill=tk.X, pady=5)

        # --- 実行・終了ボタンエリア ---
        action_frame = ttk.Frame(container)
        action_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        # 終了ボタン
        ttk.Button(
            action_frame,
            text="終了",
            command=self.destroy
        ).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # 開始ボタン
        self.start_btn = ttk.Button(
            action_frame,
            text="スクリプト開始",
            command=self._on_start_click
        )
        self.start_btn.pack(side=tk.RIGHT, padx=5, expand=True, fill=tk.X)

    def _open_user_config(self):
        """
        ユーザー情報設定ダイアログを起動する。
        """
        UserConfigDialog(self, self.conf_dir)

    def _open_item_config(self):
        """
        購入ページ情報設定ダイアログを起動する（今後作成予定）。
        """
        messagebox.showinfo("設定", "ItemConfigDialogを表示します（準備中）")

    def _open_env_config(self):
        """
        環境情報設定ダイアログを起動する（今後作成予定）。
        """
        messagebox.showinfo("設定", "EnvConfigDialogを表示します（準備中）")

    def _open_test_menu(self):
        """
        試験メニューダイアログを起動する（今後作成予定）。
        """
        messagebox.showinfo("試験", "TestMenuDialogを表示します（準備中）")

    def _on_start_click(self):
        """
        スクリプト開始ボタン押下時の処理。
        """
        if messagebox.askyesno("確認", "自動購入処理を開始してよろしいですか？"):
            self.result["is_start"] = True
            self.destroy()


if __name__ == "__main__":
    # モジュール単体テスト用の起動処理
    # 親ディレクトリをパスに追加して実行する必要がある場合があります
    app = TopMenu()
    app.mainloop()
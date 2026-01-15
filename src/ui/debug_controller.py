import tkinter as tk
from tkinter import ttk
import time

# BaseMainDialog（tk.Tkベース）を継承
from ui.base_main_dialog import BaseMainDialog


class DebugController(BaseMainDialog):
    def __init__(self, driver, logic, item_data):
        # 1. データを保持
        self.driver = driver
        self.logic = logic
        self.item_data = item_data

        # 2. 親（BaseMainDialog）の初期化
        # メイン窓として振る舞うため parent は不要
        super().__init__(title="デバッグコントローラー", size=None)

        # 3. UI作成
        self._create_widgets()

        # 4. コンテンツに合わせてサイズ調整
        self.adjust_to_content(width=350)

        # デバッグ用なので常に最前面に配置
        self.attributes("-topmost", True)

    def _create_widgets(self):
        # BaseDialogの共通機能でスクロール領域を作成
        self.scroll_f = self.create_scrollable_container()

        frame = ttk.Frame(self.scroll_f, padding="10")
        frame.pack(fill="both", expand=True)

        # --- ボタン類 ---
        ttk.Label(frame, text="■ デバッグ操作", font=("", 10, "bold")).pack(anchor="w", pady=(0, 5))

        ttk.Button(frame, text="商品URLへ移動",
                   command=self.go_to_item_page).pack(fill="x", pady=2)

        ttk.Button(frame, text="【全セット】を連続でカゴ入れ",
                   command=self.run_all_actions).pack(fill="x", pady=10)

        # 保存されたリストからボタン生成
        actions = self.item_data.get("required_keywords", [])
        for i, kw_str in enumerate(actions):
            # "数量###表示名###POSTデータ" の形式を分解
            parts = kw_str.split("###")
            display_name = parts[1] if len(parts) > 1 else f"セット {i + 1}"

            ttk.Button(frame, text=f"実行: {display_name}",
                       command=lambda k=kw_str: self.run_full_action(k)).pack(fill="x", pady=2)

        ttk.Button(frame, text="注文手続き画面へ",
                   command=lambda: self.logic.go_to_checkout()).pack(fill="x", pady=(10, 2))

    def go_to_item_page(self):
        url = self.item_data.get("item_url", "")
        if url:
            self.driver.get(url)

    def run_all_actions(self):
        keywords = self.item_data.get("required_keywords", [])
        for kw in keywords:
            if not self.run_full_action(kw):
                break
            time.sleep(0.2)

    def run_full_action(self, kw_string):
        print(f"DEBUG EXEC: {kw_string}")
        return self.logic.execute_cart_post(kw_string)
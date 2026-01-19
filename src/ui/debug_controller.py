import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading

from ui.base_main_dialog import BaseMainDialog
from component.chrome_driver_manager import ChromeDriverManager
from bl.purchase_logic import PurchaseLogic


class DebugController(BaseMainDialog):
    def __init__(self):
        logic = PurchaseLogic.get_instance()
        self.item_data = getattr(logic, "item", {})

        common = getattr(logic, "common", {})
        self.top_url = common.get("top_url") or "https://www.rakuten.co.jp/"

        super().__init__(title="デバッグコントローラー", size=None)
        self.btn_list = []  # 個別投入ボタン保持用
        self._create_widgets()

        # 420x700 などの初期サイズを指定しつつ、リサイズを許可
        self.adjust_to_content(width=420)
        self.resizable(True, True)
        self.attributes("-topmost", True)

    def _create_widgets(self):
        # --- 1. 終了ボタン（最下部固定エリア） ---
        # スクロールコンテナを作る前に、親（self）に対して先に bottom_f を pack しておく
        bottom_f = ttk.Frame(self, padding="10")
        bottom_f.pack(side="bottom", fill="x")

        ttk.Separator(bottom_f, orient="horizontal").pack(fill="x", pady=(0, 10))
        self.btn_close = ttk.Button(bottom_f, text="デバッグ終了 (ブラウザを閉じる)",
                                    command=self.terminate_debug)
        self.btn_close.pack(fill="x", ipady=5)

        # --- 2. スクロール可能な操作エリア ---
        # self.create_scrollable_container は side="top", fill="both", expand=True で配置される
        self.scroll_f = self.create_scrollable_container()
        frame = ttk.Frame(self.scroll_f, padding="10")
        frame.pack(fill="both", expand=True)

        # --- 以下、操作ウィジェット ---
        # --- ページ移動 ---
        ttk.Label(frame, text="■ ページ移動", font=("", 9, "bold")).pack(anchor="w")
        ttk.Button(frame, text="楽天TOPページへ移動",
                   command=lambda: ChromeDriverManager.get_driver().get(self.top_url)).pack(fill="x", pady=1)
        ttk.Button(frame, text="商品URLへ移動",
                   command=self.go_to_item_page).pack(fill="x", pady=1)

        # --- セッション ---
        ttk.Label(frame, text="■ セッション", font=("", 9, "bold")).pack(anchor="w", pady=(10, 0))
        self.btn_login = ttk.Button(frame, text="ログイン実行",
                                    command=self._start_login_thread)
        self.btn_login.pack(fill="x", pady=1)

        # --- カート追加 ---
        ttk.Label(frame, text="■ カート追加", font=("", 9, "bold")).pack(anchor="w", pady=(10, 0))
        self.btn_all = ttk.Button(frame, text="すべてをカートに追加",
                                  command=self._start_all_actions_thread)
        self.btn_all.pack(fill="x", pady=(5, 10))

        keywords_list = self.item_data.get("required_keywords", [])
        self.combo_values = ["すべてをカートに追加"]
        self.kw_map = {}

        for i, kw_str in enumerate(keywords_list):
            parts = kw_str.split("###")
            if len(parts) >= 3:
                qty = parts[0]
                full_name = parts[1]
                detail = full_name.replace('\n', ' ')
                display_name = detail[:25]
                btn_text = f"{display_name} ({qty}個)"
            else:
                btn_text = f"セット {i + 1}"

            self.combo_values.append(btn_text)
            self.kw_map[btn_text] = kw_str

            btn = ttk.Button(frame, text=btn_text,
                             command=lambda k=kw_str, idx=i: self._start_single_action_thread(k, idx))
            btn.pack(fill="x", pady=1)
            self.btn_list.append(btn)

        # --- 決済 ---
        ttk.Label(frame, text="■ 決済", font=("", 9, "bold")).pack(anchor="w", pady=(10, 0))
        self.btn_checkout = ttk.Button(frame, text="注文手続き画面へ移動",
                                       command=self._start_checkout_thread)
        self.btn_checkout.pack(fill="x", pady=(5, 0))

        # --- カート追加＆決済 ---
        ttk.Label(frame, text="■ カート追加＆決済", font=("", 9, "bold")).pack(anchor="w", pady=(15, 0))

        self.target_var = tk.StringVar()
        self.combo_target = ttk.Combobox(frame, textvariable=self.target_var, state="readonly")
        self.combo_target['values'] = self.combo_values
        self.combo_target.current(0)
        self.combo_target.pack(fill="x", pady=5)

        self.btn_mix = ttk.Button(frame, text="カート追加して注文手続き画面へ移動",
                                  command=self._start_mixed_action_thread)
        self.btn_mix.pack(fill="x", pady=2)

    # --- 内部処理：スレッド開始 ---
    def _start_login_thread(self):
        self.btn_login.config(state="disabled")
        threading.Thread(target=self.run_login, daemon=True).start()

    def _start_all_actions_thread(self):
        self.btn_all.config(state="disabled")
        threading.Thread(target=self.run_all_actions, daemon=True).start()

    def _start_single_action_thread(self, kw_string, idx):
        self.btn_list[idx].config(state="disabled")
        threading.Thread(target=lambda: self.run_single_action(kw_string, idx), daemon=True).start()

    def _start_checkout_thread(self):
        self.btn_checkout.config(state="disabled")
        threading.Thread(target=lambda: self.run_checkout(), daemon=True).start()

    def _start_mixed_action_thread(self):
        self.btn_mix.config(state="disabled")
        threading.Thread(target=self.run_mixed_action, daemon=True).start()

    # --- 内部処理：実行ロジック ---
    def go_to_item_page(self):
        url = self.item_data.get("item_url", "")
        if url:
            ChromeDriverManager.get_driver().get(url)

    def run_login(self):
        try:
            PurchaseLogic.get_instance().execute_login()
        finally:
            self.btn_login.after(0, lambda: self.btn_login.config(state="normal"))

    def run_all_actions(self):
        try:
            keywords = self.item_data.get("required_keywords", [])
            for kw in keywords:
                if not self.run_full_action(kw):
                    break
                time.sleep(0.5)
        finally:
            self.btn_all.after(0, lambda: self.btn_all.config(state="normal"))

    def run_single_action(self, kw_string, idx):
        try:
            self.run_full_action(kw_string)
        finally:
            self.btn_list[idx].after(0, lambda: self.btn_list[idx].config(state="normal"))

    def run_mixed_action(self):
        try:
            selected = self.target_var.get()
            if selected == "すべてをカートに追加":
                keywords = self.item_data.get("required_keywords", [])
                for kw in keywords:
                    self.run_full_action(kw)
            else:
                kw_str = self.kw_map.get(selected)
                if kw_str:
                    self.run_full_action(kw_str)
            self.run_checkout()
        finally:
            self.btn_mix.after(0, lambda: self.btn_mix.config(state="normal"))

    def run_full_action(self, kw_string):
        return PurchaseLogic.get_instance().execute_cart_post(kw_string)

    def run_checkout(self):
        try:
            PurchaseLogic.get_instance().go_to_checkout()
        finally:
            self.btn_checkout.after(0, lambda: self.btn_checkout.config(state="normal"))

    def terminate_debug(self):
        if messagebox.askokcancel("終了", "ブラウザを閉じてデバッグを終了しますか？"):
            try:
                ChromeDriverManager.close_driver()
            except:
                pass
            self.destroy()
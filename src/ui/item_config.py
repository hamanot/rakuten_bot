import tkinter as tk
from tkinter import ttk, messagebox
import os, sys

# パス解決
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui.base_dialog import BaseDialog
from component.item_manager import ItemManager


class ItemConfigDialog(BaseDialog):
    def __init__(self, parent):
        # 早押し用なので、横幅を少しスリムにして視認性を上げました
        super().__init__(parent, title="【最速設定】商品購入・バリエーション設定", size="650x700")
        self.manager = ItemManager(self.conf_dir)
        self.current_data = self.manager.load()

        # データの初期化（items[0]のみを使用する設計に固定）
        if not self.current_data.get("items"):
            self.current_data["items"] = [{"item_url": "", "actions": []}]

        self.item_data = self.current_data["items"][0]
        self.action_sets_vars = []

        self._create_widgets()

    def _create_widgets(self):
        container = self.create_container(padding="15")

        # --- 1. 楽天共通設定 (URLを確実に2行表示) ---
        common_f = ttk.LabelFrame(container, text=" 楽天共通設定 ", padding="10")
        common_f.pack(fill="x", pady=(0, 15))
        common_f.columnconfigure(1, weight=1)

        self.top_url = tk.StringVar(value=self.current_data["common"].get("top_url", "https://www.rakuten.co.jp/"))
        self.login_url = tk.StringVar(
            value=self.current_data["common"].get("login_url", "https://login.rakuten.co.jp/rid/login/"))

        ttk.Label(common_f, text="TOPページURL:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(common_f, textvariable=self.top_url).grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(common_f, text="ログインURL:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(common_f, textvariable=self.login_url).grid(row=1, column=1, sticky="ew", padx=5)

        # --- 2. ターゲット商品URL ---
        url_f = ttk.Frame(container)
        url_f.pack(fill="x", pady=(0, 10))
        ttk.Label(url_f, text="早押し対象の商品URL:", font=("", 10, "bold")).pack(anchor="w")
        self.url_var = tk.StringVar(value=self.item_data.get("item_url", ""))
        ttk.Entry(url_f, textvariable=self.url_var).pack(fill="x", pady=2)

        # --- 3. 連続カゴ入れ設定 (スクロールエリア) ---
        ttk.Label(container, text="カゴ入れ操作リスト (上から順に連続実行):", font=("", 10, "bold")).pack(anchor="w",
                                                                                                          pady=(10, 0))

        canvas_frame = ttk.Frame(container)
        canvas_frame.pack(fill="both", expand=True, pady=5)

        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        v_scroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scroll_f = ttk.Frame(self.canvas)

        self.scroll_f.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_win = self.canvas.create_window((0, 0), window=self.scroll_f, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_win, width=e.width))

        self.canvas.configure(yscrollcommand=v_scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        # 既存データの読み込み
        actions = self.item_data.get("actions", [])
        if not actions and "details" in self.item_data:  # 互換性
            actions = [self.item_data["details"]]

        for a_set in actions:
            self._add_action_set_ui(a_set)

        if not self.action_sets_vars:
            self._add_action_set_ui()

        # セット追加ボタン (同じページ内で別の種類を続けて買うため)
        ttk.Button(container, text="+ 続けて別の種類もカゴに入れる設定を追加",
                   command=lambda: self._add_action_set_ui()).pack(fill="x", pady=5)

        # --- 4. 保存・キャンセル ---
        btn_f = ttk.Frame(container, padding="10")
        btn_f.pack(side="bottom", fill="x")
        ttk.Button(btn_f, text="設定を保存して完了", command=self._save, width=25).pack(side="right")
        ttk.Button(btn_f, text="キャンセル", command=self.close_dialog).pack(side="right", padx=10)

    def _add_action_set_ui(self, set_data=None):
        if not set_data: set_data = [{"target_name": "", "keyword": ""}]

        set_num = len(self.action_sets_vars) + 1
        lf = ttk.LabelFrame(self.scroll_f, text=f" カゴ入れセット {set_num} ", padding="10")
        lf.pack(fill="x", pady=5)

        rows_f = ttk.Frame(lf)
        rows_f.pack(fill="x")

        current_set_vars = []

        def add_row(n="", k=""):
            row = ttk.Frame(rows_f)
            row.pack(fill="x", pady=2)
            nv, kv = tk.StringVar(value=n), tk.StringVar(value=k)
            ttk.Label(row, text="項目名:").pack(side="left")
            ttk.Entry(row, textvariable=nv, width=12).pack(side="left", padx=2)
            ttk.Label(row, text=" キーワード:").pack(side="left")
            ttk.Entry(row, textvariable=kv).pack(side="left", fill="x", expand=True, padx=2)

            # 削除ボタン
            btn = ttk.Button(row, text="×", width=3,
                             command=lambda: [row.destroy(), current_set_vars.remove((nv, kv))])
            btn.pack(side="right")
            current_set_vars.append((nv, kv))

        # 下部操作
        ctrl = ttk.Frame(lf)
        ctrl.pack(fill="x", pady=(5, 0))
        ttk.Button(ctrl, text="このセットを削除",
                   command=lambda: [lf.destroy(), self.action_sets_vars.remove(current_set_vars)]).pack(side="left")
        ttk.Button(ctrl, text="+ 項目追加(サイズ等)", command=add_row).pack(side="right")

        # データの流し込み
        for d in set_data:
            add_row(d.get("target_name"), d.get("keyword"))

        self.action_sets_vars.append(current_set_vars)

    def _save(self):
        # 1ページに特化した保存処理
        final_actions = []
        for v_set in self.action_sets_vars:
            rows = [{"target_name": p[0].get().strip(), "keyword": p[1].get().strip()}
                    for p in v_set if p[1].get().strip()]
            if rows:
                final_actions.append(rows)

        if not self.url_var.get().strip():
            messagebox.showerror("エラー", "商品URLを入力してください。")
            return

        new_data = {
            "common": {
                "top_url": self.top_url.get().strip(),
                "login_url": self.login_url.get().strip()
            },
            "items": [
                {
                    "item_url": self.url_var.get().strip(),
                    "actions": final_actions
                }
            ]
        }
        self.manager.save(new_data)
        messagebox.showinfo("成功", "早押し設定を保存しました。")
        self.close_dialog()
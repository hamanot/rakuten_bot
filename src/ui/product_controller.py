import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading
import time

from ui.base_main_dialog import BaseMainDialog
from ui.log_window_parts import LogWindowParts
from ui.spin_box_ex_parts import SpinBoxEx
from ui.toggle_button_parts import ToggleButton

# --- 設定画面・マネージャーのインポート ---
from ui.user_config import UserConfigDialog
from ui.item_config import ItemConfigDialog

from component.item_manager import ItemManager
from component.user_manager import UserManager
from bl.purchase_logic import PurchaseLogic

try:
    from tkcalendar import DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False


class ProductController(BaseMainDialog):
    def __init__(self, debug_mode=False):
        temp_root = tk.Tk()
        temp_root.withdraw()
        sw = temp_root.winfo_screenwidth()
        sh = temp_root.winfo_screenheight()
        temp_root.destroy()

        target_w = int(sw * 2 / 3)
        target_h = int(sh * 2 / 3)

        super().__init__(title="Product Order Controller", size=f"{target_w}x{target_h}")
        self.debug_mode = debug_mode

        # マネージャー初期化
        self.user_mgr = UserManager()
        self.item_mgr = ItemManager(debug_mode=self.debug_mode)
        self.parsed_data_list = self.item_mgr.get_parsed_items()
        self.logic = PurchaseLogic.get_instance(self.debug_mode)

        self._log_visible_var = tk.BooleanVar(value=True)
        self._debug_mode_var = tk.BooleanVar(value=self.debug_mode)

        self._is_reserved = False
        self._stop_event = threading.Event()
        self._browser_activated = False

        self._create_widgets()
        self._set_widgets_state("disabled")
        self._set_default_selection()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.update_idletasks()
        self.minsize(300, 400)
        self.log_viewer.info("[SYSTEM] Controller Initialized")

        # 起動時に UserManager の is_valid() でチェック
        self.after(100, self._check_user_config)

    def _check_user_config(self):
        """UserManager.is_valid() を使用して設定を確認"""
        if not self.user_mgr.is_valid():
            messagebox.showwarning("設定確認", "ユーザー情報を設定してください。")
            self._on_open_user_config()
            return False
        return True

    def _bind_mouse_wheel(self):
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _create_widgets(self):
        # --- A. バナー ---
        self.banner = tk.Label(self, text="", fg="white", font=("Meiryo", 10, "bold"), pady=8)
        self.banner.pack(side="top", fill="x")
        self._update_banner_style()

        # --- B. 終了ボタン ---
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 15))
        ttk.Button(bottom_frame, text="終了", width=12, command=self._on_closing).pack(side="right")

        # --- C. メインコンテンツ ---
        content_frame = ttk.Frame(self)
        content_frame.pack(side="top", fill="both", expand=True)

        toolbar_frame = ttk.Frame(content_frame)
        toolbar_frame.pack(fill="x", padx=20, pady=(10, 0))

        settings_f = ttk.Frame(toolbar_frame)
        settings_f.pack(side="left")
        ttk.Button(settings_f, text="ユーザー設定", width=15, command=self._on_open_user_config).pack(side="left", padx=2)
        ttk.Button(settings_f, text="商品設定", width=15, command=self._on_open_item_config).pack(side="left", padx=2)

        toggle_f = ttk.Frame(toolbar_frame)
        toggle_f.pack(side="right")
        self.log_toggle = ToggleButton(toggle_f, variable=self._log_visible_var, command=self._toggle_log)
        self.log_toggle.pack(side="right", padx=(5, 0))
        tk.Label(toggle_f, text="ログ").pack(side="right")
        self.debug_toggle = ToggleButton(toggle_f, variable=self._debug_mode_var, command=self._update_debug_mode)
        self.debug_toggle.pack(side="right", padx=(5, 15))
        tk.Label(toggle_f, text="テスト").pack(side="right")

        self.main_paned = ttk.PanedWindow(content_frame, orient="horizontal")
        self.main_paned.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        self.left_f = ttk.Frame(self.main_paned)
        self.main_paned.add(self.left_f, weight=1)

        self.canvas = tk.Canvas(self.left_f, highlightthickness=0)
        self.v_scrollbar = ttk.Scrollbar(self.left_f, orient="vertical", command=self.canvas.yview)
        self.scroll_content = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.v_scrollbar.pack(side="right", fill="y")

        self.scroll_content.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self._bind_mouse_wheel()

        # ① ページ管理
        self.lock_widgets = []
        group1 = ttk.LabelFrame(self.scroll_content, text=" ① ページ管理 ", padding=10)
        group1.pack(fill="x", pady=(0, 10))
        self.btn_top = ttk.Button(group1, text="TOPページへ移動", command=self._on_go_top)
        self.btn_top.pack(fill="x", pady=2)

        page_actions = [("ログイン", self._on_login), ("商品ページへ移動", self._on_go_product), ("カートへ移動", self._on_go_cart), ("購入ページへ移動", self._on_go_checkout)]
        for text, cmd in page_actions:
            b = ttk.Button(group1, text=text, command=cmd)
            b.pack(fill="x", pady=2); self.lock_widgets.append(b)

        # ② カート操作 & 自動購入
        group2 = ttk.LabelFrame(self.scroll_content, text=" ② カート操作 & 自動購入 ", padding=10)
        group2.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(group2, columns=("qty", "product", "variation"), show="headings", height=10)
        self.tree.heading("qty", text="数量"); self.tree.heading("product", text="商品名"); self.tree.heading("variation", text="バリエーション")
        self.tree.column("qty", width=50, anchor="center", stretch=False)
        self.tree.pack(fill="both", expand=True, pady=5); self.lock_widgets.append(self.tree)
        self._fill_treeview()

        self.btn_post = ttk.Button(group2, text="選択商品をカートに追加(POST)", command=self._on_post_cart)
        self.btn_post.pack(fill="x", pady=5); self.lock_widgets.append(self.btn_post)

        auto_f = ttk.LabelFrame(group2, text=" 自動購入スケジュール ", padding=10)
        auto_f.pack(fill="x", pady=5)
        row = ttk.Frame(auto_f); row.pack(fill="x")
        now = datetime.now()
        if HAS_TKCALENDAR: self.exec_date_ent = DateEntry(row, width=12, date_pattern='yyyy-mm-dd')
        else: self.exec_date_ent = ttk.Entry(row, width=12); self.exec_date_ent.insert(0, now.strftime("%Y-%m-%d"))
        self.exec_date_ent.pack(side="left", padx=5)

        self.hour_spin = SpinBoxEx(row, 0, 23); self.hour_spin.set_value(now.hour); self.hour_spin.pack(side="left")
        self.min_spin = SpinBoxEx(row, 0, 59); self.min_spin.set_value(now.minute); self.min_spin.pack(side="left")
        self.sec_spin = SpinBoxEx(row, 0, 59); self.sec_spin.set_value(0); self.sec_spin.pack(side="left")

        btn_f = ttk.Frame(auto_f); btn_f.pack(fill="x", pady=(10, 0))
        self.reserve_btn = ttk.Button(btn_f, text="指定時間実行予約", command=self._on_scheduled_exec)
        self.reserve_btn.pack(side="left", fill="x", expand=True)
        self.instant_btn = ttk.Button(btn_f, text="即時実行", command=self._on_instant_exec)
        self.instant_btn.pack(side="left", fill="x", expand=True)
        self.lock_widgets.extend([self.reserve_btn, self.instant_btn])

        self.right_f = ttk.LabelFrame(self.main_paned, text=" ③ 実行ログ ", padding=10)
        self.main_paned.add(self.right_f, weight=2)
        self.log_viewer = LogWindowParts(self.right_f, is_debug_mode=self.debug_mode)
        self.log_viewer.pack(fill="both", expand=True)

    def _set_widgets_state(self, state):
        for w in self.lock_widgets:
            if isinstance(w, ttk.Treeview): w.configure(selectmode="none" if state == "disabled" else "browse")
            else: w.configure(state=state)

    def _check_actual_browser_alive(self):
        from component.chrome_driver_manager import ChromeDriverManager
        driver = ChromeDriverManager._instance
        if driver is None: return False
        try: return bool(driver.title)
        except: return False

    def sync_browser_state(self):
        if self._check_actual_browser_alive():
            self._browser_activated = True
            self._set_widgets_state("normal")
        else:
            self._browser_activated = False
            self._set_widgets_state("disabled")
            self.log_viewer.info("[SYSTEM] Browser closed or reset. Please push 'TOP' button.")

    def _check_browser_ready(self):
        if not self._check_browser_ready_flag(): return False
        if not self._check_actual_browser_alive():
            self.sync_browser_state()
            return False
        return True

    def _check_browser_ready_flag(self):
        if not self._browser_activated:
            res = messagebox.askyesno("確認", "ブラウザは起動済ですか？")
            if res:
                self._browser_activated = True
                self._set_widgets_state("normal")
                return True
            else:
                messagebox.showinfo("案内", "「ページ管理」より「TOPページへ移動」を押下してください。")
                return False
        return True

    def _on_go_top(self):
        if not self._check_user_config(): return
        url = self.item_mgr.item_data.get("common", {}).get("top_url")
        if url:
            self.logic.navigate_to(url)
            self._browser_activated = True
            self._set_widgets_state("normal")
            self.log_viewer.info("[SYSTEM] Browser Activated.")

    def _on_scheduled_exec(self):
        if self._is_reserved:
            self._stop_event.set(); self._is_reserved = False; self._update_reserve_ui()
            self.log_viewer.info("[CANCEL] 予約キャンセル。")
            return
        if not self._check_user_config(): return
        if not self._check_browser_ready(): return
        try:
            date_str = self.exec_date_ent.get_date().strftime("%Y-%m-%d") if HAS_TKCALENDAR else self.exec_date_ent.get()
            h, m, s = self.hour_spin.get_value_str(), self.min_spin.get_value_str(), self.sec_spin.get_value_str()
            target_time = datetime.strptime(f"{date_str} {h}:{m}:{s}", "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            messagebox.showerror("エラー", f"日時不正: {e}"); return
        diff = (target_time - datetime.now()).total_seconds()
        if diff <= 0: messagebox.showwarning("警告", "過去の時間は指定できません"); return
        self._is_reserved = True; self._stop_event.clear(); self._update_reserve_ui()
        self.log_viewer.info(f"[SCHEDULE] {target_time.strftime('%H:%M:%S')} 予約完了")
        threading.Thread(target=self._wait_for_execute, args=(target_time,), daemon=True).start()

    def _on_instant_exec(self):
        if not self._check_user_config(): return
        if not self._check_browser_ready(): return
        threading.Thread(target=lambda: (self._on_post_cart(), self.logic.go_to_checkout()), daemon=True).start()

    def _wait_for_execute(self, target_time):
        while not self._stop_event.is_set():
            diff = (target_time - datetime.now()).total_seconds()
            if diff <= 0: self.after(0, self._on_execute_trigger); return
            wait_t = 10 if diff > 60 else (1 if diff > 10 else 0.01)
            if self._stop_event.wait(wait_t): return

    def _on_execute_trigger(self):
        self._is_reserved = False; self._update_reserve_ui()
        self.log_viewer.info("[START] 予約時間です。")
        self._on_instant_exec()

    def _update_reserve_ui(self):
        self.reserve_btn.configure(text="予約キャンセル (待機中)" if self._is_reserved else "指定時間実行予約")

    def _on_open_item_config(self):
        dialog = ItemConfigDialog(self)
        self.wait_window(dialog)
        self.reload_item_list()
        self.sync_browser_state()
        self.focus_force()
        self._bind_mouse_wheel()

    def reload_item_list(self):
        try:
            self.item_mgr.load()
            self.parsed_data_list = self.item_mgr.get_parsed_items()
            self._fill_treeview()
            self._set_default_selection()
            self.log_viewer.info("Reloaded.")
        except Exception as e: self.log_viewer.error(f"Reload failed: {e}")

    def _update_debug_mode(self):
        self.debug_mode = self._debug_mode_var.get(); self._update_banner_style()
        self.logic.debug_mode = self.debug_mode; self.item_mgr.debug_mode = self.debug_mode
        self.log_viewer.is_debug_mode = self.debug_mode
        self.log_viewer.info(f"Mode: {'DEBUG' if self.debug_mode else 'PROD'}")

    def _update_banner_style(self):
        color = "#2980b9" if self.debug_mode else "#c0392b"
        self.banner.configure(bg=color, text=f"【{'テストモード' if self.debug_mode else '本番モード'}】自動購入は{'決済前まで' if self.debug_mode else '決済まで'}実施します")

    def _fill_treeview(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for d in self.parsed_data_list:
            var_display = " / ".join(d["variation_labels"])
            self.tree.insert("", "end", iid=d["id"], values=(d["quantity"], d["product_name"], var_display))

    def _on_login(self):
        if not self._check_user_config(): return
        threading.Thread(target=lambda: (self.log_viewer.info("ログイン成功") if self.logic.execute_login() else self.log_viewer.error("ログイン失敗")), daemon=True).start()

    def _on_go_product(self):
        if not self._check_user_config(): return
        items = self.item_mgr.item_data.get("items", [])
        if items: self.logic.navigate_to(items[0].get("item_url"))

    def _on_go_cart(self):
        if not self._check_user_config(): return
        self.logic.go_to_checkout()

    def _on_go_checkout(self):
        if not self._check_user_config(): return
        self.logic.go_to_checkout()

    def _on_post_cart(self):
        if not self._check_user_config(): return
        selected = self.tree.selection()
        if not selected: return
        def _exec():
            for sid in selected:
                target = next((d for d in self.parsed_data_list if d["id"] == sid), None)
                if target and self.logic.execute_cart_post(target["raw"]): self.log_viewer.info(f"POST成功: {target['product_name']}")
        threading.Thread(target=_exec, daemon=True).start()

    def _toggle_log(self):
        ch = self.winfo_height()
        if not self._log_visible_var.get():
            self._last_full_width = self.winfo_width()
            try: self._last_sash_pos = self.main_paned.sashpos(0)
            except: self._last_sash_pos = self.left_f.winfo_width()
            self.main_paned.forget(self.right_f)
            self.left_f.configure(width=self._last_sash_pos); self.left_f.pack_propagate(False)
            self.geometry(f"{self._last_sash_pos + 20}x{ch}")
        else:
            self.left_f.pack_propagate(True)
            self.geometry(f"{getattr(self, '_last_full_width', int(self.winfo_screenwidth() * 2 / 3))}x{ch}")
            self.main_paned.add(self.right_f, weight=2)
            self.update_idletasks()
            if hasattr(self, "_last_sash_pos"): self.main_paned.sashpos(0, self._last_sash_pos)

    def _on_open_user_config(self):
        """ユーザー設定画面を開き、閉じるのを待ってからデータを再ロードする"""
        dialog = UserConfigDialog(self)

        # ダイアログが閉じられるまで、ここで処理をブロック（待機）させる
        self.wait_window(dialog)

        # ダイアログが閉じた後（保存済み）に、最新のファイルをメモリに読み込む
        self.user_mgr.load()

        # ログへの通知とUIの復旧
        if self.user_mgr.is_valid():
            self.log_viewer.info("[SYSTEM] ユーザー設定が反映されました。")

        self.focus_force()
        self._bind_mouse_wheel()

    def _set_default_selection(self):
        children = self.tree.get_children()
        if children: self.tree.selection_set(children[0])

    def _on_closing(self):
        from component.chrome_driver_manager import ChromeDriverManager
        self._stop_event.set(); ChromeDriverManager.quit_driver(); self.destroy()

if __name__ == "__main__":
    app = ProductController(debug_mode=True)
    app.mainloop()
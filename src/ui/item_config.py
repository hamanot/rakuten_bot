import tkinter as tk
from tkinter import ttk, messagebox
import threading
import re

# インポートパーツ
from ui.base_sub_dialog import BaseSubDialog
from ui.toggle_button_parts import ToggleButton
from component.item_manager import ItemManager
from bl.item_analysis_logic import ItemAnalysisLogic


class ItemConfigDialog(BaseSubDialog):
    def __init__(self, parent, debug_mode=True):
        # 1. BaseSubDialogの初期化 (サイズ固定)
        super().__init__(parent, title="商品設定 - POSTパラメータ抽出モード", size="950x600")

        self.debug_mode = debug_mode
        self.logic = ItemAnalysisLogic(debug_mode=self.debug_mode)
        self.manager = ItemManager(debug_mode=debug_mode)

        # データの準備
        self.current_data = self.manager.load()
        if not self.current_data.get("common"): self.current_data["common"] = {}
        if not self.current_data.get("items"): self.current_data["items"] = [{}]
        self.item_data = self.current_data["items"][0]

        # 状態保持用
        self.post_rows = {}
        self.sku_groups = []
        self.sku_map = {}
        self.common_info = {}
        self.selected_vars = {}
        self.wrap_labels = []
        self.url_entry_widgets = []

        # 2. UI構築
        self._create_widgets()

        # 3. サイズ調整とリサイズ許可
        self.adjust_to_content(width=950)
        self.resizable(True, True)

        # 最低サイズを設定してレイアウト崩れを防止
        self.update_idletasks()
        self.minsize(800, 500)

    def _create_widgets(self):
        # --- A. 下部ボタンエリア（最下部固定） ---
        bottom_f = ttk.Frame(self, padding="15")
        bottom_f.pack(side="bottom", fill="x")

        ttk.Separator(bottom_f, orient="horizontal").pack(fill="x", pady=(0, 15))

        btn_row = ttk.Frame(bottom_f)
        btn_row.pack(side="right")

        ttk.Button(btn_row, text="キャンセル", width=15, command=self.close_dialog).pack(side="left", padx=5)
        ttk.Button(btn_row, text="保存", width=15, command=self._save).pack(side="left", padx=5)

        # --- B. スクロール可能なメインエリア ---
        self.scroll_f = self.create_scrollable_container()

        # --- 1. 楽天共通設定 ---
        common_f = ttk.LabelFrame(self.scroll_f, text=" 楽天共通設定 ", padding="10")
        common_f.pack(fill="x", pady=(5, 5), padx=15)

        toggle_row = ttk.Frame(common_f)
        toggle_row.pack(anchor="e", pady=(0, 5))
        ttk.Label(toggle_row, text="編集許可 ").pack(side="left")

        self.edit_mode_var = tk.BooleanVar(value=False)
        self.edit_switch = ToggleButton(toggle_row, self.edit_mode_var, command=self._toggle_url_lock)
        self.edit_switch.pack(side="left")

        configs = [("楽天TOP URL:", "top_url"), ("ログインURL:", "login_url"),
                   ("POST先URL:", "post_url"), ("カートURL:", "cart_url")]

        for label, key in configs:
            ttk.Label(common_f, text=label).pack(anchor="w")
            var = tk.StringVar(value=self.current_data["common"].get(key, ""))
            setattr(self, f"{key}_var", var)
            ent = tk.Entry(common_f, textvariable=var, state="readonly", readonlybackground="#f0f0f0", font=("", 10))
            ent.pack(fill="x", pady=(0, 8), ipady=3)
            self.url_entry_widgets.append(ent)

        # --- 2. 基本注文設定 ---
        base_f = ttk.LabelFrame(self.scroll_f, text=" 基本注文設定 ", padding="10")
        base_f.pack(fill="x", pady=5, padx=15)
        ttk.Label(base_f, text="商品URL:").pack(anchor="w")

        url_row = ttk.Frame(base_f)
        url_row.pack(fill="x", pady=(0, 5))

        self.url_var = tk.StringVar(value=self.item_data.get("item_url", ""))
        # UIロック用に参照保持
        self.url_entry = ttk.Entry(url_row, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=3)

        self.analyze_btn = ttk.Button(url_row, text="解析実行", width=12, command=self._start_load_thread)
        self.analyze_btn.pack(side="right", padx=5)

        # --- 3. 解析結果 ---
        self.analysis_main_f = ttk.LabelFrame(self.scroll_f, text=" 解析結果の選択 ", padding="10")
        self.analysis_main_f.pack(fill="x", pady=5, padx=15)
        self.status_var = tk.StringVar(value="URLを入力して「解析実行」を押してください")
        ttk.Label(self.analysis_main_f, textvariable=self.status_var, foreground="blue").pack(anchor="w")

        self.dynamic_container = ttk.Frame(self.analysis_main_f)
        self.dynamic_container.pack(fill="x")

        # --- 4. 登録済みPOSTセット ---
        self.kw_main_f = ttk.LabelFrame(self.scroll_f, text=" 登録済みPOSTセット (購入対象) ", padding="10")
        self.kw_main_f.pack(fill="x", pady=5, padx=15)
        self.kw_list_f = ttk.Frame(self.kw_main_f)
        self.kw_list_f.pack(fill="x")

        for kw in self.item_data.get("required_keywords", []):
            self._add_post_row_from_string(kw)

    def _toggle_url_lock(self):
        is_edit = self.edit_mode_var.get()
        state = "normal" if is_edit else "readonly"
        for ent in self.url_entry_widgets:
            ent.config(state=state, bg="#ffffff" if is_edit else "#f0f0f0")

    def _start_load_thread(self):
        url = self.url_var.get().strip()
        if not url: return

        # UIロック：解析中はボタンと入力を無効化
        self.status_var.set("⏳ 解析中（ヘッドレスブラウザ起動中）...")
        self.analyze_btn.config(state="disabled")
        self.url_entry.config(state="disabled")

        threading.Thread(target=self._load_task, args=(url,), daemon=True).start()

    def _load_task(self, url):
        try:
            # 解析実行（ヘッドレス）
            data = self.logic.fetch_item_variants(url)
            # 解析完了後に即座にブラウザを破棄
            self.logic.close()

            self.after(0, lambda: self._on_load_success(data))
        except Exception as err:
            self.logic.close()
            self.after(0, lambda e=err: self._on_load_error(e))

    def _on_load_success(self, data):
        self.analyze_btn.config(state="normal")
        self.url_entry.config(state="normal")
        self._reflect_variants(data)

    def _on_load_error(self, err):
        self.analyze_btn.config(state="normal")
        self.url_entry.config(state="normal")
        self.status_var.set(f"❌ 失敗: {err}")

    def _reflect_variants(self, data):
        for child in self.dynamic_container.winfo_children():
            child.destroy()
        self.wrap_labels = []
        self.sku_groups = data.get('groups', [])
        self.sku_map = data.get('skuMap', {})
        self.common_info = data.get('common', {})
        self.selected_vars = {}

        f_name = ttk.LabelFrame(self.dynamic_container, text=" 商品名 ", padding=10)
        f_name.pack(fill="x", pady=5, padx=5)
        item_title = self.common_info.get('title', '商品名が取得できませんでした')
        lbl_name = tk.Label(f_name, text=item_title, font=("", 10, "bold"), anchor="w", justify="left", wraplength=850)
        lbl_name.pack(fill="x", padx=5)
        self.wrap_labels.append(lbl_name)

        f_var = ttk.LabelFrame(self.dynamic_container, text=" 商品バリエーション ", padding=10)
        f_var.pack(fill="x", pady=5, padx=5)

        sku_gs = [g for g in self.sku_groups if g.get('type') == 'sku']
        if not sku_gs:
            ttk.Label(f_var, text="※この商品はオプション選択がありません。", foreground="blue").pack(anchor="w", padx=5)
        else:
            for g in sku_gs:
                self._create_combo_item(f_var, g)

        qty_row = ttk.Frame(f_var)
        qty_row.pack(fill="x", pady=(10, 5), padx=5)
        ttk.Label(qty_row, text="購入数量:").pack(side="left")
        self.qty_var = tk.StringVar(value="1")
        ttk.Entry(qty_row, textvariable=self.qty_var, width=8).pack(side="left", padx=5)

        choice_gs = [g for g in self.sku_groups if g.get('type') == 'choice']
        if choice_gs:
            f_choice = ttk.LabelFrame(self.dynamic_container, text=" 確認事項（了承事項） ", padding=10)
            f_choice.pack(fill="x", pady=5, padx=5)
            for g in choice_gs:
                self._create_combo_item(f_choice, g)

        ttk.Button(self.dynamic_container, text="この構成で登録済みPOSTセットに追加",
                   command=self._add_selected_combination, width=45).pack(pady=15)
        self.adjust_to_content(width=950)
        self.status_var.set(f"✅ 解析完了: {len(self.sku_groups)} 項目")

    def _create_combo_item(self, parent, group):
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=5)
        lbl = tk.Label(f, text=group['name'], font=("", 9, "bold"), anchor="w", justify="left", wraplength=900)
        lbl.pack(fill="x", padx=5)
        self.wrap_labels.append(lbl)
        var = tk.StringVar()
        cb = ttk.Combobox(f, textvariable=var, state="readonly", font=("", 10))
        cb['values'] = group['options']
        if group['options']: cb.current(0)
        cb.pack(fill="x", padx=5, pady=5)
        self.selected_vars[group['id']] = var

    def _add_selected_combination(self):
        sku_vals = []
        choice_vals = []
        choice_pairs = []
        sku_gs = [g for g in self.sku_groups if g.get('type') == 'sku']
        for g in self.sku_groups:
            var = self.selected_vars.get(g['id'])
            if not var: continue
            val = var.get().strip()
            if not val: return
            if g.get('type') == 'sku':
                sku_vals.append(val)
            else:
                choice_vals.append(val)
                choice_pairs.append(f"{g['name']}:{val}")

        vid = None
        if sku_gs:
            key = ",".join(sku_vals)
            sku_info = self.sku_map.get(key)
            if sku_info:
                vid = sku_info.get('vid') if isinstance(sku_info, dict) else str(sku_info)
            else:
                vid = self.common_info.get('vid')

        clean_vid = str(vid) if vid else ""
        item_id = self.common_info.get('itemid', '')
        row_key = clean_vid if clean_vid else f"item_{item_id}"

        try:
            add_qty = int(self.qty_var.get())
        except:
            add_qty = 1

        if row_key in self.post_rows:
            current_qty = int(self.post_rows[row_key]["qty_var"].get())
            self.post_rows[row_key]["qty_var"].set(str(current_qty + add_qty))
        else:
            item_title = self.common_info.get('title', '単品商品')
            extra_parts = sku_vals + choice_vals
            detail_text = " ・ ".join(extra_parts).replace('\n', ' ') if extra_parts else ""
            display_text = f"{item_title} ({detail_text})" if detail_text else item_title

            choices_str = "||".join(choice_pairs)
            post_data = f"{clean_vid}|{choices_str}|{item_id}|{self.common_info.get('shopid', '')}"
            self._create_post_row_ui(row_key, display_text, post_data, add_qty)

        self.status_var.set(f"✅ セットを追加しました")
        self.adjust_to_content(width=950)

    def _create_post_row_ui(self, vid, display_text, post_data, qty):
        row = ttk.Frame(self.kw_list_f)
        row.pack(fill="x", pady=2)
        qty_var = tk.StringVar(value=str(qty))
        ctrl_f = ttk.Frame(row)
        ctrl_f.pack(side="right", padx=5)
        ttk.Button(ctrl_f, text="－", width=3, command=lambda v=vid: self._change_qty(v, -1)).pack(side="left")
        ttk.Entry(ctrl_f, textvariable=qty_var, width=5, justify="center").pack(side="left", padx=2)
        ttk.Button(ctrl_f, text="＋", width=3, command=lambda v=vid: self._change_qty(v, 1)).pack(side="left")
        ttk.Button(ctrl_f, text="×", width=3, command=lambda v=vid: self._remove_row(v)).pack(side="left", padx=5)

        lbl = tk.Label(row, text=display_text, font=("", 9), anchor="w", justify="left", wraplength=700)
        lbl.pack(side="left", padx=5, fill="x", expand=True)
        self.wrap_labels.append(lbl)
        self.post_rows[vid] = {"row_frame": row, "qty_var": qty_var, "display_text": display_text,
                               "post_data": post_data}

    def _change_qty(self, vid, delta):
        try:
            val = int(self.post_rows[vid]["qty_var"].get())
            self.post_rows[vid]["qty_var"].set(str(max(1, val + delta)))
        except:
            pass

    def _remove_row(self, vid):
        self.post_rows[vid]["row_frame"].destroy()
        del self.post_rows[vid]
        self.adjust_to_content(width=950)

    def _add_post_row_from_string(self, raw_str):
        if "###" in raw_str:
            parts = raw_str.split("###")
            if len(parts) == 3:
                qty, display, p_data = parts
                vid_part = p_data.split("|")[0]
                self._create_post_row_ui(vid_part if vid_part else f"init_{qty}", display, p_data, qty)

    def _save(self):
        self.current_data["common"].update({
            "top_url": self.top_url_var.get().strip(),
            "login_url": self.login_url_var.get().strip(),
            "post_url": self.post_url_var.get().strip(),
            "cart_url": self.cart_url_var.get().strip()
        })
        self.item_data["item_url"] = self.url_var.get().strip()
        self.item_data["required_keywords"] = [
            f"{r['qty_var'].get()}###{r['display_text']}###{r['post_data']}" for r in self.post_rows.values()
        ]
        if self.manager.save(self.current_data):
            messagebox.showinfo("保存", "設定を保存しました。")
            self.close_dialog()

    def close_dialog(self):
        # 閉じるときに確実にブラウザを破棄
        if hasattr(self, 'logic') and self.logic:
            self.logic.close()
        super().close_dialog()
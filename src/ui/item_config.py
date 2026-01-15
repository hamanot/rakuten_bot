import tkinter as tk
from tkinter import ttk, messagebox
import threading

# 新しいベースクラスをインポート
from ui.base_sub_dialog import BaseSubDialog
from component.item_manager import ItemManager
from bl.item_analysis_logic import ItemAnalysisLogic


class ItemConfigDialog(BaseSubDialog):
    def __init__(self, parent, debug_mode=True):
        # 1. BaseSubDialogの初期化
        super().__init__(parent, title="商品設定 - POSTパラメータ抽出モード", size=None)

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

        # 2. UI構築
        self._create_widgets()

        # 3. 初期表示時のサイズ調整
        self.adjust_to_content(width=950)

    def _create_widgets(self):
        # BaseDialogの機能でスクロール領域を作成
        self.scroll_f = self.create_scrollable_container()

        # --- 1. 楽天共通設定 ---
        common_f = ttk.LabelFrame(self.scroll_f, text=" 楽天共通設定 ", padding="10")
        common_f.pack(fill="x", pady=(5, 5), padx=15)

        for label, key in [("ログインURL:", "login_url"), ("POST先URL:", "post_url"), ("購入完了URL:", "complete_url")]:
            ttk.Label(common_f, text=label).pack(anchor="w")
            var = tk.StringVar(value=self.current_data["common"].get(key, ""))
            setattr(self, f"{key}_var", var)
            ttk.Entry(common_f, textvariable=var).pack(fill="x", pady=(0, 5))

        # --- 2. 基本注文設定 ---
        base_f = ttk.LabelFrame(self.scroll_f, text=" 基本注文設定 ", padding="10")
        base_f.pack(fill="x", pady=5, padx=15)
        ttk.Label(base_f, text="商品URL:").pack(anchor="w")
        url_row = ttk.Frame(base_f)
        url_row.pack(fill="x", pady=(0, 5))
        self.url_var = tk.StringVar(value=self.item_data.get("item_url", ""))
        ttk.Entry(url_row, textvariable=self.url_var).pack(side="left", fill="x", expand=True)
        ttk.Button(url_row, text="解析実行", width=12, command=self._start_load_thread).pack(side="right", padx=5)

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

        # 既存データの復元
        for kw in self.item_data.get("required_keywords", []):
            self._add_post_row_from_string(kw)

        # 保存/キャンセルボタン
        btn_area = ttk.Frame(self.scroll_f)
        btn_area.pack(pady=20)
        ttk.Button(btn_area, text="保存", width=15, command=self._save).pack(side="left", padx=10)
        ttk.Button(btn_area, text="キャンセル", width=15, command=self.close_dialog).pack(side="left", padx=10)

    def _reflect_variants(self, data):
        """解析結果を画面に反映（ここで動的にサイズが変わる）"""
        for child in self.dynamic_container.winfo_children():
            child.destroy()
        self.wrap_labels = []

        self.sku_groups = data.get('groups', [])
        self.sku_map = data.get('skuMap', {})
        self.common_info = data.get('common', {})
        self.selected_vars = {}

        if not self.sku_groups:
            ttk.Label(self.dynamic_container, text="❌ 項目が見つかりませんでした", foreground="red").pack(pady=10)
            self.adjust_to_content(width=950)
            return

        # SKU項目の生成
        sku_gs = [g for g in self.sku_groups if g.get('type') == 'sku']
        if sku_gs:
            f_sku = ttk.LabelFrame(self.dynamic_container, text=" 商品バリエーション ", padding=10)
            f_sku.pack(fill="x", pady=5, padx=5)
            for g in sku_gs:
                self._create_combo_item(f_sku, g)

            qty_row = ttk.Frame(f_sku)
            qty_row.pack(fill="x", pady=(10, 5), padx=5)
            ttk.Label(qty_row, text="購入数量:").pack(side="left")
            self.qty_var = tk.StringVar(value="1")
            ttk.Entry(qty_row, textvariable=self.qty_var, width=8).pack(side="left", padx=5)

        # 選択項目の生成
        choice_gs = [g for g in self.sku_groups if g.get('type') == 'choice']
        if choice_gs:
            f_choice = ttk.LabelFrame(self.dynamic_container, text=" 確認事項（了承事項） ", padding=10)
            f_choice.pack(fill="x", pady=5, padx=5)
            for g in choice_gs:
                self._create_combo_item(f_choice, g)

        ttk.Button(self.dynamic_container, text="この構成で登録済みPOSTセットに追加",
                   command=self._add_selected_combination, width=45).pack(pady=15)

        # 重要：動的に中身が増えたので、BaseDialogの機能でサイズを再調整する
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

        for g in self.sku_groups:
            val = self.selected_vars[g['id']].get().strip()
            if not val: return

            if g.get('type') == 'sku':
                sku_vals.append(val)
            else:
                choice_vals.append(val)
                choice_pairs.append(f"{g['name']}:{val}")

        key = ",".join(sku_vals)
        sku_info = self.sku_map.get(key)
        vid = sku_info.get('vid') if isinstance(sku_info, dict) else str(sku_info)

        if vid:
            try:
                add_qty = int(self.qty_var.get())
            except:
                add_qty = 1

            if vid in self.post_rows:
                current_qty = int(self.post_rows[vid]["qty_var"].get())
                self.post_rows[vid]["qty_var"].set(str(current_qty + add_qty))
            else:
                display_text = " ・ ".join(sku_vals + choice_vals).replace('\n', ' ')
                choices_str = "||".join(choice_pairs)
                post_data = f"{vid}|{choices_str}|{self.common_info.get('itemid', '')}|{self.common_info.get('shopid', '')}"
                self._create_post_row_ui(vid, display_text, post_data, add_qty)

            self.status_var.set(f"✅ セットを追加/更新しました")
            self.adjust_to_content(width=950)
        else:
            messagebox.showerror("エラー", "SKU IDの特定に失敗しました。")

    def _create_post_row_ui(self, vid, display_text, post_data, qty):
        row = ttk.Frame(self.kw_list_f)
        row.pack(fill="x", pady=2)
        qty_var = tk.StringVar(value=str(qty))

        lbl = tk.Label(row, text=display_text, font=("", 9), anchor="w", justify="left", wraplength=800)
        lbl.pack(side="left", padx=5, fill="x", expand=True)
        self.wrap_labels.append(lbl)

        ctrl_f = ttk.Frame(row)
        ctrl_f.pack(side="right")
        ttk.Button(ctrl_f, text="－", width=3, command=lambda: self._change_qty(vid, -1)).pack(side="left")
        ttk.Entry(ctrl_f, textvariable=qty_var, width=5, justify="center").pack(side="left", padx=2)
        ttk.Button(ctrl_f, text="＋", width=3, command=lambda: self._change_qty(vid, 1)).pack(side="left")
        ttk.Button(ctrl_f, text="×", width=3, command=lambda: self._remove_row(vid)).pack(side="left", padx=5)

        self.post_rows[vid] = {
            "row_frame": row,
            "qty_var": qty_var,
            "display_text": display_text,
            "post_data": post_data
        }

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
                vid = p_data.split("|")[0]
                self._create_post_row_ui(vid, display, p_data, qty)

    def _start_load_thread(self):
        url = self.url_var.get().strip()
        if not url: return
        self.status_var.set("⏳ 解析中...")
        threading.Thread(target=self._load_task, args=(url,), daemon=True).start()

    def _load_task(self, url):
        try:
            data = self.logic.fetch_item_variants(url)
            self.after(0, lambda: self._reflect_variants(data))
        except Exception as err:
            self.after(0, lambda e=err: self.status_var.set(f"❌ 失敗: {e}"))

    def _save(self):
        self.current_data["common"]["login_url"] = self.login_url_var.get().strip()
        self.current_data["common"]["post_url"] = self.post_url_var.get().strip()
        self.current_data["common"]["complete_url"] = self.complete_url_var.get().strip()
        self.item_data["item_url"] = self.url_var.get().strip()

        save_list = []
        for vid, row in self.post_rows.items():
            save_list.append(f"{row['qty_var'].get()}###{row['display_text']}###{row['post_data']}")
        self.item_data["required_keywords"] = save_list

        if self.manager.save(self.current_data):
            messagebox.showinfo("保存", "設定を保存しました。")
            self.close_dialog()

    def close_dialog(self):
        if hasattr(self, 'logic') and self.logic:
            self.logic.close()
        # BaseSubDialogの終了処理を呼ぶ
        super().close_dialog()
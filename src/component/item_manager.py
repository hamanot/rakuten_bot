import json
import os


class ItemManager:
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

        self.conf_dir = os.path.join(project_root, "conf")
        filename = "item_info_debug.json" if self.debug_mode else "item_info.json"
        self.file_path = os.path.join(self.conf_dir, filename)

        self.item_data = {
            "common": {"top_url": "", "login_url": "", "post_url": "", "cart_url": ""},
            "items": [{"item_url": "", "required_keywords": [], "actions": []}]
        }

    def load(self):
        if not os.path.exists(self.file_path):
            return self.item_data

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "common" not in data:
                data["common"] = self.item_data["common"]

            # 必須キーの補完 (cart_url を確実に含める)
            for k in ["top_url", "login_url", "post_url", "cart_url"]:
                if k not in data["common"]:
                    data["common"][k] = ""

            if "items" not in data or not data["items"]:
                data["items"] = self.item_data["items"]

            self.item_data = data
            return self.item_data
        except:
            return self.item_data

    def save(self, data):
        self.item_data = data
        try:
            if not os.path.exists(self.conf_dir):
                os.makedirs(self.conf_dir, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False

    def is_valid(self):
        data = self.load()
        c = data.get("common", {})
        items = data.get("items", [])
        i = items[0] if items else {}

        # cart_url を含む必須URLのチェック
        return all([
            c.get("top_url", "").strip(),
            c.get("login_url", "").strip(),
            c.get("cart_url", "").strip(),
            i.get("item_url", "").strip()
        ])


    def parse_sku_string(self, raw_val):
        """
        巨大なフルフル文字列を分解し、プログラムが直接利用可能なオブジェクトに変換する。

        Args:
            raw_val (str): パース対象のRAW文字列

        Returns:
            dict: {
                "quantity": str,          # 数量 (先頭の数字)
                "product_name": str,      # 商品名
                "variation_labels": list, # バリエーション名の配列 (「 ・ 」で分割)
                "sku_id": str,            # SKU管理番号 (存在しない場合は空文字)
                "choices": list,          # 選択事項の配列 (承諾事項:回答)
                "shop_id": str,           # 店舗ID (後ろから2番目)
                "item_id": str,           # 商品ID (最後尾)
                "raw": str                # オリジナル文字列
            }
        """
        try:
            # 1. ### で3分割 (数量 / 商品名(バリエ) / その他ID群)
            parts_hash = raw_val.split("###")
            quantity = parts_hash[0]
            full_name_var = parts_hash[1]
            remains = parts_hash[2]

            # 2. 商品名(バリエーション) のパース
            product_name = full_name_var
            variation_labels = []
            if "(" in full_name_var and full_name_var.endswith(")"):
                # 最後の ( で分割
                n_parts = full_name_var.rsplit("(", 1)
                product_name = n_parts[0].strip()
                # カッコ内の「 ・ 」区切りの文字列を配列にする
                var_content = n_parts[1].rstrip(")")
                variation_labels = [v.strip() for v in var_content.split(" ・ ") if v.strip()]

            # 3. ID・Choice群のパース (後ろから逆算)
            # パイプ「|」で分割
            parts_pipe = remains.split("|")

            # 確実にある後ろの2つを取得
            item_id = parts_pipe[-1]
            shop_id = parts_pipe[-2]

            # 4. sku_id と choices の切り分け
            # 前から見て最初の要素が sku_id 候補だが、承諾事項（:を含む）なら sku_id は空
            sku_id = ""
            choices = []

            # 残りの要素（前後を除いた中間部分）をループ
            middle_parts = parts_pipe[:-2]
            for i, p in enumerate(middle_parts):
                p = p.replace("||", "").strip()
                if not p: continue

                if i == 0 and "compass_sku" in p:
                    sku_id = p
                elif ":" in p:
                    choices.append(p)
                else:
                    # sku_id 形式ではないが最初の要素だった場合、一応保持
                    if i == 0 and not sku_id:
                        sku_id = p

            return {
                "quantity": quantity,
                "product_name": product_name,
                "variation_labels": variation_labels,
                "sku_id": sku_id,
                "choices": choices,
                "shop_id": shop_id,
                "item_id": item_id,
                "raw": raw_val
            }
        except Exception:
            # 失敗時は最低限表示が壊れない辞書を返す
            return {
                "quantity": "1",
                "product_name": "Parse Error",
                "variation_labels": [raw_val],
                "sku_id": "",
                "choices": [],
                "shop_id": "",
                "item_id": "",
                "raw": raw_val
            }

    def get_parsed_items(self):
        """
        JSONの全商品をパース済みオブジェクトのリストとして返す
        """
        data = self.load()
        parsed_list = []
        for idx, item in enumerate(data.get("items", [])):
            keywords = item.get("required_keywords", [])
            for k_idx, k in enumerate(keywords):
                res = self.parse_sku_string(k)
                res["id"] = f"item_{idx}_k{k_idx}"
                parsed_list.append(res)
        return parsed_list
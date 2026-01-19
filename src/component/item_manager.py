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
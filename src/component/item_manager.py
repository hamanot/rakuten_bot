import os
import json

class ItemManager:
    def __init__(self, conf_dir):
        self.conf_dir = conf_dir
        self.file_path = os.path.join(conf_dir, "item_info.json")
        self.default_data = {
            "common": {"top_url": "https://www.rakuten.co.jp/", "login_url": "https://login.rakuten.co.jp/rid/login/"},
            "items": [{"item_url": "", "details": [], "notes": []}]
        }

    def save(self, data):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def load(self):
        if not os.path.exists(self.file_path): return self.default_data
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "items" not in data: # 互換性維持
                    data = {"common": data.get("common", self.default_data["common"]), "items": [data.get("individual", {})]}
                return data
        except: return self.default_data

    def is_valid(self):
        data = self.load()
        items = data.get("items", [])
        return len(items) > 0 and bool(items[0].get("item_url"))
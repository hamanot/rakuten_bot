import os
import json
import base64
import hashlib
import uuid
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


class UserManager:
    def __init__(self, config_path=None):
        # パスの固定処理
        if config_path is None:
            # UserManager.py (src/component/) から見たプロジェクトルート (../..) を取得
            current_file_path = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
            self.config_path = os.path.join(project_root, "conf", "user_info.json")
        else:
            self.config_path = config_path

        # UI側が .get("rakuten_id") 等でアクセスするための辞書を必ず初期化
        self.user_data = {
            "rakuten_id": "",
            "rakuten_pw": "",
            "is_valid": False
        }

        # フォルダ作成（プロジェクト直下の conf を作成）
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        self.load()

    def is_valid(self):
        """top_menu.py (37行目) 用"""
        return self.user_data.get("is_valid", False)

    def get_info(self):
        """user_config.py 用"""
        return self.user_data

    def _get_mac_address(self):
        node = uuid.getnode()
        return ":".join(("%012X" % node)[i:i + 2] for i in range(0, 12, 2))

    def _get_cipher(self):
        try:
            mac = self._get_mac_address().encode("utf-8")
            salt = hashlib.sha256(mac).digest()[:16]
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(mac))
            return Fernet(key)
        except:
            return None

    def _encrypt(self, text):
        if not text: return ""
        try:
            cipher = self._get_cipher()
            if not cipher: return ""
            return cipher.encrypt(text.encode("utf-8")).decode("utf-8")
        except:
            return ""

    def _decrypt(self, encrypted_text):
        if not encrypted_text: return ""
        try:
            cipher = self._get_cipher()
            if not cipher: return ""
            return cipher.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
        except:
            return ""

    def save(self, data_dict):
        """UI側の self.manager.save(new_data) という呼び出しに適合"""
        rakuten_id = data_dict.get("rakuten_id", "").strip()
        rakuten_pw = data_dict.get("rakuten_pw", "").strip()

        try:
            save_dict = {
                "rakuten_id": self._encrypt(rakuten_id),
                "rakuten_pw": self._encrypt(rakuten_pw),
                "is_valid": True if (rakuten_id and rakuten_pw) else False
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(save_dict, f, indent=4)

            # 内部メモリを更新
            self.user_data["rakuten_id"] = rakuten_id
            self.user_data["rakuten_pw"] = rakuten_pw
            self.user_data["is_valid"] = save_dict["is_valid"]
            return True
        except:
            return False

    def load(self):
        """UI側の self.current_data = self.manager.load() に適合させるため辞書を返す"""
        if not os.path.exists(self.config_path):
            self.user_data["is_valid"] = False
            return self.user_data

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            raw_id = self._decrypt(data.get("rakuten_id", ""))
            raw_pw = self._decrypt(data.get("rakuten_pw", ""))

            self.user_data["rakuten_id"] = raw_id
            self.user_data["rakuten_pw"] = raw_pw
            self.user_data["is_valid"] = True if (raw_id and raw_pw) else False
        except:
            self.user_data["is_valid"] = False

        return self.user_data
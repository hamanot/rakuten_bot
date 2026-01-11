import os
import uuid
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class UserManager:
    def __init__(self, conf_dir):
        self.conf_dir = conf_dir
        self.file_path = os.path.join(conf_dir, "user_info.bin")
        self._key = self._generate_key()

    def _generate_key(self):
        mac = str(uuid.getnode())
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b'rakuten_bot', iterations=100000)
        return base64.urlsafe_b64encode(kdf.derive(mac.encode()))

    def save(self, user_id, password):
        f = Fernet(self._key)
        data = f"{user_id}:{password}".encode()
        with open(self.file_path, "wb") as file:
            file.write(f.encrypt(data))

    def load(self):
        if not os.path.exists(self.file_path): return None, None
        try:
            f = Fernet(self._key)
            with open(self.file_path, "rb") as file:
                decrypted = f.decrypt(file.read()).decode()
            return decrypted.split(":")
        except: return None, None

    def is_valid(self):
        u, p = self.load()
        return bool(u and p)
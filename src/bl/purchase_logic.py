import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from component.chrome_driver_manager import ChromeDriverManager
from component.user_manager import UserManager
from component.item_manager import ItemManager


class PurchaseLogic:
    _instance = None

    @classmethod
    def get_instance(cls, debug_mode=True):
        if cls._instance is None:
            cls._instance = cls(debug_mode)
        else:
            # 既にインスタンスがあっても、呼び出し時のモードを適用し、
            # 常に最新の設定ファイルを読み直す
            cls._instance.debug_mode = debug_mode
            cls._instance._load_config()
        return cls._instance

    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        self._load_config()

    def _load_config(self):
        """ItemManagerからモードに応じた最新の設定をロード。"""
        # ItemManager内部で正しいパス導出(3段階遡り)が行われている前提
        i_mgr = ItemManager(debug_mode=self.debug_mode)
        conf = i_mgr.load() or {}
        self.common = conf.get("common") or {}
        self.item = conf.get("items", [{}])[0]
        print(f"[CONFIG] {'DEBUG' if self.debug_mode else 'PRODUCTION'} 設定をロード完了")

    def is_logged_in(self):
        try:
            driver = ChromeDriverManager.get_driver(self.debug_mode)
            source = driver.page_source
            return "log-out" in source or "my-rakuten" in source
        except:
            return False

    def execute_login(self):
        driver = ChromeDriverManager.get_driver(self.debug_mode)
        top_url = self.common.get("top_url") or "https://www.rakuten.co.jp/"
        login_url = self.common.get("login_url")

        print(f"[LOGIN] ログイン状態確認中... (Mode: {self.debug_mode})")
        driver.get(top_url)

        if self.is_logged_in():
            print("[LOGIN] プロファイルによる自動ログイン成功")
            return True

        print("[LOGIN] 未ログインのため通常ログイン開始")
        if login_url:
            driver.get(login_url)

        user = UserManager().load()
        user_id = user.get("rakuten_id")
        user_pw = user.get("rakuten_pw")

        try:
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.ID, "loginInner_u")))
            driver.find_element(By.ID, "loginInner_u").send_keys(user_id)
            driver.find_element(By.ID, "loginInner_p").send_keys(user_pw)
            driver.find_element(By.NAME, "submit").click()

            for _ in range(300):
                if top_url in driver.current_url or self.is_logged_in():
                    print("[LOGIN] 成功。")
                    time.sleep(2)
                    return True
                time.sleep(1)
            return False
        except Exception as e:
            print(f"[ERROR] ログイン失敗: {e}")
            return False

    def execute_cart_post(self, kw_string):
        """fetchによるカート投入リクエスト"""
        try:
            driver = ChromeDriverManager.get_driver(self.debug_mode)

            parts = kw_string.split("###")
            if len(parts) < 3: return False
            qty, data_part = parts[0], parts[2]
            elements = [e.strip() for e in data_part.split("|")]

            # --- ここから修正 ---
            shopid, itemid = elements[-1], elements[-2]
            vid = elements[0]  # elements[0] が空文字 "" なら False 扱いになる
            choice_list = [c.strip() for c in "|".join(elements[1:-2]).split("||") if c.strip()]

            post_url = self.common.get("post_url")
            print(f"[CART_POST] リクエスト送信 (VID: {vid if vid else 'NONE'})")

            # JavaScriptはそのまま (空のキーを送らないように、payload側で制御する)
            script = """
            const postUrl = arguments[0];
            const payload = arguments[1];
            const formData = new URLSearchParams();
            for (const key in payload) {
                if (Array.isArray(payload[key])) {
                    payload[key].forEach(val => formData.append(key, val));
                } else {
                    formData.append(key, payload[key]);
                }
            }
            fetch(postUrl, {
                method: "POST",
                body: formData,
                mode: "no-cors",
                credentials: "include",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
                }
            });
            return true;
            """

            # --- ここで payload を動的に作成 ---
            payload = {
                "choice[]": choice_list,
                "units": qty,
                "itemid": itemid,
                "shopid": shopid,
                "device": "pc",
                "userid": "itempage",
                "response_encode": "utf8"
            }

            # vid が存在する場合（SKU商品）のみパラメータを追加する
            if vid:
                payload["variant_id"] = vid
            # --------------------

            driver.execute_script(script, post_url, payload)
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"[ERROR] execute_cart_post 失敗: {e}")
            return False

    def go_to_checkout(self):
        """設定ファイル(common.cart_url)を使用して遷移し、最速連打する。"""
        driver = ChromeDriverManager.get_driver(self.debug_mode)

        # --- 修正箇所: conf内の cart_url を使用。なければデフォルト値をセット ---
        target_url = self.common.get("cart_url") or "https://basket.step.rakuten.co.jp/rms/mall/bs/cartall/"

        fast_click_script = """
        (function() {
            const start = Date.now();
            const interval = setInterval(() => {
                if (window.self !== window.top) return;
                if (window.location.href.indexOf('cart') === -1) return;

                const buttons = Array.from(document.querySelectorAll('button, a, input'));
                const target = buttons.find(b => 
                    b.getAttribute('aria-label')?.includes('購入手続き') || 
                    b.innerText?.includes('購入手続き') ||
                    b.innerText?.includes('ご購入手続き')
                );

                if (target) {
                    target.click();
                    target.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                }
                if (Date.now() - start > 10000) clearInterval(interval);
            }, 10);
        })();
        """

        # Selenium 3.141.0 でも execute_cdp_cmd は利用可能
        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": fast_click_script})
        except Exception:
            # 万が一CDPコマンドが失敗した場合の予備
            print("[WARN] CDP injection failed. Falling back to standard script.")

        print(f"[PYTHON] 買い物かご({target_url})へ遷移中...")
        driver.execute_script(f"window.location.href = '{target_url}';")
        return True
import os
import time
import json
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from component.chrome_driver_manager import ChromeDriverManager
from component.user_manager import UserManager
from component.item_manager import ItemManager

class PurchaseLogic:
    _instance = None
    _active_script_id = None

    @classmethod
    def get_instance(cls, debug_mode=True):
        if cls._instance is None:
            cls._instance = cls(debug_mode)
        else:
            cls._instance.debug_mode = debug_mode
            cls._instance._load_config()
        return cls._instance

    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        self._load_config()

    def _load_config(self):
        i_mgr = ItemManager(debug_mode=self.debug_mode)
        conf = i_mgr.load() or {}
        self.common = conf.get("common") or {}
        # itemsの0番目は念のため保持
        items = conf.get("items", [{}])
        self.item = items[0] if items else {}
        print(f"[CONFIG] {'DEBUG' if self.debug_mode else 'PRODUCTION'} 設定をロード完了")

    def _cleanup_script(self):
        if PurchaseLogic._active_script_id:
            try:
                driver = ChromeDriverManager.get_driver(self.debug_mode)
                driver.execute_cdp_cmd("Page.removeScriptToEvaluateOnNewDocument",
                                       {"identifier": PurchaseLogic._active_script_id})
                print(f"[CLEANUP] CDP Script Removed: {PurchaseLogic._active_script_id}")
                PurchaseLogic._active_script_id = None
            except Exception as e:
                print(f"[WARN] Failed to remove CDP script: {e}")

    def navigate_to(self, url):
        self._cleanup_script()
        driver = ChromeDriverManager.get_driver(self.debug_mode)
        driver.get(url)

    def is_logged_in(self):
        try:
            driver = ChromeDriverManager.get_driver(self.debug_mode)
            source = driver.page_source
            return "log-out" in source or "my-rakuten" in source
        except:
            return False

    def execute_login(self):
        self._cleanup_script()
        driver = ChromeDriverManager.get_driver(self.debug_mode)
        top_url = self.common.get("top_url") or "https://www.rakuten.co.jp/"
        login_url = self.common.get("login_url")

        print(f"[LOGIN] ログイン状態確認中... (Mode: {self.debug_mode})")
        driver.get(top_url)

        if self.is_logged_in():
            print("[LOGIN] プロファイルによる自動ログイン成功")
            return True

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
        """5秒間 全力リトライPOST"""
        self._cleanup_script()
        try:
            driver = ChromeDriverManager.get_driver(self.debug_mode)
            parts = kw_string.split("###")
            if len(parts) < 3: return False
            qty, data_part = parts[0], parts[2]
            elements = [e.strip() for e in data_part.split("|")]
            shopid, itemid, vid = elements[-1], elements[-2], elements[0]
            choice_list = [c.strip() for c in "|".join(elements[1:-2]).split("||") if c.strip()]
            post_url = self.common.get("post_url")

            payload = {"choice[]": choice_list, "units": qty, "itemid": itemid, "shopid": shopid,
                       "device": "pc", "userid": "itempage", "response_encode": "utf8"}
            if vid: payload["variant_id"] = vid

            script = """
            const postUrl = arguments[0];
            const payload = arguments[1];
            const callback = arguments[arguments.length - 1];
            const startTime = Date.now();
            const timeout = 5000; 

            const sendRequest = () => {
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
                    headers: {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}
                })
                .then(() => callback(true))
                .catch(() => {
                    if (Date.now() - startTime < timeout) {
                        setTimeout(sendRequest, 250); 
                    } else {
                        callback(false); 
                    }
                });
            };
            sendRequest();
            """
            driver.set_script_timeout(10)
            return driver.execute_async_script(script, post_url, payload)
        except Exception as e:
            print(f"[ERROR] execute_cart_post 失敗: {e}")
            return False

    def go_to_checkout(self):
        """混雑検知リロード ＋ 自動連鎖クリック"""
        driver = ChromeDriverManager.get_driver(self.debug_mode)
        target_url = self.common.get("cart_url") or "https://basket.step.rakuten.co.jp/rms/mall/bs/cartall/"

        targets = ["ご購入手続き", "購入手続き"]
        if not self.debug_mode:
            targets.extend(["注文を確定する", "注文を確定"])
            print("[PYTHON] 本番モード：注文確定まで連鎖します。")
        else:
            print("[PYTHON] デバッグモード：注文確定は押しません。")

        targets_json = json.dumps(targets, ensure_ascii=False)
        fast_chain_script = """
        (function() {
            const start = Date.now();
            const targets = """ + targets_json + """;
            const errKws = ["混み合って", "アクセスが集中", "システムエラー", "時間をおいて"];

            const interval = setInterval(() => {
                if (window.self !== window.top) return;

                const txt = document.body.innerText || "";
                // 混雑検知（2つ以上キーワードがヒットしたらリロード）
                if (errKws.filter(k => txt.includes(k)).length >= 2) {
                    console.log("[JS] 混雑検知 -> 自動リロード");
                    location.reload();
                    return;
                }

                const elements = Array.from(document.querySelectorAll('button, a, input, div[role="button"]'));
                const target = elements.find(el => {
                    const t = (el.innerText || el.value || el.getAttribute('aria-label') || "").replace(/\\s/g, "");
                    return targets.some(k => t.includes(k));
                });

                if (target) {
                    console.log("[JS] Target found:", target);
                    target.click();
                    target.dispatchEvent(new MouseEvent('click', {bubbles: true, view: window}));
                }

                if (Date.now() - start > 60000) clearInterval(interval);
            }, 100);
        })();
        """

        try:
            self._cleanup_script()
            res = driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": fast_chain_script})
            PurchaseLogic._active_script_id = res.get("identifier")
            print(f"[REGISTER] CDP Script ID: {PurchaseLogic._active_script_id}")
        except Exception as e:
            print(f"[WARN] CDP injection failed: {e}")

        # --- 移動リトライ処理 (502等対策) ---
        print(f"[PYTHON] 買い物かごへ移動します: {target_url}")
        for i in range(5):
            try:
                driver.get(target_url)
                break
            except Exception as e:
                print(f"[RETRY] ページ移動失敗 ({i+1}/5): {e}")
                time.sleep(0.5)

        return True

    def quit_browser(self):
        """ブラウザを終了してマネージャーをリセット"""
        self._cleanup_script()
        from component.chrome_driver_manager import ChromeDriverManager
        ChromeDriverManager.quit_driver()
        print("[BROWSER] Driver closed.")
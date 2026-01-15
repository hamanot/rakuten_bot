import os
import pickle
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from component.user_manager import UserManager
from component.item_manager import ItemManager


class PurchaseLogic:
    def __init__(self, driver, debug_mode=True):
        self.driver = driver
        self.debug_mode = debug_mode
        i_mgr = ItemManager(debug_mode=self.debug_mode)
        conf = i_mgr.load()
        self.common = conf.get("common", {})
        self.item = conf.get("items", [{}])[0]

        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(current_file))
        self.cookie_path = os.path.join(project_root, "conf", "cookies_debug.pkl" if debug_mode else "cookies.pkl")

    # --- ログイン・クッキー関連 ---
    def load_cookies(self):
        if os.path.exists(self.cookie_path):
            try:
                with open(self.cookie_path, "rb") as f:
                    cookies = pickle.load(f)
                    for cookie in cookies:
                        self.driver.add_cookie(cookie)
                return True
            except:
                return False
        return False

    def save_cookies(self):
        try:
            os.makedirs(os.path.dirname(self.cookie_path), exist_ok=True)
            with open(self.cookie_path, "wb") as f:
                pickle.dump(self.driver.get_cookies(), f)
            return True
        except:
            return False

    def is_logged_in(self):
        return "log-out" in self.driver.page_source or "my-rakuten" in self.driver.page_source

    def execute_login(self):
        login_url = self.common.get("login_url")
        if login_url:
            self.driver.get(login_url)

        user_mgr = UserManager()
        user = user_mgr.load()
        user_id = user.get("rakuten_id")
        user_pw = user.get("rakuten_pw")

        if not user_id or not user_pw:
            print("IDまたはパスワードが設定されていません")
            return False

        try:
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.ID, "loginInner_u")))
            self.driver.find_element_by_id("loginInner_u").send_keys(user_id)
            self.driver.find_element_by_id("loginInner_p").send_keys(user_pw)
            self.driver.find_element_by_name("submit").click()
            print("ログインを実行しました。")
            return True
        except Exception as e:
            print("ログイン失敗:", e)
            return False

    # --- 商品選択・購入操作関連 ---
    def select_required_options(self, keywords):
        """必須項目の選択。一つでも実行したらTrueを返す"""
        success = False
        try:
            for sel in self.driver.find_elements_by_tag_name("select"):
                obj = Select(sel)
                for opt in obj.options:
                    for kw in keywords:
                        if kw in opt.text:
                            obj.select_by_visible_text(opt.text)
                            success = True
                            break
        except:
            pass
        return success

    def execute_action_set(self, action_set):
        """
        全アクションを実行する前に、前回のトーストを跡形もなく消す
        """
        # 前回のトースト、背景のオーバーレイ、モーダルをすべて削除
        self.driver.execute_script("""
            const junk = [
                '.cart-common-toast', 
                '.action-feedback', 
                '[role="alert"]', 
                '.modal-backdrop', 
                '.overlay'
            ];
            junk.forEach(s => {
                document.querySelectorAll(s).forEach(el => el.remove());
            });
            // 念のためbodyのoverflow制限（スクロール不可状態）も解除
            document.body.style.overflow = 'auto';
        """)

        try:
            for action in action_set:
                n, k = action.get("target_name"), action.get("keyword")
                if not n or not k: continue
                if "数量" in n or "個数" in n:
                    self._set_quantity(n, k)
                else:
                    self._select_by_label_and_keyword(n, k)
            return True
        except Exception as e:
            print(f"DEBUG: セット実行エラー: {e}")
            return False

    def _set_quantity(self, label, val):
        try:
            xpath = "//*[contains(text(),'{}')]/following::input[1]".format(label)
            el = self.driver.find_element_by_xpath(xpath)
            el.clear()
            el.send_keys(str(val))
            return True
        except:
            return False

    def _select_by_label_and_keyword(self, label, kw):
        sku_button_xpaths = [
            "//button[@aria-label='{}']".format(kw),
            "//button[contains(@aria-label, '{}')]".format(kw),
            "//button//span[contains(text(), '{}')]".format(kw),
            "//button//div[contains(text(), '{}')]".format(kw)
        ]

        for xpath in sku_button_xpaths:
            try:
                el = self.driver.find_element_by_xpath(xpath)
                # スクロールさせずにJSでクリック（トーストが消えていれば貫通する）
                self.driver.execute_script("arguments[0].click();", el)
                return True
            except:
                continue
        return False

    def add_to_cart(self):
        # 本体ボタン(size-m)に絞る
        xpath = "//button[@aria-label='かごに追加' and contains(@class, 'size-m')]"

        try:
            # 1. カゴ入れボタンを見つける
            btn = self.driver.find_element(By.XPATH, xpath)

            # 2. ボタンが「押せる状態」になるまで最大2秒だけ待つ（実際にはコンマ数秒で終わる）
            # disabled属性が消えるのを待つ
            WebDriverWait(self.driver, 2).until(
                lambda d: btn.is_enabled() and "disabled" not in btn.get_attribute("class")
            )

            # 3. 物理クリックではなくJSで「通信を直接発火」させる
            self.driver.execute_script("arguments[0].click();", btn)
            print("DEBUG: カゴ入れ成功")

            # ★ ここでトーストを消す代わりに、通信が完了するまで「最小限」だけ待機
            # 楽天のサーバーが「次を受けていいよ」となるためのインターバル
            time.sleep(0.3)
            return True
        except:
            print("DEBUG: ボタンが準備完了になりませんでした")
            return False

    def _backup_add_to_cart(self):
        # バックアップも同様にスクロールなしJS実行
        try:
            btn = self.driver.find_element_by_xpath("//button[@aria-label='かごに追加']")
            self.driver.execute_script("arguments[0].click();", btn)
            return True
        except:
            return False

    def go_to_checkout(self, url=None):
        target_url = url if url else self.common.get("cart_url")
        if target_url:
            self.driver.get(target_url)
            return True
        return False
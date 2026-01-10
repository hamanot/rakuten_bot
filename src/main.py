import os
import pickle
import time
import uuid
import base64
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException, NoAlertPresentException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tkinter as tk
from tkinter import simpledialog
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# ================= 構成設定 =================
DEBUG_MODE = True  # 【デバッグ時: True / 本番: False】
TARGET_URL = "https://item.rakuten.co.jp/goodgoods-center/3dsuru/"  # デバッグしたい商品URL

base_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(base_dir)
DRIVER_PATH = os.path.join(project_root, "bin", "chromedriver.exe")
CONF_DIR = os.path.join(project_root, "conf")
COOKIE_FILE = os.path.join(CONF_DIR, "cookies.pkl")
USER_INFO_FILE = os.path.join(CONF_DIR, "user_info.bin")

if not os.path.exists(CONF_DIR):
    os.makedirs(CONF_DIR)


# ================= 関数定義 =================

def setup_driver():
    """
    Selenium WebDriverの初期化とBot検知回避設定を行う。

    Returns:
        webdriver.Chrome: 設定済みのChromeドライバインスタンス
    """
    options = webdriver.ChromeOptions()
    options.add_experimental_option('w3c', True)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(executable_path=DRIVER_PATH, options=options)

    # navigator.webdriverフラグを消去
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


def save_cookies(driver):
    """
    現在のブラウザセッションからCookieを取得し、ファイルに保存する。
    """
    with open(COOKIE_FILE, "wb") as f:
        pickle.dump(driver.get_cookies(), f)
    print(f">> Cookieを保存しました: {COOKIE_FILE}")


def load_cookies(driver):
    """
    保存済みのCookieファイルを読み込み、ブラウザに適用する。
    """
    if os.path.exists(COOKIE_FILE):
        driver.get('https://www.rakuten.co.jp/')
        with open(COOKIE_FILE, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    print(f"Cookie設定エラー: {e}")
        print(f">> {COOKIE_FILE} からCookieを読み込みました。")
    else:
        print(">> Cookieファイルが見つかりません。")
        driver.get('https://www.rakuten.co.jp/')


def get_mac_key():
    """MACアドレスベースの暗号化キー生成"""
    mac = str(uuid.getnode())
    salt = b'rakuten_bot_salt'
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    return base64.urlsafe_b64encode(kdf.derive(mac.encode()))


def get_user_input():
    """GUIダイアログでID/PASS取得"""
    root = tk.Tk()
    root.withdraw()
    user_id = simpledialog.askstring("設定", "楽天ユーザーIDを入力してください")
    if not user_id: return None, None
    password = simpledialog.askstring("設定", "楽天パスワードを入力してください", show='*')
    return user_id, password


def save_user_info(user_id, password):
    """ユーザー情報を暗号化保存"""
    key = get_mac_key()
    f = Fernet(key)
    data = f"{user_id}:{password}".encode()
    with open(USER_INFO_FILE, "wb") as file:
        file.write(f.encrypt(data))


def load_user_info():
    """ユーザー情報を復号取得。失敗時は入力を促す"""
    key = get_mac_key()
    f = Fernet(key)
    if os.path.exists(USER_INFO_FILE):
        try:
            with open(USER_INFO_FILE, "rb") as file:
                data = f.decrypt(file.read()).decode()
            return data.split(":")
        except Exception:
            print(">> 復号失敗。再設定します。")

    u, p = get_user_input()
    if u and p:
        save_user_info(u, p)
        return u, p
    return None, None


def is_logged_in(driver):
    """ログイン状態の判定"""
    try:
        xpath = "//a[@aria-label='ログイン' or contains(., 'ログイン')]"
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath)))
        return False
    except TimeoutException:
        return True


def perform_login(driver, user_id, password):
    """ログインページでのログイン実行"""
    print(">> ログイン実行中...")
    driver.get("https://grp01.id.rakuten.co.jp/rms/nid/vc?__event=login&service_id=top")
    try:
        wait = WebDriverWait(driver, 10)
        u_input = wait.until(EC.presence_of_element_located((By.ID, "loginInner_u")))
        u_input.send_keys(user_id)
        p_input = driver.find_element(By.ID, "loginInner_p")
        p_input.send_keys(password + Keys.RETURN)
        time.sleep(5)
        driver.get("https://www.rakuten.co.jp/")
        if is_logged_in(driver):
            save_cookies(driver)
            return True
        return False
    except Exception as e:
        print(f">> ログインエラー: {e}")
        return False


def check_for_option_alert(driver):
    """
    未選択によるアラートポップアップが出ているか確認し、あれば閉じる。

    Returns:
        bool: アラートがあった場合はTrue、なければFalse
    """
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        print(f">> [警告ポップアップ] {alert_text}")
        alert.accept()
        return True
    except NoAlertPresentException:
        return False


def main():
    """
    メイン実行フロー。
    DEBUG_MODE に応じてログインを制御する。
    """
    driver = None
    try:
        # 1. ユーザー情報準備
        user_id, password = load_user_info()
        if not user_id: return False

        # 2. ブラウザ起動
        driver = setup_driver()

        # 3. ログイン分岐
        if DEBUG_MODE:
            print(">> [DEBUG MODE] ログインをスキップして商品ページへ。")
            driver.get(TARGET_URL)
        else:
            load_cookies(driver)
            driver.refresh()
            if not is_logged_in(driver):
                if not perform_login(driver, user_id, password):
                    print(">> ログイン失敗。")
                    return False
            driver.get(TARGET_URL)

        # 4. 商品ページ解析（デバッグポイント）
        print(f">> 解析対象: {driver.title}")

        # --- ここにカート追加ボタンのクリックや選択肢操作を記述 ---
        # 動作確認例：
        # if check_for_option_alert(driver):
        #     print(">> 選択項目が不足しています。")

        if DEBUG_MODE:
            input(">> [DEBUG] 画面を確認してください。Enterで終了します...")
        else:
            time.sleep(5)

        return True

    except Exception as e:
        print(f">> エラー発生: {e}")
        return False
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
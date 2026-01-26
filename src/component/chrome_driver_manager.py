import os
from selenium import webdriver
from selenium.common.exceptions import WebDriverException


class ChromeDriverManager:
    _instance = None
    _current_mode = None  # デバッグ(True) / 本番(False)
    _current_headless = None  # ヘッドレス(True) / 通常(False)

    @classmethod
    def get_driver(cls, is_debug_mode=True, is_headless=False):
        """
        ドライバーを取得する。
        モード（デバッグ/本番）または表示設定（通常/ヘッドレス）が変更された場合は再起動する。
        """
        if cls._instance:
            try:
                # ブラウザの生存確認
                _ = cls._instance.window_handles

                # モード変更、またはヘッドレス設定の変更を検知したら再起動
                change_mode = cls._current_mode != is_debug_mode
                change_headless = cls._current_headless != is_headless

                if change_mode or change_headless:
                    reason = "モード変更" if change_mode else "ヘッドレス切替"
                    print(f"[CHANGE] {reason}を検知。ブラウザを再起動します。")
                    cls.quit_driver()
                else:
                    return cls._instance
            except:
                cls._instance = None

        if cls._instance is None:
            cls._current_mode = is_debug_mode
            cls._current_headless = is_headless
            cls._instance = cls._create_driver(is_debug_mode, is_headless)
        return cls._instance

    @classmethod
    def _create_driver(cls, is_debug_mode, is_headless):
        # --- ディレクトリ構造の解析 ---
        current_file = os.path.abspath(__file__)
        comp_dir = os.path.dirname(current_file)
        src_dir = os.path.dirname(comp_dir)
        project_root = os.path.dirname(src_dir)

        driver_path = os.path.join(project_root, "bin", "chromedriver.exe")
        base_dir = os.path.join(project_root, "conf", "user_profiles")
        folder = "debug_user" if is_debug_mode else "production_user"
        profile_path = os.path.join(base_dir, folder)

        if not os.path.exists(profile_path):
            os.makedirs(profile_path)

        # --- Selenium 3.141.0 用の設定 ---
        options = webdriver.ChromeOptions()

        # ヘッドレスモードの設定
        if is_headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')  # Windows環境でのヘッドレス安定化
            options.add_argument('--window-size=1920,1080')  # ヘッドレス時の要素判定漏れ防止

        # プロファイルディレクトリを指定
        options.add_argument(f'--user-data-dir={profile_path}')
        options.add_argument("--profile-directory=Default")

        # 自動操作検知回避
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        print(f"--- BROWSER LAUNCH ---")
        print(f"HEADLESS: {is_headless}")
        print(f"MODE    : {'DEBUG' if is_debug_mode else 'PRODUCTION'}")
        print(f"PROFILE : {profile_path}")

        # Selenium 3.141.0 では executable_path が必須
        driver = webdriver.Chrome(executable_path=driver_path, options=options)

        # navigator.webdriver 回避
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        return driver

    @classmethod
    def quit_driver(cls):
        """ブラウザを終了し、インスタンスを破棄する"""
        if cls._instance:
            try:
                cls._instance.quit()
            except:
                pass
            cls._instance = None
            cls._current_mode = None
            cls._current_headless = None
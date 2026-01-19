import os
from selenium import webdriver
from selenium.common.exceptions import WebDriverException


class ChromeDriverManager:
    _instance = None
    _current_mode = None

    @classmethod
    def get_driver(cls, is_debug_mode=True):
        if cls._instance:
            try:
                # ブラウザの生存確認
                _ = cls._instance.window_handles
                # モード（デバッグ/本番）が切り替わっていたら再起動
                if cls._current_mode != is_debug_mode:
                    print(f"[CHANGE] モード変更を検知。ブラウザを再起動します。")
                    cls.quit_driver()
                else:
                    return cls._instance
            except:
                cls._instance = None

        if cls._instance is None:
            cls._current_mode = is_debug_mode
            cls._instance = cls._create_driver(is_debug_mode)
        return cls._instance

    @classmethod
    def _create_driver(cls, is_debug_mode):
        # --- ディレクトリ構造の解析 (Python 3.12.3) ---
        # ファイル: rakuten_bot/src/component/chrome_driver_manager.py
        current_file = os.path.abspath(__file__)
        comp_dir = os.path.dirname(current_file)  # rakuten_bot/src/component
        src_dir = os.path.dirname(comp_dir)  # rakuten_bot/src
        project_root = os.path.dirname(src_dir)  # rakuten_bot (ルート)

        # ルート直下の各ディレクトリへのパス
        driver_path = os.path.join(project_root, "bin", "chromedriver.exe")

        base_dir = os.path.join(project_root, "conf", "user_profiles")
        folder = "debug_user" if is_debug_mode else "production_user"
        profile_path = os.path.join(base_dir, folder)

        # プロファイル用ディレクトリの作成
        if not os.path.exists(profile_path):
            os.makedirs(profile_path)

        # --- Selenium 3.141.0 用の設定 ---
        options = webdriver.ChromeOptions()
        # プロファイルディレクトリを指定
        options.add_argument(f'--user-data-dir={profile_path}')
        options.add_argument("--profile-directory=Default")

        # 自動操作検知回避
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        print(f"--- BROWSER LAUNCH ---")
        print(f"PYTHON  : 3.12.3")
        print(f"SELENIUM: 3.141.0")
        print(f"ROOT    : {project_root}")
        print(f"DRIVER  : {driver_path}")
        print(f"PROFILE : {profile_path}")

        # Selenium 3.141.0 では executable_path 引数が必須です
        driver = webdriver.Chrome(executable_path=driver_path, options=options)

        # navigator.webdriver を undefined に書き換えて検知を回避
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        return driver

    @classmethod
    def quit_driver(cls):
        if cls._instance:
            try:
                cls._instance.quit()
            except:
                pass
            cls._instance = None
            cls._current_mode = None
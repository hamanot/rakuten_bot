import sys, os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from ui.top_menu import TopMenu
from bl.purchase_logic import PurchaseLogic
from ui.debug_controller import DebugController


def main():
    # 1. 初期メニュー起動
    menu = TopMenu()
    menu.mainloop()
    if not menu.result["is_start"]: return

    is_debug = menu.result["debug_mode"].get()

    # 2. パス計算 (rakuten_bot/bin/chromedriver.exe)
    current_file = os.path.abspath(__file__)
    src_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(src_dir)
    driver_path = os.path.join(project_root, "bin", "chromedriver.exe")

    if not os.path.exists(driver_path):
        import tkinter.messagebox as mb
        mb.showerror("エラー", f"ChromeDriverが見つかりません:\n{driver_path}")
        return

    # 3. ブラウザ設定（おまじない）
    options = Options()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--lang=ja-JP')

    try:
        driver = webdriver.Chrome(executable_path=driver_path, options=options)
    except TypeError:
        from selenium.webdriver.chrome.service import Service
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=options)

    # navigator.webdriver隠蔽
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    try:
        # 4. ロジック初期化 (設定読み込みは Logic 内部で行われる)
        logic = PurchaseLogic(driver, debug_mode=is_debug)

        # 商品ページへ
        driver.get(logic.item.get("item_url"))

        if not is_debug:
            # --- 本番モード ---
            logic.load_cookies()
            driver.refresh()

            if not logic.is_logged_in():
                # execute_login 内部で login_url への get を行う
                logic.execute_login()

            actions = logic.item.get("actions", [])
            for i, a_set in enumerate(actions):
                logic.select_required_options(logic.item.get("required_keywords", []))
                logic.execute_action_set(a_set)
                logic.add_to_cart()
                if i < len(actions) - 1:
                    driver.get(logic.item.get("item_url"))

            logic.go_to_checkout()
        else:
            # --- デバッグモード ---
            # コントローラー起動
            ctrl = DebugController(driver, logic, logic.item)
            # 新しいメインウィンドウとしてイベントループを開始する
            ctrl.mainloop()

    except Exception as e:
        print(f"実行エラー: {e}")

    finally:
        # ★ ここを追加：プログラムが終わる時に必ずブラウザを閉じる
        if 'driver' in locals():
            print("ブラウザを終了します...")
            driver.quit()


if __name__ == "__main__":
    main()
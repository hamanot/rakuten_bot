import sys
import os
import tkinter.messagebox as mb

# シングルトンマネージャーと各コンポーネントのインポート
from component.chrome_driver_manager import ChromeDriverManager
from bl.purchase_logic import PurchaseLogic
from ui.top_menu import TopMenu
from ui.debug_controller import DebugController


def main():
    try:
        # 1. 初期メニュー起動
        # TopMenu内部で ChromeDriverManager.get_driver() および
        # PurchaseLogic.get_instance(debug_mode=...) が呼ばれる想定です
        menu = TopMenu()
        menu.mainloop()

        # 2. 実行開始確認
        # menu.result が存在しない、または開始ボタンが押されていない場合は終了
        if not hasattr(menu, "result") or not menu.result.get("is_start"):
            print("実行キャンセル: メニューを閉じました。")
            ChromeDriverManager.quit_driver()
            return

        # 3. シングルトンインスタンスの取得（TopMenuで初期化済みのものを引き継ぐ）
        try:
            driver = ChromeDriverManager.get_driver()
            logic = PurchaseLogic.get_instance()
        except Exception as e:
            mb.showerror("エラー", f"インスタンスの取得に失敗しました:\n{e}")
            return

        is_debug = logic.debug_mode
        item_url = logic.item.get("item_url")

        if not item_url:
            mb.showerror("エラー", "商品URLが設定されていません。")
            ChromeDriverManager.quit_driver()
            return

        # 4. 実行フェーズ
        print(f"モード: {'デバッグ' if is_debug else '本番'}")

        # まずは商品ページへ移動
        driver.get(item_url)

        if not is_debug:
            # --- 本番モード ---
            print("本番モードを実行します...")

            # クッキーの読み込みとログインチェック
            logic.load_cookies()
            driver.refresh()

            if not logic.is_logged_in():
                print("未ログインのため、ログイン処理を実行します。")
                if not logic.execute_login():
                    mb.showerror("エラー", "ログインに失敗しました。")
                    return

            # 購入アクションの実行
            actions = logic.item.get("actions", [])
            required_kw = logic.item.get("required_keywords", [])

            for i, a_set in enumerate(actions):
                print(f"アクションセット {i + 1}/{len(actions)} を実行中...")
                # 必須項目の選択
                logic.select_required_options(required_kw)
                # 個別アクション（色・サイズ選択等）の実行
                logic.execute_action_set(a_set)
                # カゴ入れ
                logic.add_to_cart()

                # 次のセットがある場合は商品ページに戻る
                if i < len(actions) - 1:
                    driver.get(item_url)

            # 最終決済画面（ワープ）
            print("決済画面へ遷移します。")
            logic.go_to_checkout()

        else:
            # --- デバッグモード ---
            print("デバッグコントローラーを起動します...")
            # DebugController内部で自ら get_instance されるため引数は不要
            ctrl = DebugController()
            ctrl.mainloop()

    except Exception as e:
        print(f"実行エラー: {e}")
        mb.showerror("実行エラー", f"プログラムの実行中にエラーが発生しました:\n{e}")

    finally:
        # ブラウザを閉じる
        ChromeDriverManager.quit_driver()
        pass


if __name__ == "__main__":
    main()
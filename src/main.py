import sys
import tkinter.messagebox as mb
from component.chrome_driver_manager import ChromeDriverManager
from ui.product_controller import ProductController

def main():
    try:
        # 1. プロダクトコントローラーを起動
        # デフォルトのモード（例: debug_mode=True）で開始
        # この中でブラウザの生成、ロジックの初期化がすべて完結します
        app = ProductController(debug_mode=True)
        app.mainloop()

    except Exception as e:
        print(f"致命的なエラー: {e}")
        mb.showerror("起動エラー", f"プログラムの開始に失敗しました:\n{e}")

    finally:
        # 2. アプリ終了時にブラウザを確実に破棄
        # ProductControllerの _on_closing でも呼ばれますが、念のためここでも実行
        ChromeDriverManager.quit_driver()

if __name__ == "__main__":
    main()
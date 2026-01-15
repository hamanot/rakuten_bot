import tkinter as tk
from tkinter import ttk
import os


class BaseDialog(tk.Toplevel):
    def __init__(self, parent, title="Dialog", size="400x300"):
        super().__init__(parent)
        self.title(title)

        # size引数が渡された場合のみ geometry を設定する
        if size:
            self.geometry(size)

        # プロジェクトルートの特定
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.abspath(os.path.join(self.current_dir, "..", ".."))

        # モーダル設定
        self.transient(parent)
        self.grab_set()

        # Canvas等の初期化用属性
        self.canvas = None
        self.canvas_window = None
        self.scroll_frame = None

        self.protocol("WM_DELETE_WINDOW", self.close_dialog)

    def create_scrollable_container(self):
        """
        スクロール可能なコンテナを作成。
        内部フレームのサイズ変更を監視し、自動でスクロール範囲を更新する。
        """
        self.canvas = tk.Canvas(self, highlightthickness=0)
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)

        # 【重要】内部フレームのサイズが変わるたびにスクロール範囲(scrollregion)を自動更新
        # これにより、解析結果が増えた瞬間にスクロールバーが有効になります
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # フレームをCanvasの (0,0) 位置に「北西(nw)」基準で配置（上詰めの基本）
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        # ウィンドウサイズが変わった時に、Canvas自体の幅も同期
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=v_scroll.set)

        v_scroll.pack(side="right", fill="y")
        # expand=True だが、初期サイズを小さくすれば中身に合わせて表示される
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        return self.scroll_frame

    def adjust_to_content(self, width=None, max_ratio=0.85):
        self.update_idletasks()

        screen_h = self.winfo_screenheight()
        limit_h = int(screen_h * max_ratio)

        if self.scroll_frame:
            # 内部フレームの「真の要求高さ」を取得
            needed_h = self.scroll_frame.winfo_reqheight()
        else:
            needed_h = self.winfo_reqheight()

        final_h = min(needed_h, limit_h)
        current_width = width if width else self.winfo_width()

        # ウィンドウサイズを変更
        self.geometry(f"{current_width}x{final_h}")

        # 【重要】geometryの適用がOSレベルで完了するのを待ってから
        # スクロール範囲を「表示領域ぴったり」に上書きする
        self.after(50, self.finalize_scroll_precision)

    def finalize_scroll_precision(self):
        """遊びをゼロにするための最終調整"""
        if self.canvas:
            # 1. 内部の再計算を強制
            self.update_idletasks()
            # 2. 現在のCanvasの表示高さ(winfo_height)を取得
            canvas_display_h = self.canvas.winfo_height()
            # 3. 中身の高さ(bbox)を取得
            content_h = self.canvas.bbox("all")[3]  # y2座標

            # もし中身が表示領域より小さければ、スクロール領域を表示領域と同じにする（＝スクロール不能にする）
            actual_scroll_h = max(canvas_display_h, content_h)
            self.canvas.configure(scrollregion=(0, 0, self.winfo_width(), actual_scroll_h))

    def _on_canvas_configure(self, event):
        """ウィンドウ幅に合わせて内部フレームの幅を調整"""
        if self.canvas_window:
            self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        """マウスホイールイベント"""
        if self.canvas and self.winfo_exists():
            scroll_units = int(-1 * (event.delta / 120))
            self.canvas.yview_scroll(scroll_units, "units")

    def update_scroll(self):
        """手動でスクロール範囲を最新にする（描画直後用）"""
        self.update_idletasks()
        if self.canvas:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def close_dialog(self):
        """終了処理：イベント解除とモーダル解除"""
        try:
            self.unbind_all("<MouseWheel>")
            self.grab_release()
        except:
            pass
        self.destroy()
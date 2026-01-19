import tkinter as tk
from tkinter import ttk
import os


class BaseDialog:
    """共通機能（スクロール、リサイズ、パス管理）を提供する基本クラス"""

    def _init_base_logic(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.abspath(os.path.join(self.current_dir, "..", ".."))
        self.canvas = None
        self.canvas_window = None
        self.scroll_frame = None

    def create_scrollable_container(self):
        """リサイズとマウスホイールに完璧に同期するスクロールコンテナを作成"""
        self.canvas = tk.Canvas(self, highlightthickness=0)
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)

        # 1. 内部フレームのサイズが変わったらスクロール領域を更新
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self._update_scroll_region()
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        # 2. ウィンドウサイズ変更時に幅を同期させ、領域を再計算
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=v_scroll.set)

        v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # 3. マウスホイール制御（ガード付き）
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind("<Destroy>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

        return self.scroll_frame

    def _update_scroll_region(self):
        """スクロール可能範囲を最新のコンテンツサイズに同期"""
        if self.canvas:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """キャンバスのリサイズに合わせて内部フレームの幅を調整"""
        if self.canvas_window:
            self.canvas.itemconfig(self.canvas_window, width=event.width)
            self._update_scroll_region()

    def _on_mousewheel(self, event):
        """スクロールバーが必要な時だけホイールを有効にするガードロジック"""
        if not self.canvas or not self.winfo_exists():
            return

        # ガード：コンテンツがCanvasより小さい場合は何もしない
        self.update_idletasks()  # 最新のサイズを取得
        content_h = self.scroll_frame.winfo_height()
        canvas_h = self.canvas.winfo_height()

        if content_h <= canvas_h:
            return

        # スクロール実行
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def adjust_to_content(self, width=None, max_ratio=0.85):
        """コンテンツ量（中身＋固定エリア）に基づいた初期サイズ調整"""
        self.update_idletasks()

        # 1. 画面の高さ制限を取得
        screen_h = self.winfo_screenheight()
        limit_h = int(screen_h * max_ratio)

        # 2. スクロール領域「以外」の高さ（ボタンエリアなど）を計算
        # self（ダイアログ本体）の要求高さから、Canvasの現在の高さを引くことで外枠のサイズを算出
        other_h = 0
        for child in self.winfo_children():
            # Canvas(スクロールエリア)とScrollbar以外の高さを合算
            if child != self.canvas and not isinstance(child, ttk.Scrollbar):
                other_h += child.winfo_reqheight()

        # 3. スクロール領域の中身(scroll_frame)の要求高さ
        content_h = self.scroll_frame.winfo_reqheight() if self.scroll_frame else self.winfo_reqheight()

        # 4. 合計の必要高さ
        needed_h = content_h + other_h

        # 5. 最終的な高さを決定（画面制限内に収める）
        final_h = min(needed_h, limit_h)
        current_width = width if width else self.winfo_width()

        # 6. サイズ反映
        self.geometry(f"{current_width}x{final_h}")
        self._update_scroll_region()
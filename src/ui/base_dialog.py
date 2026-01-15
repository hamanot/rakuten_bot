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
        self.canvas = tk.Canvas(self, highlightthickness=0)
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=v_scroll.set)

        v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        return self.scroll_frame

    def _on_canvas_configure(self, event):
        if self.canvas_window:
            self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if self.canvas and self.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def adjust_to_content(self, width=None, max_ratio=0.85):
        self.update_idletasks()
        screen_h = self.winfo_screenheight()
        limit_h = int(screen_h * max_ratio)
        needed_h = self.scroll_frame.winfo_reqheight() if self.scroll_frame else self.winfo_reqheight()
        final_h = min(needed_h, limit_h)
        current_width = width if width else self.winfo_width()
        self.geometry(f"{current_width}x{final_h}")
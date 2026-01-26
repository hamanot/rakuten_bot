import tkinter as tk
from datetime import datetime


class LogWindowParts(tk.Frame):
    def __init__(self, parent, is_debug_mode=True, **kwargs):
        super().__init__(parent, **kwargs)
        self.is_debug_mode = is_debug_mode
        self._create_widgets()

    def _create_widgets(self):
        font_candidates = ["BIZ UDゴシック", "MS Gothic", "monospace"]
        import tkinter.font as tkfont
        available = tkfont.families()
        selected_font = "monospace"
        for f in font_candidates:
            if f in available:
                selected_font = f
                break

        self.text_area = tk.Text(
            self,
            bg="#1e1e1e",
            fg="#d4d4d4",
            font=(selected_font, 10),
            padx=10,
            pady=10,
            # --- 修正ポイント: wrap を "char" に変更 ---
            wrap="char"
        )

        scrollbar = tk.Scrollbar(self, command=self.text_area.yview)
        scrollbar.pack(side="right", fill="y")
        self.text_area.pack(side="left", fill="both", expand=True)

        self.text_area.config(yscrollcommand=scrollbar.set)

        self.text_area.tag_configure("DEBUG", foreground="#848484")
        self.text_area.tag_configure("WARNING", foreground="#f1c40f")
        self.text_area.tag_configure("ERROR", foreground="#ff6b6b")
        self.text_area.tag_configure("INFO", foreground="#51cf66")

    def _write(self, level_name, message, tag):
        now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_msg = f"[{now}] [{level_name}] {message}"
        print(formatted_msg)

        self.text_area.insert("end", formatted_msg + "\n", tag)
        self.text_area.see("end")

    def debug(self, message):
        if self.is_debug_mode:
            self._write("DEBUG", message, "DEBUG")

    def info(self, message):
        self._write("INFO", message, "INFO")

    def warning(self, message):
        self._write("WARNING", message, "WARNING")

    def error(self, message, code=None):
        msg = f"{message} (Code: {code})" if code else message
        self._write("ERROR", msg, "ERROR")

    def clear(self):
        self.text_area.delete("1.0", "end")
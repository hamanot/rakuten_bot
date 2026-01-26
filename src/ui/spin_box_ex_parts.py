import tkinter as tk


class SpinBoxEx(tk.Spinbox):
    """
    Python 3.6対応: 2桁0埋めとループ機能を備えた拡張スピンボックス
    """

    def __init__(self, parent, from_, to, **kwargs):
        # デフォルト設定
        opts = {
            "width": 3,
            "justify": "center",
            "wrap": True,
            "from_": from_,
            "to": to,
            "command": self._format_value
        }
        opts.update(kwargs)
        super().__init__(parent, **opts)

        # 手入力（フォーカスアウト）時も0埋めされるようにバインド
        self.bind("<FocusOut>", lambda e: self._format_value())

    def _format_value(self):
        """現在の値を2桁0埋めに整形する"""
        try:
            val = int(self.get())
            self.set_value(val)
        except ValueError:
            pass

    def set_value(self, val):
        """外部から値をセットする（0埋め適用）"""
        self.delete(0, "end")
        self.insert(0, "{:02d}".format(int(val)))

    def get_value_str(self):
        """現在の値を2桁文字列で取得する"""
        self._format_value()  # 念のため整形
        return self.get()
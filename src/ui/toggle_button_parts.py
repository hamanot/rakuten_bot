import tkinter as tk
from PIL import Image, ImageDraw, ImageFilter, ImageTk


class ToggleButton(tk.Canvas):
    def __init__(self, parent, variable, command=None, width=50, height=26):
        super().__init__(parent, width=width, height=height, highlightthickness=0, cursor="hand2")
        self.variable = variable
        self.command = command
        self.w = width
        self.h = height
        self.scale = 4  # アンチエイリアス用

        # アニメーション用パラメータ
        self.pos = 1.0 if self.variable.get() else 0.0  # 0.0(OFF) ～ 1.0(ON)
        self.animating = False

        self.bind("<Button-1>", self.toggle)
        self.draw()

    def _get_color(self, pos):
        """OFF色とON色の間を補完した色を返す"""
        r1, g1, b1 = 233, 233, 234  # #E9E9EA (OFF)
        r2, g2, b2 = 76, 217, 100  # #4CD964 (ON)
        r = int(r1 + (r2 - r1) * pos)
        g = int(g1 + (g2 - g1) * pos)
        b = int(b1 + (b2 - b1) * pos)
        return (r, g, b)

    def draw(self):
        s = self.scale
        # 透明背景のベース
        img = Image.new("RGBA", (self.w * s, self.h * s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 現在の進捗(self.pos)に基づいた描画
        color = self._get_color(self.pos)

        # 1. 背景（カプセル型）
        draw.ellipse([0, 0, self.h * s, self.h * s], fill=color)
        draw.ellipse([(self.w - self.h) * s, 0, self.w * s, self.h * s], fill=color)
        draw.rectangle([self.h * s / 2, 0, (self.w - self.h / 2) * s, self.h * s], fill=color)

        # 2. ノブの影（シャドウ）の描画
        # ノブの位置を計算
        padding = 2 * s
        knob_size = (self.h * s) - (padding * 2)
        # OFF位置(0)とON位置(w-h)の間をスライド
        start_x = padding + (self.pos * (self.w - self.h) * s)

        # 影用の別レイヤー作成（少しぼかす）
        shadow_img = Image.new("RGBA", (self.w * s, self.h * s), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow_img)
        # わずかに下にずらした位置にグレーの円を描画
        shadow_offset = 1 * s
        s_draw.ellipse([start_x, padding + shadow_offset, start_x + knob_size, padding + knob_size + shadow_offset],
                       fill=(0, 0, 0, 40))
        shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=2 * s))

        # ベース画像に影を合成
        img.alpha_composite(shadow_img)

        # 3. ノブ本体の描画
        draw.ellipse([start_x, padding, start_x + knob_size, padding + knob_size], fill="white")

        # 4. リサイズして表示
        img = img.resize((self.w, self.h), Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(img)
        self.delete("all")
        self.create_image(0, 0, image=self.tk_img, anchor="nw")

    def animate(self):
        """位置(pos)を目標値まで近づける"""
        target = 1.0 if self.variable.get() else 0.0
        step = 0.2  # アニメーション速度（大きいほど速い）

        if abs(self.pos - target) < step:
            self.pos = target
            self.draw()
            self.animating = False
        else:
            self.pos += step if target > self.pos else -step
            self.draw()
            self.after(15, self.animate)

    def toggle(self, event=None):
        self.variable.set(not self.variable.get())
        if not self.animating:
            self.animating = True
            self.animate()

        if self.command:
            self.command()
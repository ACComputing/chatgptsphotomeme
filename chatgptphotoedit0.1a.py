#!/usr/bin/env python3.14
import tkinter as tk
from tkinter import filedialog, messagebox
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

APP_TITLE = "Chatgpts photoediit 0.1"

TEMPLATES = {
    "Drake":             "https://i.imgflip.com/30b1gx.jpg",
    "Distracted BF":     "https://i.imgflip.com/1ur9b0.jpg",
    "Two Buttons":       "https://i.imgflip.com/1g8my4.jpg",
    "Change My Mind":    "https://i.imgflip.com/24y43o.jpg",
    "This Is Fine":      "https://i.imgflip.com/wxica.jpg",
    "Expanding Brain":   "https://i.imgflip.com/1jwhww.jpg",
    "Disaster Girl":     "https://i.imgflip.com/23ls.jpg",
    "Doge":              "https://i.imgflip.com/4t0m5.jpg",
    "Hide the Pain":     "https://i.imgflip.com/gk5el.jpg",
    "Gru's Plan":        "https://i.imgflip.com/26am.jpg",
    "Stonks":            "https://i.imgflip.com/3m09bn.jpg",
    "Always Has Been":   "https://i.imgflip.com/46e43q.jpg",
    "Chad":              "https://i.imgflip.com/6yvpkj.png",
    "Tuxedo Winnie":     "https://i.imgflip.com/5c7lwq.png",
    "Uno Draw 25":       "https://i.imgflip.com/3lmzyx.jpg",
}

IMPACT_PATHS = (
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/Library/Fonts/Impact.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
    "/usr/share/fonts/truetype/impact.ttf",
    "impact.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "DejaVuSans-Bold.ttf",
    "arialbd.ttf",
)

BTN = {
    "bg": "black",
    "fg": "#2b7cff",
    "activebackground": "#111",
    "activeforeground": "#5599ff",
}

BTN_BOLD = {
    **BTN,
    "font": ("Arial", 10, "bold"),
}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("940x570")
        self.root.configure(bg="#0b0b0f")
        self.root.resizable(False, False)

        self.image = None
        self.output = None
        self.preview = None
        self.tk_img = None
        self.render_job = None

        self.canvas_w = 650
        self.canvas_h = 510
        self.display_x = 0
        self.display_y = 0
        self.display_w = self.canvas_w
        self.display_h = self.canvas_h

        self.top_text = tk.StringVar(value="TOP TEXT")
        self.bottom_text = tk.StringVar(value="BOTTOM TEXT")

        self.top_pos = [0.5, 0.10]
        self.bottom_pos = [0.5, 0.90]
        self.dragging = None

        self._image_cache = {}
        self._font_cache = {}
        self._text_fit_cache = {}
        self._last_render_key = None

        self.build_ui()
        self.root.after(80, self.load_selected)

    # ================= UI =================

    def build_ui(self):
        main = tk.Frame(self.root, bg="#0b0b0f")
        main.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            main,
            width=self.canvas_w,
            height=self.canvas_h,
            bg="#050508",
            highlightthickness=0,
        )
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)

        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)

        panel = tk.Frame(main, width=250, bg="#121218")
        panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        panel.pack_propagate(False)

        tk.Label(
            panel,
            text="Photoediit 0.1",
            bg="#121218",
            fg="#2b7cff",
            font=("Arial", 16, "bold"),
        ).pack(pady=10)

        tk.Label(
            panel,
            text="Default Memes",
            bg="#121218",
            fg="#aaa",
            font=("Arial", 10, "bold"),
        ).pack(pady=(4, 0))

        lb_frame = tk.Frame(panel, bg="#121218")
        lb_frame.pack(fill=tk.X, padx=8, pady=4)

        sb = tk.Scrollbar(lb_frame, orient=tk.VERTICAL)

        self.listbox = tk.Listbox(
            lb_frame,
            yscrollcommand=sb.set,
            bg="#0b0b0f",
            fg="white",
            selectbackground="#2b7cff",
            selectforeground="black",
            height=9,
            font=("Arial", 11),
            activestyle="none",
            bd=0,
            highlightthickness=0,
        )

        sb.config(command=self.listbox.yview)
        self.listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        for name in TEMPLATES:
            self.listbox.insert(tk.END, name)

        self.listbox.select_set(0)
        self.listbox.bind("<<ListboxSelect>>", lambda event: self.load_selected())

        tk.Button(
            panel,
            text="Load Selected",
            command=self.load_selected,
            **BTN_BOLD,
        ).pack(fill=tk.X, padx=8, pady=(2, 6))

        tk.Frame(panel, bg="#2b7cff", height=1).pack(fill=tk.X, padx=8, pady=4)

        tk.Button(
            panel,
            text="Open Local Image…",
            command=self.open_image,
            **BTN,
        ).pack(fill=tk.X, padx=8, pady=(0, 8))

        tk.Label(
            panel,
            text="Top Caption",
            bg="#121218",
            fg="white",
        ).pack(pady=(4, 0))

        top_entry = tk.Entry(
            panel,
            textvariable=self.top_text,
            bg="#0b0b0f",
            fg="white",
            insertbackground="white",
        )
        top_entry.pack(fill=tk.X, padx=8)
        top_entry.bind("<KeyRelease>", lambda event: self.schedule_render())

        tk.Label(
            panel,
            text="Bottom Caption",
            bg="#121218",
            fg="white",
        ).pack(pady=(8, 0))

        bottom_entry = tk.Entry(
            panel,
            textvariable=self.bottom_text,
            bg="#0b0b0f",
            fg="white",
            insertbackground="white",
        )
        bottom_entry.pack(fill=tk.X, padx=8)
        bottom_entry.bind("<KeyRelease>", lambda event: self.schedule_render())

        tk.Button(
            panel,
            text="Reset Positions",
            command=self.reset_text,
            **BTN,
        ).pack(fill=tk.X, padx=8, pady=(12, 4))

        tk.Button(
            panel,
            text="Export PNG",
            command=self.export_png,
            **BTN_BOLD,
        ).pack(fill=tk.X, padx=8, pady=4)

        tk.Label(
            panel,
            text="Drag red dots to reposition text.",
            bg="#121218",
            fg="#666",
            wraplength=210,
            font=("Arial", 9),
        ).pack(padx=8, pady=8)

        self.render_empty()

    # ================= IMAGE LOADING =================

    def load_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return

        name = self.listbox.get(sel[0])

        if name in self._image_cache:
            self.image = self._image_cache[name].copy()
            self.reset_text()
            return

        try:
            img = self.download_image(TEMPLATES[name])
            self._image_cache[name] = img.copy()
            self.image = img
            self.reset_text()

        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not load '{name}':\n\n{exc}")
            self.render_empty(f"Could not load image:\n{exc}")

    def download_image(self, url):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X) "
                "AppleWebKit/537.36 Chrome Safari"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        }

        req = Request(url, headers=headers)

        try:
            with urlopen(req, timeout=20) as response:
                data = response.read()

        except HTTPError as exc:
            raise RuntimeError(f"HTTP error {exc.code}: {exc.reason}") from exc

        except URLError as exc:
            raise RuntimeError(f"Network error: {exc.reason}") from exc

        if not data:
            raise RuntimeError("Downloaded 0 bytes.")

        if data[:200].lstrip().lower().startswith((b"<!doctype html", b"<html")):
            raise RuntimeError("The URL returned HTML instead of an image.")

        try:
            img = Image.open(BytesIO(data))
            img = ImageOps.exif_transpose(img)
            return img.convert("RGB")

        except UnidentifiedImageError as exc:
            raise RuntimeError("Downloaded data was not a valid image.") from exc

    def open_image(self):
        path = filedialog.askopenfilename(
            title="Open meme image",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("All files", "*.*"),
            ],
        )

        if not path:
            return

        try:
            img = Image.open(path)
            img = ImageOps.exif_transpose(img)
            self.image = img.convert("RGB")
            self.reset_text()

        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not open image:\n\n{exc}")

    # ================= FONT + TEXT =================

    def get_font(self, size):
        size = int(size)

        if size in self._font_cache:
            return self._font_cache[size]

        for path in IMPACT_PATHS:
            try:
                font = ImageFont.truetype(path, size)
                self._font_cache[size] = font
                return font
            except Exception:
                pass

        try:
            font = ImageFont.load_default(size=size)
        except TypeError:
            font = ImageFont.load_default()

        self._font_cache[size] = font
        return font

    def text_size(self, draw, text, font, stroke_width):
        bbox = draw.textbbox(
            (0, 0),
            text,
            font=font,
            stroke_width=stroke_width,
            anchor="lt",
        )
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def wrap_text(self, draw, text, font, stroke_width, max_width):
        words = text.split()
        if not words:
            return []

        lines = []
        current = words[0]

        for word in words[1:]:
            test = current + " " + word
            if self.text_size(draw, test, font, stroke_width)[0] <= max_width:
                current = test
            else:
                lines.append(current)
                current = word

        lines.append(current)
        return lines

    def fit_text(self, draw, text, max_width, max_height):
        cache_key = (
            text,
            max_width,
            max_height,
            self.image.size if self.image else None,
        )

        if cache_key in self._text_fit_cache:
            return self._text_fit_cache[cache_key]

        start_size = clamp(int(max(self.image.width, self.image.height) * 0.115), 42, 96)

        for size in range(start_size, 17, -2):
            stroke = max(3, int(size * 0.10))
            font = self.get_font(size)
            lines = self.wrap_text(draw, text, font, stroke, max_width)

            if not lines:
                continue

            widths = [self.text_size(draw, line, font, stroke)[0] for line in lines]
            line_h = self.text_size(draw, "Ag", font, stroke)[1]
            gap = max(2, int(size * 0.08))
            total_h = len(lines) * line_h + (len(lines) - 1) * gap

            if max(widths) <= max_width and total_h <= max_height:
                result = font, stroke, lines, line_h, gap, total_h
                self._text_fit_cache[cache_key] = result
                return result

        font = self.get_font(18)
        stroke = 3
        lines = self.wrap_text(draw, text, font, stroke, max_width)
        line_h = self.text_size(draw, "Ag", font, stroke)[1]
        gap = 2
        total_h = len(lines) * line_h + max(0, len(lines) - 1) * gap

        result = font, stroke, lines, line_h, gap, total_h
        self._text_fit_cache[cache_key] = result
        return result

    def draw_meme_text(self, img, text, pos):
        text = " ".join(text.strip().upper().split())
        if not text:
            return

        draw = ImageDraw.Draw(img)
        max_width = int(img.width * 0.92)
        max_height = int(img.height * 0.34)

        font, stroke, lines, line_h, gap, total_h = self.fit_text(
            draw,
            text,
            max_width,
            max_height,
        )

        center_x = int(pos[0] * img.width)
        center_y = int(pos[1] * img.height)
        y = clamp(center_y - total_h // 2, 8, img.height - total_h - 8)

        for line in lines:
            text_w, _ = self.text_size(draw, line, font, stroke)
            x = clamp(center_x - text_w // 2, 8, img.width - text_w - 8)

            draw.text(
                (x, y),
                line,
                font=font,
                fill="white",
                stroke_width=stroke,
                stroke_fill="black",
                anchor="lt",
            )

            y += line_h + gap

    # ================= RENDER =================

    def make_output(self):
        if not self.image:
            return None

        img = self.image.copy()
        self.draw_meme_text(img, self.top_text.get(), self.top_pos)
        self.draw_meme_text(img, self.bottom_text.get(), self.bottom_pos)
        return img

    def render_empty(self, msg="← Pick a meme or open an image"):
        self.canvas.delete("all")
        self.canvas.create_text(
            self.canvas_w // 2,
            self.canvas_h // 2,
            text=msg,
            fill="#555",
            font=("Arial", 16, "bold"),
            justify="center",
        )

    def schedule_render(self):
        if self.render_job is not None:
            self.root.after_cancel(self.render_job)

        self.render_job = self.root.after(35, self.render)

    def render(self):
        self.render_job = None

        if not self.image:
            self.render_empty()
            return

        key = (
            id(self.image),
            self.image.size,
            self.top_text.get(),
            self.bottom_text.get(),
            round(self.top_pos[0], 4),
            round(self.top_pos[1], 4),
            round(self.bottom_pos[0], 4),
            round(self.bottom_pos[1], 4),
        )

        if key != self._last_render_key:
            self.output = self.make_output()
            self.preview = self.output.copy()
            self.preview.thumbnail((self.canvas_w, self.canvas_h), Image.Resampling.LANCZOS)

            self.display_w, self.display_h = self.preview.size
            self.display_x = (self.canvas_w - self.display_w) // 2
            self.display_y = (self.canvas_h - self.display_h) // 2

            self.tk_img = ImageTk.PhotoImage(self.preview)
            self._last_render_key = key

        self.canvas.delete("all")
        self.canvas.create_image(
            self.display_x,
            self.display_y,
            image=self.tk_img,
            anchor=tk.NW,
        )

        self.draw_dot(self.top_pos)
        self.draw_dot(self.bottom_pos)

    # ================= DRAG =================

    def draw_dot(self, pos):
        x = self.display_x + pos[0] * self.display_w
        y = self.display_y + pos[1] * self.display_h

        self.canvas.create_oval(
            x - 7,
            y - 7,
            x + 7,
            y + 7,
            fill="red",
            outline="white",
            width=2,
        )

    def screen_to_pos(self, x, y):
        return [
            clamp((x - self.display_x) / max(1, self.display_w), 0.0, 1.0),
            clamp((y - self.display_y) / max(1, self.display_h), 0.0, 1.0),
        ]

    def hit(self, x, y):
        for name, pos in (("top", self.top_pos), ("bottom", self.bottom_pos)):
            px = self.display_x + pos[0] * self.display_w
            py = self.display_y + pos[1] * self.display_h

            if abs(x - px) < 30 and abs(y - py) < 30:
                return name

        return None

    def start_drag(self, event):
        self.dragging = self.hit(event.x, event.y)

    def stop_drag(self, event):
        self.dragging = None

    def drag(self, event):
        if self.dragging == "top":
            self.top_pos = self.screen_to_pos(event.x, event.y)
            self.schedule_render()

        elif self.dragging == "bottom":
            self.bottom_pos = self.screen_to_pos(event.x, event.y)
            self.schedule_render()

    # ================= ACTIONS =================

    def reset_text(self):
        self.top_pos = [0.5, 0.10]
        self.bottom_pos = [0.5, 0.90]
        self._last_render_key = None
        self.render()

    def export_png(self):
        if not self.output:
            messagebox.showwarning(APP_TITLE, "Nothing to export yet.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")],
        )

        if not path:
            return

        try:
            self.output.save(path)
            messagebox.showinfo(APP_TITLE, f"Saved to {path}")

        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not save image:\n\n{exc}")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()

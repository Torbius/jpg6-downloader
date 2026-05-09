"""ctk_frontend.py — CustomTkinter Material Design 3 UI for JPG6 Downloader."""
from __future__ import annotations

import json
import os
import sys
import threading
import urllib.request
from io import BytesIO
from tkinter import filedialog
import tkinter as tk

import customtkinter as ctk

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
except ImportError:
    print("Pillow is required: pip install Pillow")
    sys.exit(1)

from backend import CONFIG_DIR, DEBUG_LOG_FILE, ERROR_LOG_FILE, DownloadBackend, format_size

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ── Palette ───────────────────────────────────────────────────────────────────
C_BG      = "#0e0b17"
C_SIDE    = "#120b1f"
C_CARD    = "#1a1230"
C_SURF    = "#160e28"
C_ACC1    = "#7C3AED"   # Deep Purple
C_ACC1_H  = "#6d28d9"
C_ACC2    = "#F59E0B"   # Amber
C_ACC2_H  = "#d97706"
C_GREEN   = "#22c55e"   # Download button
C_GREEN_H = "#16a34a"
C_STOP    = "#ef4444"
C_STOP_H  = "#dc2626"
C_TEXT    = "#f0eeff"
C_MUTED   = "#b8aad8"
C_BORDER  = "#3d2f6a"
R         = 12

FONT_TITLE = ("Inter", 20, "bold")
FONT_SUB   = ("Inter", 11)
FONT_LBL   = ("Inter", 13)
FONT_BTN   = ("Inter", 13, "bold")
FONT_SM    = ("Inter", 11)
FONT_MONO  = ("Consolas", 11)

# ── Segoe Fluent Icons (built into Windows 10/11) ─────────────────────────────
_ICON_FONT_PATH = r"C:\Windows\Fonts\SegoeFluentIcons.ttf"
_ICON_AVAIL = os.path.exists(_ICON_FONT_PATH)

ICO_FOLDER   = "\uED25"
ICO_SAVE     = "\uE74E"
ICO_IMPORT   = "\uE8B5"
ICO_SCAN     = "\uE773"
ICO_DOWNLOAD = "\uE896"
ICO_STOP     = "\uE71A"
ICO_ADD      = "\uE710"
ICO_CLEAR    = "\uE74D"
ICO_CHECK    = "\uE73E"
ICO_CLOSE    = "\uE711"
ICO_TRASH    = "\uE74D"
ICO_PASTE    = "\uF0E3"

_ICONS: dict[str, ctk.CTkImage | None] = {}


def _make_icon(char: str, size: int, color: str) -> "ctk.CTkImage | None":
    """Render a Segoe Fluent Icons glyph as CTkImage."""
    if not _ICON_AVAIL:
        return None
    try:
        pil_font = ImageFont.truetype(_ICON_FONT_PATH, size)
        tmp      = Image.new("RGBA", (size * 3, size * 3), (0, 0, 0, 0))
        d        = ImageDraw.Draw(tmp)
        bbox     = d.textbbox((0, 0), char, font=pil_font)
        w        = max(1, bbox[2] - bbox[0])
        h        = max(1, bbox[3] - bbox[1])
        img      = Image.new("RGBA", (w + 2, h + 2), (0, 0, 0, 0))
        d2       = ImageDraw.Draw(img)
        r_       = int(color[1:3], 16)
        g_       = int(color[3:5], 16)
        b_       = int(color[5:7], 16)
        d2.text((-bbox[0] + 1, -bbox[1] + 1), char, font=pil_font, fill=(r_, g_, b_, 255))
        return ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
    except Exception:
        return None


def get_icon(char: str, size: int = 15, color: str = "#ffffff") -> "ctk.CTkImage | None":
    key = f"{char}_{size}_{color}"
    if key not in _ICONS:
        _ICONS[key] = _make_icon(char, size, color)
    return _ICONS[key]


# ── I18N ──────────────────────────────────────────────────────────────────────
I18N: dict[str, dict[str, str]] = {
    "en": {
        "window_title":        "JPG6 Downloader Pro",
        "app_title":           "JPG6 Downloader",
        "app_subtitle":        "Material Design 3  \u00b7  Direct Engine",
        "workers":             "Workers",
        "language":            "Language",
        "folder_label":        "Download folder",
        "pick_folder":         "Pick Folder",
        "save_settings":       "Save Settings",
        "import_txt":          "Import TXT",
        "scan_preview":        "Scan & Preview",
        "start_download":      "Download Selected",
        "stop":                "Stop",
        "url_placeholder":     "Paste album / profile / image URL\u2026",
        "add":                 "Add URL",
        "clear_queue":         "Clear Queue",
        "status_ready":        "Ready",
        "settings_saved":      "Settings saved",
        "pick_folder_dialog":  "Select download folder",
        "invalid_url":         "Invalid URL \u2014 must start with http",
        "queued_count":        "In queue: {count}",
        "queue_cleared":       "Queue cleared",
        "import_file_dialog":  "Select TXT files with URLs",
        "imported_count":      "Imported {count} URLs \u2014 click Scan",
        "backend_running":     "Already running \u2014 please wait",
        "queue_empty":         "Queue is empty \u2014 add URLs first",
        "starting_scan":       "Scanning URLs\u2026",
        "starting_download":   "Downloading\u2026",
        "stopping":            "Stopping\u2026",
        "scan_done":           "Scan complete: {count} images found",
        "no_selected":         "No images selected in gallery",
        "cancelled_summary":   "Stopped \u2014 downloaded={downloaded}  skipped={skipped}  errors={errors}",
        "done_summary":        "Done \u2014 downloaded={downloaded}  skipped={skipped}  errors={errors}",
        "lang_ru":             "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
        "lang_en":             "English",
        "select_all":          "Select All",
        "deselect_all":        "Deselect",
        "size_small":          "S",
        "size_medium":         "M",
        "size_large":          "L",
        "clear_gallery":       "Clear Gallery",
        "gallery_title":       "Gallery  \u00b7  check images to download",
        "ctx_cut":             "Cut",
        "ctx_copy":            "Copy",
        "ctx_paste":           "Paste",
        "ctx_select_all":      "Select All",
        "ctx_clear":           "Clear",
        "pasted_multi":        "Added {count} URLs to queue",
        "paste_btn":           "Paste URL",
    },
    "ru": {
        "window_title":        "JPG6 Downloader Pro",
        "app_title":           "JPG6 Downloader",
        "app_subtitle":        "Material Design 3  \u00b7  \u043f\u0440\u044f\u043c\u043e\u0439 \u0434\u0432\u0438\u0436\u043e\u043a",
        "workers":             "\u041f\u043e\u0442\u043e\u043a\u0438",
        "language":            "\u042f\u0437\u044b\u043a",
        "folder_label":        "\u041f\u0430\u043f\u043a\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0438",
        "pick_folder":         "\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u043f\u0430\u043f\u043a\u0443",
        "save_settings":       "\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c",
        "import_txt":          "\u0418\u043c\u043f\u043e\u0440\u0442 TXT",
        "scan_preview":        "\u0421\u043a\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u0442\u044c",
        "start_download":      "\u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c",
        "stop":                "\u0421\u0442\u043e\u043f",
        "url_placeholder":     "\u0421\u0441\u044b\u043b\u043a\u0430 \u043d\u0430 \u0430\u043b\u044c\u0431\u043e\u043c / \u043f\u0440\u043e\u0444\u0438\u043b\u044c / \u0444\u043e\u0442\u043e\u2026",
        "add":                 "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c",
        "clear_queue":         "\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c",
        "status_ready":        "\u0413\u043e\u0442\u043e\u0432\u043e",
        "settings_saved":      "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u044b",
        "pick_folder_dialog":  "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0430\u043f\u043a\u0443 \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0438",
        "invalid_url":         "\u041d\u0435\u0432\u0435\u0440\u043d\u044b\u0439 URL \u2014 \u0434\u043e\u043b\u0436\u0435\u043d \u043d\u0430\u0447\u0438\u043d\u0430\u0442\u044c\u0441\u044f \u0441 http",
        "queued_count":        "\u0412 \u043e\u0447\u0435\u0440\u0435\u0434\u0438: {count}",
        "queue_cleared":       "\u041e\u0447\u0435\u0440\u0435\u0434\u044c \u043e\u0447\u0438\u0449\u0435\u043d\u0430",
        "import_file_dialog":  "Выберите TXT-файлы со ссылками",
        "imported_count":      "\u0418\u043c\u043f\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u043e {count} URL \u2014 \u043d\u0430\u0436\u043c\u0438\u0442\u0435 \u0421\u043a\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u0442\u044c",
        "backend_running":     "\u0423\u0436\u0435 \u0437\u0430\u043f\u0443\u0449\u0435\u043d\u043e",
        "queue_empty":         "\u041e\u0447\u0435\u0440\u0435\u0434\u044c \u043f\u0443\u0441\u0442\u0430 \u2014 \u0434\u043e\u0431\u0430\u0432\u044c\u0442\u0435 URL",
        "starting_scan":       "\u0421\u043a\u0430\u043d\u0438\u0440\u0443\u044e URL\u2026",
        "starting_download":   "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430\u2026",
        "stopping":            "\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0430\u2026",
        "scan_done":           "\u0421\u043a\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u043e: {count} \u0444\u043e\u0442\u043e",
        "no_selected":         "\u041d\u0435\u0442 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0445",
        "cancelled_summary":   "\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u043e \u2014 \u0441\u043a\u0430\u0447\u0430\u043d\u043e={downloaded}  \u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u043e={skipped}  \u043e\u0448\u0438\u0431\u043e\u043a={errors}",
        "done_summary":        "\u0413\u043e\u0442\u043e\u0432\u043e \u2014 \u0441\u043a\u0430\u0447\u0430\u043d\u043e={downloaded}  \u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u043e={skipped}  \u043e\u0448\u0438\u0431\u043e\u043a={errors}",
        "lang_ru":             "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
        "lang_en":             "English",
        "select_all":          "\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0432\u0441\u0435",
        "deselect_all":        "\u0421\u043d\u044f\u0442\u044c",
        "size_small":          "\u041c",
        "size_medium":         "\u0421",
        "size_large":          "\u041a",
        "clear_gallery":       "\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c",
        "gallery_title":       "\u0413\u0430\u043b\u0435\u0440\u0435\u044f  \u00b7  \u043e\u0442\u043c\u0435\u0442\u044c\u0442\u0435 \u0444\u043e\u0442\u043e \u0434\u043b\u044f \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0438",
        "ctx_cut":             "\u0412\u044b\u0440\u0435\u0437\u0430\u0442\u044c",
        "ctx_copy":            "\u041a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c",
        "ctx_paste":           "\u0412\u0441\u0442\u0430\u0432\u0438\u0442\u044c",
        "ctx_select_all":      "\u0412\u044b\u0434\u0435\u043b\u0438\u0442\u044c \u0432\u0441\u0451",
        "ctx_clear":           "\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c",
        "pasted_multi":        "\u0414\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u043e {count} URL \u0432 \u043e\u0447\u0435\u0440\u0435\u0434\u044c",
        "paste_btn":           "\u0412\u0441\u0442\u0430\u0432\u0438\u0442\u044c URL",
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def load_json(path: str, default=None):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default if default is not None else {}


def save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Background workers ────────────────────────────────────────────────────────
class PreviewWorker:
    """Thread that scans URLs for preview images."""

    def __init__(self, urls, base_dir, workers, batch_name=None,
                 image_found_cb=None, status_cb=None, finished_cb=None, log_cb=None):
        self.urls           = list(urls)
        self.base_dir       = base_dir
        self.workers        = workers
        self.batch_name     = batch_name
        self.image_found_cb = image_found_cb
        self.status_cb      = status_cb
        self.finished_cb    = finished_cb
        self.log_cb         = log_cb
        self.backend        = None
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        count = [0]
        self.backend = DownloadBackend(
            base_dir=self.base_dir, workers=self.workers,
            status_cb=self.status_cb, logger=self.log_cb,
        )

        def _cb(album_title, img):
            count[0] += 1
            if self.image_found_cb:
                self.image_found_cb(
                    album_title,
                    img.get("url", ""),
                    img.get("filename", ""),
                    img.get("thumb_url") or img.get("url", ""),
                )

        self.backend.scan_for_preview(
            self.urls, batch_name=self.batch_name, image_found_cb=_cb,
        )
        if self.finished_cb:
            self.finished_cb(count[0])

    def stop(self):
        if self.backend:
            self.backend.cancel()

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()


class DownloadWorker:
    """Thread that downloads selected images."""

    def __init__(self, selected, base_dir, workers, batch_name=None,
                 log_cb=None, status_cb=None, progress_cb=None,
                 finished_cb=None, file_progress_cb=None):
        self.selected         = selected
        self.base_dir         = base_dir
        self.workers          = workers
        self.batch_name       = batch_name
        self.log_cb           = log_cb
        self.status_cb        = status_cb
        self.progress_cb      = progress_cb
        self.finished_cb      = finished_cb
        self.file_progress_cb = file_progress_cb
        self.backend          = None
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        self.backend = DownloadBackend(
            base_dir=self.base_dir, workers=self.workers,
            logger=self.log_cb, status_cb=self.status_cb, progress_cb=self.progress_cb,
            file_progress_cb=self.file_progress_cb,
        )
        if self.batch_name:
            self.backend._batch_name = self.batch_name
        summary = self.backend.download_selected(self.selected)
        if self.finished_cb:
            self.finished_cb(summary)

    def stop(self):
        if self.backend:
            self.backend.cancel()

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()


class CdnThumbnailLoader:
    """Background loader for gallery thumbnails."""

    def __init__(self, url: str, size: int, on_loaded):
        self.url       = url
        self.size      = size
        self.on_loaded = on_loaded

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            img = Image.open(BytesIO(data)).convert("RGB")
            img.thumbnail((self.size, self.size), Image.LANCZOS)
            self.on_loaded(img)
        except Exception:
            pass


# ── Thumbnail card ─────────────────────────────────────────────────────────────
class ThumbnailCard(ctk.CTkFrame):
    """Gallery card: image (aspect-ratio preserved) + hover overlay + checkbox."""

    _PLACEHOLDER_COLOR = "#211640"
    _OVERLAY_BG        = "#0d0b18"

    def __init__(self, parent, album_title: str, url: str,
                 filename: str, thumb_url: str, thumb_size: int = 160,
                 check_cb=None, **kw):
        super().__init__(
            parent, fg_color=C_CARD, corner_radius=R,
            border_width=2, border_color=C_ACC1, **kw,
        )
        self.album_title = album_title
        self.url         = url
        self.filename    = filename
        self.thumb_url   = thumb_url
        self.thumb_size  = thumb_size
        self._check_cb   = check_cb or (lambda: None)
        self._pil_image: Image.Image | None = None
        self._tk_image: ImageTk.PhotoImage | None = None
        self._checked    = True
        self._hide_job: str | None = None
        self._build()

    def _build(self):
        s = self.thumb_size
        self.configure(width=s + 16)

        scale = self._get_widget_scaling() if hasattr(self, "_get_widget_scaling") else 1.0
        self._phys_size = max(1, int(round(s * scale)))
        placeholder = Image.new("RGB", (self._phys_size, self._phys_size), self._PLACEHOLDER_COLOR)
        self._tk_image = ImageTk.PhotoImage(placeholder)

        # Fixed-size container for image + hover overlay
        self._img_frame = tk.Frame(
            self, bg=self._PLACEHOLDER_COLOR, width=s, height=s,
        )
        self._img_frame.pack(padx=8, pady=8)
        self._img_frame.pack_propagate(False)

        # Image label fills the container
        self._img_label = tk.Label(
            self._img_frame, image=self._tk_image, text="", bd=0,
            highlightthickness=0, bg=self._PLACEHOLDER_COLOR, cursor="hand2",
        )
        self._img_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._img_label.bind("<Button-1>", self._on_click)

        # Filename overlay label — placed at bottom of _img_frame on hover
        full_name = self.filename or os.path.basename(self.url)
        self._name_overlay = tk.Label(
            self._img_frame, text=full_name, bg=self._OVERLAY_BG, fg="#f0eeff",
            font=("Inter", 9), anchor="w", padx=4, pady=2,
            wraplength=max(60, self.thumb_size - 8),
            justify="left",
        )
        # not placed initially — shown on hover

        # Hover bindings on all visible surfaces
        for w in (self._img_label, self._img_frame, self._name_overlay):
            w.bind("<Enter>",  self._on_hover_enter, add="+")
            w.bind("<Leave>",  self._on_hover_leave, add="+")
        self._img_frame.bind("<Button-1>", self._on_click)
        self._name_overlay.bind("<Button-1>", self._on_click)

        self._check_var = ctk.BooleanVar(value=True)
        self._checkbox = ctk.CTkCheckBox(
            self, text="", variable=self._check_var,
            width=22, height=22, checkbox_width=20, checkbox_height=20,
            corner_radius=5, fg_color=C_ACC1, hover_color=C_ACC1_H,
            border_color=C_BORDER, command=self._on_checkbox_change,
        )
        self._checkbox.place(relx=1.0, rely=0.0, anchor="ne", x=-5, y=5)

    # ── hover handlers ────────────────────────────────────────────────────────
    def _on_hover_enter(self, _e=None):
        # Cancel any pending hide
        if self._hide_job is not None:
            self.after_cancel(self._hide_job)
            self._hide_job = None
        self._name_overlay.place(relx=0, rely=1.0, relwidth=1, anchor="sw")

    def _on_hover_leave(self, _e=None):
        # Delay slightly so moving between child widgets doesn't flicker
        if self._hide_job is not None:
            self.after_cancel(self._hide_job)
        self._hide_job = self.after(80, self._do_hide)

    def _do_hide(self):
        self._hide_job = None
        # Only hide if pointer is truly outside the card frame
        try:
            px, py = self.winfo_pointerxy()
            rx, ry = self.winfo_rootx(), self.winfo_rooty()
            if rx <= px <= rx + self.winfo_width() and ry <= py <= ry + self.winfo_height():
                return
        except Exception:
            pass
        self._name_overlay.place_forget()

    def _on_click(self, _e=None):
        self._check_var.set(not self._check_var.get())
        self._on_checkbox_change()

    def _on_checkbox_change(self):
        self._checked = self._check_var.get()
        self.configure(border_color=C_ACC1 if self._checked else C_BORDER)
        self._check_cb()

    # ── public API ────────────────────────────────────────────────────────────
    def set_image(self, pil_img: Image.Image):
        """Update card with real thumbnail, letterboxed to fixed physical size."""
        self._pil_image = pil_img
        ps = self._phys_size
        copy = pil_img.copy()
        copy.thumbnail((ps, ps), Image.LANCZOS)
        w, h = copy.size
        lb = Image.new("RGB", (ps, ps), self._PLACEHOLDER_COLOR)
        lb.paste(copy, ((ps - w) // 2, (ps - h) // 2))
        self._tk_image = ImageTk.PhotoImage(lb)
        self._img_label.configure(image=self._tk_image)

    def set_checked(self, value: bool):
        self._check_var.set(value)
        self._checked = value
        self.configure(border_color=C_ACC1 if value else C_BORDER)

    def is_checked(self) -> bool:
        return self._check_var.get()

    def resize_thumb(self, new_size: int):
        self.thumb_size = new_size
        self.configure(width=new_size + 16)
        self._img_frame.configure(width=new_size, height=new_size)
        scale = self._get_widget_scaling() if hasattr(self, "_get_widget_scaling") else 1.0
        self._phys_size = max(1, int(round(new_size * scale)))
        if self._pil_image:
            self.set_image(self._pil_image)
        else:
            placeholder = Image.new("RGB", (self._phys_size, self._phys_size), self._PLACEHOLDER_COLOR)
            self._tk_image = ImageTk.PhotoImage(placeholder)
            self._img_label.configure(image=self._tk_image)


# ── Gallery scrollable frame ───────────────────────────────────────────────────
class GalleryFrame(ctk.CTkScrollableFrame):
    """Responsive grid gallery with mousewheel scroll fix."""

    def __init__(self, parent, thumb_size: int = 160, on_check_changed=None, **kw):
        super().__init__(
            parent, fg_color=C_SURF,
            scrollbar_button_color=C_BORDER,
            scrollbar_button_hover_color=C_ACC1,
            corner_radius=R, **kw,
        )
        self._on_check_changed = on_check_changed or (lambda: None)
        self.thumb_size = thumb_size
        self._cards: list[ThumbnailCard] = []
        self._cols  = 5
        self._canvas_w: int = 0
        self._relayout_pending = False
        # Discrete fast scroll — 1 unit = 1px, ~50px per wheel notch.
        # Smooth animation caused image-tearing artifacts during partial canvas
        # repaints, so we use a single full repaint per notch instead.
        self._parent_canvas.configure(yscrollincrement=1)
        self.bind("<MouseWheel>", self._on_scroll)

    # ── mousewheel scroll fix ─────────────────────────────────────────────────
    def _fit_frame_dimensions_to_canvas(self, event):
        """Override CTkScrollableFrame hook that fires on canvas <Configure>.
        We piggyback here to get the true canvas viewport width without
        replacing the parent's binding (which constrains the inner frame width).
        """
        super()._fit_frame_dimensions_to_canvas(event)
        self._canvas_w = event.width
        if not self._relayout_pending:
            self._relayout_pending = True
            self.after(80, self._deferred_relayout)

    def _on_scroll(self, event):
        """Discrete scroll — single full canvas repaint per wheel notch."""
        notches = int(-1 * (event.delta / 120))
        self._parent_canvas.yview_scroll(notches * 50, "units")

    def _bind_scroll_recursive(self, widget):
        """Bind mousewheel on all descendants so child widgets don't eat scroll."""
        widget.bind("<MouseWheel>", self._on_scroll)
        for child in widget.winfo_children():
            self._bind_scroll_recursive(child)

    # ── card management ───────────────────────────────────────────────────────
    def add_card(self, album_title, url, filename, thumb_url) -> ThumbnailCard:
        card = ThumbnailCard(
            self, album_title, url, filename, thumb_url,
            thumb_size=self.thumb_size, check_cb=self._on_check_changed,
        )
        self._cards.append(card)
        idx  = len(self._cards) - 1
        r, c = divmod(idx, max(1, self._cols))
        card.grid(row=r, column=c, padx=6, pady=6, sticky="n")
        # Fix scroll for the new card and all its children
        self.after_idle(lambda _c=card: self._bind_scroll_recursive(_c))
        return card

    def clear(self):
        for card in self._cards:
            card.destroy()
        self._cards.clear()

    def set_all_checked(self, value: bool):
        for card in self._cards:
            card.set_checked(value)
        self._on_check_changed()

    def get_selected(self) -> list[tuple]:
        return [
            (c.album_title, {"url": c.url, "filename": c.filename})
            for c in self._cards if c.is_checked()
        ]

    def count(self) -> int:
        return len(self._cards)

    def set_thumb_size(self, size: int):
        self.thumb_size = size
        for card in self._cards:
            card.resize_thumb(size)
        self._recompute_layout()

    # ── responsive layout ─────────────────────────────────────────────────────
    def _deferred_relayout(self):
        self._relayout_pending = False
        self._recompute_layout()

    def _recompute_layout(self):
        w = self._canvas_w or self._parent_canvas.winfo_width()
        if w < 40:
            self.after(100, self._recompute_layout)  # retry when layout is ready
            return
        # event.width is in PHYSICAL pixels (DPI-scaled), but thumb_size is a
        # LOGICAL value. We must scale the card slot to physical pixels too,
        # otherwise on 125%/150% displays we overestimate the column count.
        card_slot_logical = self.thumb_size + 16 + 12  # thumb + card pad + grid padx
        card_slot_physical = self._apply_widget_scaling(card_slot_logical)
        new_cols  = max(1, int(w // card_slot_physical))
        if new_cols != self._cols:
            self._cols = new_cols
            self._relayout()

    def scroll_to_top(self):
        self._parent_canvas.yview_moveto(0)

    def _relayout(self):
        for i, card in enumerate(self._cards):
            r, c = divmod(i, max(1, self._cols))
            card.grid(row=r, column=c, padx=6, pady=6, sticky="n")


# ── Main window ───────────────────────────────────────────────────────────────
class DownloaderCtkWindow(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.settings    = load_json(SETTINGS_FILE, {})
        self.lang: str   = self.settings.get("lang", "ru")
        if self.lang not in I18N:
            self.lang = "ru"

        self._worker: PreviewWorker | DownloadWorker | None = None
        self._batch_name: str | None = None
        self._queued_urls: list[str] = []
        self._queued_set:  set[str]  = set()
        self._thumb_size: int        = 160
        self._log_job_id             = None
        self._pending_cards: list    = []
        self._flush_job: str | None  = None
        # Per-file progress tracking (in-place log update)
        self._engine_progress_line: int | None = None
        self._engine_progress_filename: str    = ""

        self.title("JPG6 Downloader Pro")
        self.geometry("1380x880")
        self.minsize(960, 640)
        self.configure(fg_color=C_BG)

        self._build_ui()
        self._load_settings()
        self._apply_translations()
        self._schedule_log_refresh()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_content()

    # ─────────────────── SIDEBAR  (settings only) ────────────────────────────
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=C_SIDE, corner_radius=0, width=268)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        row = 0

        # Logo
        self._lbl_title = ctk.CTkLabel(
            sb, text="", font=FONT_TITLE, text_color=C_TEXT,
        )
        self._lbl_title.grid(row=row, column=0, padx=20, pady=(24, 0), sticky="w")
        row += 1

        self._lbl_sub = ctk.CTkLabel(sb, text="", font=FONT_SUB, text_color=C_MUTED)
        self._lbl_sub.grid(row=row, column=0, padx=20, pady=(2, 14), sticky="w")
        row += 1

        self._sep(sb, row); row += 1

        # Workers
        self._lbl_workers = ctk.CTkLabel(
            sb, text="", font=FONT_LBL, text_color=C_TEXT,
        )
        self._lbl_workers.grid(row=row, column=0, padx=20, pady=(14, 4), sticky="w")
        row += 1

        wf = ctk.CTkFrame(sb, fg_color="transparent")
        wf.grid(row=row, column=0, padx=20, pady=(0, 6), sticky="ew")
        wf.grid_columnconfigure(1, weight=1)
        row += 1

        ctk.CTkButton(
            wf, text="\u2212", width=36, height=36, corner_radius=10,
            fg_color=C_BORDER, hover_color=C_ACC1_H,
            text_color=C_TEXT, font=FONT_BTN,
            command=self._workers_dec,
        ).grid(row=0, column=0, padx=(0, 6))

        self._workers_var = ctk.StringVar(value="3")
        ctk.CTkEntry(
            wf, textvariable=self._workers_var, width=60, height=36,
            corner_radius=10, fg_color=C_CARD, border_color=C_BORDER,
            text_color=C_TEXT, justify="center", font=("Inter", 15, "bold"),
        ).grid(row=0, column=1, sticky="ew")

        ctk.CTkButton(
            wf, text="+", width=36, height=36, corner_radius=10,
            fg_color=C_BORDER, hover_color=C_ACC1_H,
            text_color=C_TEXT, font=FONT_BTN,
            command=self._workers_inc,
        ).grid(row=0, column=2, padx=(6, 0))

        # Language
        self._lbl_lang = ctk.CTkLabel(sb, text="", font=FONT_LBL, text_color=C_TEXT)
        self._lbl_lang.grid(row=row, column=0, padx=20, pady=(10, 4), sticky="w")
        row += 1

        self._lang_var = ctk.StringVar(value="\u0420\u0443\u0441\u0441\u043a\u0438\u0439")
        self._lang_menu = ctk.CTkOptionMenu(
            sb, values=["\u0420\u0443\u0441\u0441\u043a\u0438\u0439", "English"],
            variable=self._lang_var, command=self._on_lang_changed,
            fg_color=C_CARD, button_color=C_ACC1, button_hover_color=C_ACC1_H,
            dropdown_fg_color=C_CARD, dropdown_text_color=C_TEXT,
            dropdown_hover_color=C_BORDER, text_color=C_TEXT,
            font=FONT_LBL, corner_radius=R, height=38,
        )
        self._lang_menu.grid(row=row, column=0, padx=20, pady=(0, 6), sticky="ew")
        row += 1

        self._sep(sb, row); row += 1

        # Folder
        self._lbl_folder = ctk.CTkLabel(sb, text="", font=FONT_LBL, text_color=C_TEXT)
        self._lbl_folder.grid(row=row, column=0, padx=20, pady=(14, 4), sticky="w")
        row += 1

        self._dir_var = ctk.StringVar()
        ctk.CTkEntry(
            sb, textvariable=self._dir_var, height=36, corner_radius=R,
            fg_color=C_CARD, border_color=C_BORDER, text_color=C_TEXT,
            placeholder_text="\u2026", font=FONT_SM,
        ).grid(row=row, column=0, padx=20, pady=(0, 6), sticky="ew")
        row += 1

        self._btn_pick = ctk.CTkButton(
            sb, text="", height=38, corner_radius=R,
            fg_color=C_CARD, hover_color=C_BORDER,
            text_color=C_TEXT, font=FONT_LBL,
            image=get_icon(ICO_FOLDER, 14), compound="left",
            command=self.pick_folder,
        )
        self._btn_pick.grid(row=row, column=0, padx=20, pady=(0, 6), sticky="ew")
        row += 1

        self._btn_save = ctk.CTkButton(
            sb, text="", height=40, corner_radius=R,
            fg_color=C_ACC1, hover_color=C_ACC1_H,
            text_color="#ffffff", font=FONT_BTN,
            image=get_icon(ICO_SAVE, 14), compound="left",
            command=self.save_settings,
        )
        self._btn_save.grid(row=row, column=0, padx=20, pady=(0, 4), sticky="ew")
        row += 1

        # Spacer
        spacer = ctk.CTkFrame(sb, fg_color="transparent")
        spacer.grid(row=row, column=0, sticky="nsew")
        sb.grid_rowconfigure(row, weight=1)

    # ─────────────────────────── CONTENT ──────────────────────────────────────
    def _build_content(self):
        c = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        c.grid(row=0, column=1, sticky="nsew")
        c.grid_columnconfigure(0, weight=1)
        # row 0: top action bar  (URL + Add + Import + Scan + Clear)
        # row 1: gallery toolbar (Select + Size + Clear gallery)
        # row 2: gallery         (expands)
        # row 3: bottom bar      (progress + status + Download + Stop)
        # row 4: logs
        c.grid_rowconfigure(2, weight=3)
        c.grid_rowconfigure(4, weight=1)

        # ── row 0: top action bar ─────────────────────────────────────────────
        tab = ctk.CTkFrame(c, fg_color=C_CARD, corner_radius=R)
        tab.grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=0)

        inner = ctk.CTkFrame(tab, fg_color="transparent")
        inner.grid(row=0, column=0, padx=8, pady=8, sticky="ew")
        inner.grid_columnconfigure(0, weight=1)

        self._url_var = ctk.StringVar()
        self._url_entry = ctk.CTkEntry(
            inner, textvariable=self._url_var, height=40, corner_radius=R,
            fg_color=C_SURF, border_color=C_BORDER, text_color=C_TEXT,
            placeholder_text="\u2026", font=FONT_LBL,
        )
        self._url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._url_entry.bind("<Return>", lambda _: self.add_url())
        self._setup_url_entry_bindings()

        self._btn_paste = ctk.CTkButton(
            inner, text="", width=44, height=40, corner_radius=R,
            fg_color=C_SURF, hover_color=C_BORDER,
            text_color="#ffffff", font=FONT_BTN,
            image=get_icon(ICO_PASTE, 14), compound="left",
            command=self._url_smart_paste,
        )
        self._btn_paste.grid(row=0, column=1, padx=(0, 4))

        self._btn_add = ctk.CTkButton(
            inner, text="", width=116, height=40, corner_radius=R,
            fg_color=C_BORDER, hover_color=C_ACC1,
            text_color="#ffffff", font=FONT_BTN,
            image=get_icon(ICO_ADD, 14), compound="left",
            command=self.add_url,
        )
        self._btn_add.grid(row=0, column=2, padx=(0, 4))

        # separator
        ctk.CTkFrame(inner, width=1, height=36, fg_color=C_BORDER).grid(
            row=0, column=3, padx=(0, 4),
        )

        self._btn_import = ctk.CTkButton(
            inner, text="", width=130, height=40, corner_radius=R,
            fg_color=C_SURF, hover_color=C_BORDER,
            text_color="#ffffff", font=FONT_BTN,
            image=get_icon(ICO_IMPORT, 14), compound="left",
            command=self.import_urls,
        )
        self._btn_import.grid(row=0, column=4, padx=(0, 4))

        self._btn_scan = ctk.CTkButton(
            inner, text="", width=148, height=40, corner_radius=R,
            fg_color=C_ACC1, hover_color=C_ACC1_H,
            text_color="#ffffff", font=FONT_BTN,
            image=get_icon(ICO_SCAN, 14), compound="left",
            command=self.start_scan,
        )
        self._btn_scan.grid(row=0, column=5, padx=(0, 4))

        self._btn_clear_q = ctk.CTkButton(
            inner, text="", width=116, height=40, corner_radius=R,
            fg_color=C_SURF, hover_color=C_STOP,
            text_color="#ffffff", font=FONT_BTN,
            image=get_icon(ICO_CLEAR, 14), compound="left",
            command=self.clear_queue,
        )
        self._btn_clear_q.grid(row=0, column=6)

        # ── queue panel (inside tab, row 1) — scrollable list of queued URLs ──
        self._queue_panel = ctk.CTkScrollableFrame(
            tab, height=80, fg_color=C_SURF, corner_radius=8,
            scrollbar_button_color=C_BORDER,
            scrollbar_button_hover_color=C_ACC1,
        )
        self._queue_panel.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")
        self._queue_panel.grid_columnconfigure(0, weight=1)
        self._queue_panel.grid_remove()   # hidden until queue has entries

        # ── row 1: gallery toolbar ────────────────────────────────────────────
        gth = ctk.CTkFrame(c, fg_color="transparent")
        gth.grid(row=1, column=0, padx=16, pady=(0, 6), sticky="ew")

        self._lbl_gallery = ctk.CTkLabel(
            gth, text="", font=("Inter", 12, "bold"), text_color=C_MUTED,
        )
        self._lbl_gallery.pack(side="left", padx=(2, 6))

        self._lbl_gallery_count = ctk.CTkLabel(
            gth, text="", font=FONT_SM, text_color=C_ACC2,
        )
        self._lbl_gallery_count.pack(side="left", padx=(0, 10))

        self._btn_sel_all = ctk.CTkButton(
            gth, text="", width=108, height=28, corner_radius=8,
            fg_color=C_CARD, hover_color=C_BORDER,
            text_color="#ffffff", font=FONT_SM,
            image=get_icon(ICO_CHECK, 12), compound="left",
            command=lambda: self.gallery.set_all_checked(True),
        )
        self._btn_sel_all.pack(side="left", padx=(0, 3))

        self._btn_desel = ctk.CTkButton(
            gth, text="", width=94, height=28, corner_radius=8,
            fg_color=C_CARD, hover_color=C_BORDER,
            text_color="#ffffff", font=FONT_SM,
            image=get_icon(ICO_CLOSE, 12), compound="left",
            command=lambda: self.gallery.set_all_checked(False),
        )
        self._btn_desel.pack(side="left", padx=(0, 10))

        # Thumb size buttons
        self._btn_sz: dict[int, ctk.CTkButton] = {}
        for key, sz in (("size_small", 80), ("size_medium", 120), ("size_large", 180)):
            is_active = sz == self._thumb_size
            btn = ctk.CTkButton(
                gth, text="", width=38, height=28, corner_radius=8,
                fg_color=C_ACC1 if is_active else C_CARD,
                hover_color=C_ACC1_H,
                text_color="#ffffff", font=FONT_SM,
                command=lambda s=sz: self._set_thumb_size(s),
            )
            btn.pack(side="left", padx=(0, 3))
            self._btn_sz[sz] = btn

        self._btn_clear_gal = ctk.CTkButton(
            gth, text="", width=112, height=28, corner_radius=8,
            fg_color=C_CARD, hover_color=C_STOP,
            text_color="#ffffff", font=FONT_SM,
            image=get_icon(ICO_TRASH, 12), compound="left",
            command=self._clear_gallery,
        )
        self._btn_clear_gal.pack(side="left", padx=(6, 0))

        # ── row 2: gallery ────────────────────────────────────────────────────
        self.gallery = GalleryFrame(
            c, thumb_size=self._thumb_size,
            on_check_changed=lambda: self.after(0, self._update_gallery_count),
        )
        self.gallery.grid(row=2, column=0, padx=16, pady=(0, 8), sticky="nsew")

        # ── row 3: bottom action bar ──────────────────────────────────────────
        bot = ctk.CTkFrame(c, fg_color=C_CARD, corner_radius=R)
        bot.grid(row=3, column=0, padx=16, pady=(0, 8), sticky="ew")
        bot.grid_columnconfigure(0, weight=1)

        bot_inner = ctk.CTkFrame(bot, fg_color="transparent")
        bot_inner.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        bot_inner.grid_columnconfigure(0, weight=1)

        self._progress = ctk.CTkProgressBar(
            bot_inner, height=14, corner_radius=7,
            fg_color=C_BORDER, progress_color=C_ACC1,
            mode="determinate",
        )
        self._progress.set(0.0)
        self._progress.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self._lbl_status = ctk.CTkLabel(
            bot_inner, text="", width=240, font=FONT_LBL,
            text_color=C_ACC2, anchor="w",
        )
        self._lbl_status.grid(row=0, column=1, padx=(0, 10))

        self._btn_start = ctk.CTkButton(
            bot_inner, text="", width=172, height=38, corner_radius=R,
            fg_color=C_GREEN, hover_color=C_GREEN_H,
            text_color="#ffffff", font=FONT_BTN,
            image=get_icon(ICO_DOWNLOAD, 15), compound="left",
            command=self.start_download_selected,
            state="disabled",
        )
        self._btn_start.grid(row=0, column=2, padx=(0, 6))

        self._btn_stop = ctk.CTkButton(
            bot_inner, text="", width=100, height=38, corner_radius=R,
            fg_color=C_STOP, hover_color=C_STOP_H,
            text_color="#ffffff", font=FONT_BTN,
            image=get_icon(ICO_STOP, 15), compound="left",
            command=self.stop_worker,
            state="disabled",
        )
        self._btn_stop.grid(row=0, column=3)

        # ── row 4: logs ───────────────────────────────────────────────────────
        self._log_tabs = ctk.CTkTabview(
            c, height=195,
            fg_color=C_CARD,
            segmented_button_fg_color=C_SURF,
            segmented_button_selected_color=C_ACC1,
            segmented_button_selected_hover_color=C_ACC1_H,
            segmented_button_unselected_color=C_SURF,
            segmented_button_unselected_hover_color=C_BORDER,
            text_color=C_TEXT, corner_radius=R,
            border_color=C_BORDER, border_width=1,
        )
        self._log_tabs.grid(row=4, column=0, padx=16, pady=(0, 14), sticky="nsew")

        for tab_name, attr in (
            ("Engine", "_log_engine"),
            ("Errors", "_log_error"),
            ("Debug",  "_log_debug"),
        ):
            self._log_tabs.add(tab_name)
            tf = self._log_tabs.tab(tab_name)
            tf.grid_columnconfigure(0, weight=1)
            tf.grid_rowconfigure(0, weight=1)
            txt = ctk.CTkTextbox(
                tf, font=FONT_MONO, fg_color=C_SURF, text_color="#b8d4aa",
                scrollbar_button_color=C_BORDER,
                scrollbar_button_hover_color=C_ACC1,
                corner_radius=10, wrap="word", state="disabled",
            )
            txt.grid(row=0, column=0, sticky="nsew")
            setattr(self, attr, txt)

    @staticmethod
    def _sep(parent, row: int):
        ctk.CTkFrame(parent, height=1, fg_color=C_BORDER).grid(
            row=row, column=0, padx=20, pady=4, sticky="ew",
        )

    # ── Workers spinbox ───────────────────────────────────────────────────────
    def _get_workers(self) -> int:
        try:
            return max(1, min(8, int(self._workers_var.get())))
        except ValueError:
            return 3

    def _workers_dec(self):
        self._workers_var.set(str(max(1, self._get_workers() - 1)))

    def _workers_inc(self):
        self._workers_var.set(str(min(8, self._get_workers() + 1)))

    # ── Settings ──────────────────────────────────────────────────────────────
    def _load_settings(self):
        base    = self.settings.get("base_dir", os.path.join(SCRIPT_DIR, "downloads"))
        workers = int(self.settings.get("workers", 3))
        lang    = self.settings.get("lang", "ru")
        self._dir_var.set(base)
        self._workers_var.set(str(max(1, min(8, workers))))
        if lang in I18N:
            self.lang = lang
        self._lang_var.set(I18N[self.lang].get("lang_" + self.lang, "\u0420\u0443\u0441\u0441\u043a\u0438\u0439"))

    def save_settings(self, quiet: bool = False):
        self.settings["base_dir"] = (
            self._dir_var.get().strip() or os.path.join(SCRIPT_DIR, "downloads")
        )
        self.settings["workers"] = self._get_workers()
        self.settings["lang"]    = self.lang
        save_json(SETTINGS_FILE, self.settings)
        if not quiet:
            self._set_status(self._t("settings_saved"))

    def pick_folder(self):
        cur = self._dir_var.get().strip() or SCRIPT_DIR
        folder = filedialog.askdirectory(
            title=self._t("pick_folder_dialog"), initialdir=cur, parent=self,
        )
        if folder:
            self._dir_var.set(folder)

    # ── I18N ──────────────────────────────────────────────────────────────────
    def _t(self, key: str, **kwargs) -> str:
        table = I18N.get(self.lang, I18N["ru"])
        text  = table.get(key, key)
        return text.format(**kwargs) if kwargs else text

    def _on_lang_changed(self, value: str):
        new = "en" if value == I18N["en"]["lang_en"] else "ru"
        if new != self.lang:
            self.lang = new
            self._apply_translations()
            self.save_settings(quiet=True)

    def _apply_translations(self):
        self.title(self._t("window_title"))
        self._lbl_title.configure(text=self._t("app_title"))
        self._lbl_sub.configure(text=self._t("app_subtitle"))
        self._lbl_workers.configure(text=self._t("workers"))
        self._lbl_lang.configure(text=self._t("language"))
        self._lbl_folder.configure(text=self._t("folder_label"))
        self._btn_pick.configure(text="  " + self._t("pick_folder"))
        self._btn_save.configure(text="  " + self._t("save_settings"))
        # top bar
        self._btn_add.configure(text="  " + self._t("add"))
        self._btn_import.configure(text="  " + self._t("import_txt"))
        self._btn_scan.configure(text="  " + self._t("scan_preview"))
        self._btn_clear_q.configure(text="  " + self._t("clear_queue"))
        self._url_entry.configure(placeholder_text=self._t("url_placeholder"))
        # gallery toolbar
        self._lbl_gallery.configure(text=self._t("gallery_title"))
        self._btn_sel_all.configure(text="  " + self._t("select_all"))
        self._btn_desel.configure(text="  " + self._t("deselect_all"))
        self._btn_sz[80].configure(text=self._t("size_small"))
        self._btn_sz[120].configure(text=self._t("size_medium"))
        self._btn_sz[180].configure(text=self._t("size_large"))
        self._btn_clear_gal.configure(text="  " + self._t("clear_gallery"))
        # bottom bar
        self._btn_start.configure(text="  " + self._t("start_download"))
        self._btn_stop.configure(text="  " + self._t("stop"))
        # lang menu
        self._lang_menu.configure(values=[self._t("lang_ru"), self._t("lang_en")])
        self._lang_var.set(self._t("lang_" + self.lang))
        # status
        if not self._lbl_status.cget("text").strip():
            self._set_status(self._t("status_ready"))

    # ── Queue management ──────────────────────────────────────────────────────

    def _setup_url_entry_bindings(self):
        """Bind Ctrl+V smart paste, Ctrl+A, right-click context menu."""
        # Inner tk.Entry for low-level bindings
        inner = self._url_entry._entry
        inner.bind("<Control-a>", lambda e: (inner.selection_range(0, "end"), "break")[1])
        inner.bind("<Control-A>", lambda e: (inner.selection_range(0, "end"), "break")[1])
        # Smart paste on Ctrl+V / Ctrl+Shift+V
        for seq in ("<Control-v>", "<Control-V>"):
            self._url_entry.bind(seq, self._url_smart_paste)
            inner.bind(seq, self._url_smart_paste)
        # Right-click context menu
        for seq in ("<Button-3>",):
            self._url_entry.bind(seq, self._show_url_context_menu)
            inner.bind(seq, self._show_url_context_menu)

    def _url_smart_paste(self, event=None):
        """Smart paste from clipboard.
        - Multiple http lines → add all to queue directly.
        - Single http URL → put in entry field.
        - Anything else → standard text insert.
        """
        try:
            clip = self.clipboard_get()
        except Exception:
            return "break"

        lines = [ln.strip() for ln in clip.splitlines() if ln.strip().startswith("http")]

        if len(lines) > 1:
            added = 0
            for line in lines:
                if line not in self._queued_set:
                    self._queued_urls.append(line)
                    self._queued_set.add(line)
                    added += 1
            self._url_var.set("")
            self._set_status(self._t("pasted_multi", count=added))
            self._rebuild_queue_panel()
        elif len(lines) == 1:
            self._url_var.set(lines[0])
            try:
                self._url_entry._entry.icursor("end")
            except Exception:
                pass
        else:
            # Not a URL — do plain insert at cursor
            try:
                inner = self._url_entry._entry
                if inner.selection_present():
                    inner.delete("sel.first", "sel.last")
                inner.insert("insert", clip)
            except Exception:
                pass
        return "break"

    def _show_url_context_menu(self, event):
        """Right-click context menu for the URL entry."""
        inner = self._url_entry._entry
        try:
            has_sel = bool(inner.selection_present())
        except Exception:
            has_sel = False
        try:
            clip_text = self.clipboard_get()
            clip_has_content = bool(clip_text.strip())
        except Exception:
            clip_text = ""
            clip_has_content = False

        menu = tk.Menu(
            self, tearoff=0,
            bg=C_CARD, fg=C_TEXT,
            activebackground=C_ACC1, activeforeground="#ffffff",
            bd=0, relief="flat", font=FONT_SM,
        )
        menu.add_command(
            label=self._t("ctx_cut"),
            command=lambda: inner.event_generate("<<Cut>>"),
            state="normal" if has_sel else "disabled",
        )
        menu.add_command(
            label=self._t("ctx_copy"),
            command=lambda: inner.event_generate("<<Copy>>"),
            state="normal" if has_sel else "disabled",
        )
        menu.add_command(
            label=self._t("ctx_paste"),
            command=self._url_smart_paste,
            state="normal" if clip_has_content else "disabled",
        )
        menu.add_separator()
        menu.add_command(
            label=self._t("ctx_select_all"),
            command=lambda: inner.selection_range(0, "end"),
        )
        menu.add_command(
            label=self._t("ctx_clear"),
            command=lambda: self._url_var.set(""),
        )
        menu.tk_popup(event.x_root, event.y_root)

    def add_url(self):
        url = self._url_var.get().strip()
        if not url:
            return
        if not url.startswith("http"):
            self._set_status(self._t("invalid_url"))
            return
        if url not in self._queued_set:
            self._queued_urls.append(url)
            self._queued_set.add(url)
        self._url_var.set("")
        self._set_status(self._t("queued_count", count=len(self._queued_urls)))
        self._rebuild_queue_panel()

    def clear_queue(self):
        self._queued_urls.clear()
        self._queued_set.clear()
        self._batch_name = None
        self._progress.set(0.0)
        self._set_status(self._t("queue_cleared"))
        self._rebuild_queue_panel()

    def import_urls(self):
        paths = filedialog.askopenfilenames(
            title=self._t("import_file_dialog"),
            initialdir=SCRIPT_DIR,
            filetypes=[("Text files", "*.txt")],
            parent=self,
        )
        if not paths:
            return
        # batch_name: single file → use filename; multiple → None (no shared name)
        if len(paths) == 1:
            self._batch_name = os.path.splitext(os.path.basename(paths[0]))[0]
        else:
            self._batch_name = None
        added = 0
        for path in paths:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line.startswith("http"):
                        continue
                    if line not in self._queued_set:
                        self._queued_urls.append(line)
                        self._queued_set.add(line)
                    added += 1
        self._set_status(self._t("imported_count", count=added))
        self._rebuild_queue_panel()

    # ── Queue panel ───────────────────────────────────────────────────────────
    def _rebuild_queue_panel(self):
        """Re-render the queue URL list. Shows panel when queue non-empty, hides when empty."""
        # Destroy all children
        for widget in self._queue_panel.winfo_children():
            widget.destroy()

        if not self._queued_urls:
            self._queue_panel.grid_remove()
            return

        self._queue_panel.grid()
        MAX_DISPLAY = 50
        display_urls = self._queued_urls[:MAX_DISPLAY]

        for i, url in enumerate(display_urls):
            row_frame = ctk.CTkFrame(self._queue_panel, fg_color="transparent")
            row_frame.grid(row=i, column=0, sticky="ew", padx=2, pady=1)
            row_frame.grid_columnconfigure(0, weight=1)

            # Truncate long URLs for display
            display_text = url if len(url) <= 80 else url[:77] + "…"
            ctk.CTkLabel(
                row_frame, text=display_text, font=FONT_SM, text_color=C_MUTED,
                fg_color="transparent", anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=(4, 4))

            ctk.CTkButton(
                row_frame, text="×", width=24, height=20, corner_radius=6,
                fg_color=C_BORDER, hover_color=C_STOP,
                text_color="#ffffff", font=("Inter", 12, "bold"),
                command=lambda u=url: self._remove_queued_url(u),
            ).grid(row=0, column=1, padx=(0, 2))

        extra = len(self._queued_urls) - MAX_DISPLAY
        if extra > 0:
            ctk.CTkLabel(
                self._queue_panel,
                text=f"… и ещё {extra}",
                font=FONT_SM, text_color=C_MUTED, fg_color="transparent", anchor="w",
            ).grid(row=MAX_DISPLAY, column=0, sticky="ew", padx=6, pady=(0, 2))

    def _remove_queued_url(self, url: str):
        """Remove a single URL from the queue and refresh the panel."""
        try:
            self._queued_urls.remove(url)
        except ValueError:
            pass
        self._queued_set.discard(url)
        self._set_status(self._t("queued_count", count=len(self._queued_urls)))
        self._rebuild_queue_panel()
    def _set_thumb_size(self, size: int):
        self._thumb_size = size
        self.gallery.set_thumb_size(size)
        for sz, btn in self._btn_sz.items():
            if sz == size:
                btn.configure(fg_color=C_ACC1, text_color="#ffffff")
            else:
                btn.configure(fg_color=C_CARD, text_color=C_TEXT)

    def _clear_gallery(self):
        if self._flush_job:
            self.after_cancel(self._flush_job)
            self._flush_job = None
        self._pending_cards.clear()
        self.gallery.clear()
        self.gallery.scroll_to_top()
        self._btn_start.configure(state="disabled")
        self._update_gallery_count()

    def _update_gallery_count(self):
        total    = self.gallery.count()
        selected = sum(1 for c in self.gallery._cards if c.is_checked())
        if total == 0:
            self._lbl_gallery_count.configure(text="")
        else:
            self._lbl_gallery_count.configure(text=f"{selected} / {total}")

    # ── Scan workflow ─────────────────────────────────────────────────────────
    def start_scan(self):
        if self._worker and self._worker.is_alive():
            self._set_status(self._t("backend_running"))
            return
        # Auto-add whatever is typed/pasted in the entry field
        if self._url_var.get().strip():
            self.add_url()
        if not self._queued_urls:
            self._set_status(self._t("queue_empty"))
            return

        self.save_settings()
        base_dir = self._dir_var.get().strip() or os.path.join(SCRIPT_DIR, "downloads")
        workers  = self._get_workers()

        self._clear_log("engine")
        self._progress.configure(mode="indeterminate")
        self._progress.start()
        self._clear_gallery()
        self._set_ui_busy(True)
        self._set_status(self._t("starting_scan"))

        urls_to_scan = list(self._queued_urls)
        # Hide the queue panel once scan is launched — gallery takes over
        self._queued_urls.clear()
        self._queued_set.clear()
        self._rebuild_queue_panel()

        self._worker = PreviewWorker(
            urls_to_scan, base_dir, workers,
            batch_name=self._batch_name,
            image_found_cb=lambda at, u, fn, tu: self.after(
                0, lambda at=at, u=u, fn=fn, tu=tu: self._on_image_found(at, u, fn, tu),
            ),
            status_cb=lambda txt: self.after(0, lambda t=txt: self._set_status(t)),
            finished_cb=lambda cnt: self.after(0, lambda c=cnt: self._on_scan_finished(c)),
            log_cb=lambda msg: self.after(0, lambda m=msg: self._append_engine_log(m)),
        )
        self._worker.start()

    def _on_image_found(self, album_title, url, filename, thumb_url):
        self._pending_cards.append((album_title, url, filename, thumb_url))
        if self._flush_job is None:
            self._flush_job = self.after(80, self._flush_cards)

    def _flush_cards(self):
        self._flush_job = None
        batch, self._pending_cards = self._pending_cards[:25], self._pending_cards[25:]
        for album_title, url, filename, thumb_url in batch:
            card = self.gallery.add_card(album_title, url, filename, thumb_url)
            CdnThumbnailLoader(
                thumb_url or url, self._thumb_size,
                on_loaded=lambda img, _c=card: self.after(
                    0, lambda i=img, c=_c: c.set_image(i),
                ),
            ).start()
        if self._pending_cards:
            self._flush_job = self.after(80, self._flush_cards)
        self._update_gallery_count()

    def _on_scan_finished(self, count: int):
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress.set(1.0 if count > 0 else 0.0)
        self._set_ui_busy(False)
        self._worker = None
        if count > 0:
            self._btn_start.configure(state="normal")
        self._set_status(self._t("scan_done", count=count))
        self._update_gallery_count()

    # ── Download workflow ─────────────────────────────────────────────────────
    def start_download_selected(self):
        if self._worker and self._worker.is_alive():
            self._set_status(self._t("backend_running"))
            return
        selected = self.gallery.get_selected()
        if not selected:
            self._set_status(self._t("no_selected"))
            return

        self.save_settings()
        base_dir = self._dir_var.get().strip() or os.path.join(SCRIPT_DIR, "downloads")
        workers  = self._get_workers()

        self._clear_log("engine")
        self._progress.configure(mode="determinate")
        self._progress.set(0.0)
        self._set_ui_busy(True)
        self._set_status(self._t("starting_download"))

        self._worker = DownloadWorker(
            selected, base_dir, workers,
            batch_name=self._batch_name,
            log_cb=lambda msg: self.after(0, lambda m=msg: self._append_engine_log(m)),
            status_cb=lambda txt: self.after(0, lambda t=txt: self._set_status(t)),
            progress_cb=lambda d, t: self.after(0, lambda d=d, t=t: self._on_progress(d, t)),
            finished_cb=lambda s: self.after(0, lambda s=s: self._on_download_finished(s)),
            file_progress_cb=lambda fn, d, t: self.after(
                0, lambda fn=fn, d=d, t=t: self._on_file_progress(fn, d, t)
            ),
        )
        self._worker.start()

    def stop_worker(self):
        if self._worker:
            self._worker.stop()
            self._set_status(self._t("stopping"))

    # ── UI state helpers ──────────────────────────────────────────────────────
    def _set_ui_busy(self, busy: bool):
        on  = "normal"
        off = "disabled"
        self._btn_scan.configure(state=off if busy else on)
        self._btn_import.configure(state=off if busy else on)
        self._btn_add.configure(state=off if busy else on)
        self._btn_stop.configure(state=on if busy else off)
        if busy:
            self._btn_start.configure(state=off)

    def _set_status(self, text: str):
        self._lbl_status.configure(text=text)

    def _append_engine_log(self, msg: str):
        """Append a line to Engine log.
        If a progress line is active, replace it with this (final) line."""
        tw = self._log_engine._textbox
        tw.configure(state="normal")
        if self._engine_progress_line is not None:
            # Replace the in-progress line with the completed line
            line = self._engine_progress_line
            tw.delete(f"{line}.0", f"{line}.end")
            tw.insert(f"{line}.0", msg)
            self._engine_progress_line = None
            self._engine_progress_filename = ""
        else:
            tw.insert("end", msg + "\n")
        tw.see("end")
        tw.configure(state="disabled")

    def _engine_start_progress_line(self, msg: str):
        """Insert a new progress line and remember its line number for in-place updates."""
        tw = self._log_engine._textbox
        tw.configure(state="normal")
        tw.insert("end", msg + "\n")
        # Line number = total lines - 2 (last line is empty due to trailing \n)
        line_num = int(tw.index("end").split(".")[0]) - 2
        self._engine_progress_line = max(1, line_num)
        tw.see("end")
        tw.configure(state="disabled")

    def _engine_update_progress_line(self, msg: str):
        """Update the active progress line in-place."""
        if self._engine_progress_line is None:
            return
        tw = self._log_engine._textbox
        tw.configure(state="normal")
        line = self._engine_progress_line
        tw.delete(f"{line}.0", f"{line}.end")
        tw.insert(f"{line}.0", msg)
        tw.see("end")
        tw.configure(state="disabled")

    def _on_file_progress(self, filename: str, done: int, total: int):
        """Handle per-file download progress — called on main thread via after()."""
        if total <= 0:
            return
        pct = int(done / total * 100)
        bar_w = 14
        filled = int(done / total * bar_w)
        bar = "█" * filled + "░" * (bar_w - filled)
        size_done = format_size(done)
        size_total = format_size(total)
        name_part = filename[:36].ljust(36) if len(filename) > 36 else filename.ljust(36)
        msg = f"⬇  {name_part}  {size_done:>9} / {size_total:<9}  [{bar}]  {pct:3d}%"

        if done == 0:
            # New file starting — reset tracking if different file
            self._engine_progress_line = None
            self._engine_progress_filename = filename
            self._engine_start_progress_line(msg)
        elif self._engine_progress_filename == filename and self._engine_progress_line is not None:
            self._engine_update_progress_line(msg)

    def _on_progress(self, done: int, total: int):
        if total <= 0:
            self._progress.set(0.0)
            return
        self._progress.set(max(0.0, min(1.0, done / total)))

    def _on_download_finished(self, summary: dict):
        self._progress.set(1.0)
        self._set_ui_busy(False)
        self._btn_start.configure(state="normal")
        self._worker = None
        key = "cancelled_summary" if summary.get("cancelled") else "done_summary"
        self._set_status(self._t(
            key,
            albums=summary.get("albums", 0),
            downloaded=summary.get("downloaded", 0),
            skipped=summary.get("skipped", 0),
            errors=summary.get("errors", 0),
        ))

    # ── Log refresh ───────────────────────────────────────────────────────────
    def _schedule_log_refresh(self):
        self._refresh_logs()
        self._log_job_id = self.after(1500, self._schedule_log_refresh)

    def _refresh_logs(self):
        self._set_log_from_file(self._log_error, ERROR_LOG_FILE)
        self._set_log_from_file(self._log_debug, DEBUG_LOG_FILE)

    def _set_log_from_file(self, widget: ctk.CTkTextbox, path: str):
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                data = fh.read()
            widget.configure(state="normal")
            if widget.get("1.0", "end-1c") != data:
                widget.delete("1.0", "end")
                widget.insert("1.0", data)
                widget.see("end")
            widget.configure(state="disabled")
        except Exception:
            pass

    def _clear_log(self, which: str):
        widget = getattr(self, f"_log_{which}", None)
        if widget:
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.configure(state="disabled")

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def on_close(self):
        if self._log_job_id:
            self.after_cancel(self._log_job_id)
        if self._worker:
            self._worker.stop()
        self.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────
def run_ctk() -> int:
    app = DownloaderCtkWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_ctk())

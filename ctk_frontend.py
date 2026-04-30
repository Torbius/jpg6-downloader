"""ctk_frontend.py — CustomTkinter Material Design 3 UI for JPG6 Downloader."""
from __future__ import annotations

import json
import os
import sys
import threading
import urllib.request
from io import BytesIO
from tkinter import filedialog

import customtkinter as ctk

try:
    from PIL import Image
except ImportError:
    print("Pillow is required: pip install Pillow")
    sys.exit(1)

from backend import CONFIG_DIR, DEBUG_LOG_FILE, ERROR_LOG_FILE, DownloadBackend

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
C_STOP    = "#ef4444"
C_STOP_H  = "#dc2626"
C_TEXT    = "#f0eeff"
C_MUTED   = "#9585b8"
C_BORDER  = "#2b1f4a"
R         = 14          # universal corner_radius

FONT_TITLE = ("Inter", 20, "bold")
FONT_SUB   = ("Inter", 11)
FONT_LBL   = ("Inter", 13)
FONT_BTN   = ("Inter", 13, "bold")
FONT_SM    = ("Inter", 11)
FONT_MONO  = ("Consolas", 11)

# ── I18N ──────────────────────────────────────────────────────────────────────
I18N: dict[str, dict[str, str]] = {
    "en": {
        "window_title":               "JPG6 Downloader Pro",
        "app_title":                  "JPG6 Downloader",
        "app_subtitle":               "Material Design  ·  Direct Engine",
        "workers":                    "Workers:",
        "language":                   "Language:",
        "folder_label":               "Download folder:",
        "pick_folder":                "📁  Pick Folder",
        "save_settings":              "💾  Save Settings",
        "import_txt":                 "📋  Import URLs (TXT)",
        "scan_preview":               "🔍  Scan & Preview",
        "start_download":             "⬇  Download Selected",
        "stop":                       "⏹  Stop",
        "url_placeholder":            "Paste album / profile / image URL…",
        "add":                        "Add",
        "clear_queue":                "Clear Queue",
        "status_ready":               "Ready",
        "settings_saved":             "✓ Settings saved",
        "pick_folder_dialog":         "Select download folder",
        "invalid_url":                "⚠ Invalid URL",
        "queued_count":               "Queued: {count}",
        "queue_cleared":              "Queue cleared",
        "import_file_dialog":         "Select TXT file",
        "imported_count":             "Imported {count} URLs — click Scan & Preview",
        "backend_running":            "⚠ Already running",
        "queue_empty":                "⚠ Queue is empty",
        "starting_scan":              "🔍 Scanning URLs…",
        "starting_download":          "⬇ Downloading…",
        "stopping":                   "⏹ Stopping…",
        "scan_done":                  "✓ Scan complete: {count} images found",
        "no_selected":                "⚠ No images selected",
        "cancelled_summary":          "⏹ Stopped | albums={albums} downloaded={downloaded} skipped={skipped} errors={errors}",
        "done_summary":               "✓ Done | albums={albums} downloaded={downloaded} skipped={skipped} errors={errors}",
        "lang_ru":                    "Русский",
        "lang_en":                    "English",
        "select_all":                 "✓ Select All",
        "deselect_all":               "✗ Deselect All",
        "size_small":                 "S",
        "size_medium":                "M",
        "size_large":                 "L",
        "clear_gallery":              "🗑  Clear Gallery",
        "gallery_title":              "Gallery  ·  check images to download",
    },
    "ru": {
        "window_title":               "JPG6 Downloader Pro",
        "app_title":                  "JPG6 Downloader",
        "app_subtitle":               "Material Design  ·  прямой движок",
        "workers":                    "Потоки:",
        "language":                   "Язык:",
        "folder_label":               "Папка загрузки:",
        "pick_folder":                "📁  Выбрать папку",
        "save_settings":              "💾  Сохранить настройки",
        "import_txt":                 "📋  Импорт URL (TXT)",
        "scan_preview":               "🔍  Сканировать",
        "start_download":             "⬇  Загрузить выбранные",
        "stop":                       "⏹  Стоп",
        "url_placeholder":            "Вставьте ссылку на альбом / профиль / фото…",
        "add":                        "Добавить",
        "clear_queue":                "Очистить",
        "status_ready":               "Готово",
        "settings_saved":             "✓ Настройки сохранены",
        "pick_folder_dialog":         "Выберите папку загрузки",
        "invalid_url":                "⚠ Неверный URL",
        "queued_count":               "В очереди: {count}",
        "queue_cleared":              "Очередь очищена",
        "import_file_dialog":         "Выберите TXT файл",
        "imported_count":             "Импортировано {count} URL — нажмите Сканировать",
        "backend_running":            "⚠ Уже запущено",
        "queue_empty":                "⚠ Очередь пуста",
        "starting_scan":              "🔍 Сканирование URL…",
        "starting_download":          "⬇ Загрузка…",
        "stopping":                   "⏹ Остановка…",
        "scan_done":                  "✓ Сканирование завершено: {count} изображений",
        "no_selected":                "⚠ Нет выбранных изображений",
        "cancelled_summary":          "⏹ Остановлено | альбомов={albums} скачано={downloaded} пропущено={skipped} ошибок={errors}",
        "done_summary":               "✓ Готово | альбомов={albums} скачано={downloaded} пропущено={skipped} ошибок={errors}",
        "lang_ru":                    "Русский",
        "lang_en":                    "English",
        "select_all":                 "✓ Выбрать все",
        "deselect_all":               "✗ Снять все",
        "size_small":                 "М",
        "size_medium":                "С",
        "size_large":                 "К",
        "clear_gallery":              "🗑  Очистить",
        "gallery_title":              "Галерея  ·  отметьте фото для загрузки",
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


# ── Background workers (pure threading, no Qt) ────────────────────────────────
class PreviewWorker:
    """Resolves input URLs → image list without downloading."""

    def __init__(self, urls, base_dir, workers, batch_name=None,
                 image_found_cb=None, status_cb=None, finished_cb=None):
        self.urls         = list(urls)
        self.base_dir     = base_dir
        self.workers      = workers
        self.batch_name   = batch_name
        self.image_found_cb = image_found_cb
        self.status_cb    = status_cb
        self.finished_cb  = finished_cb
        self.backend      = None
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        count = [0]
        self.backend = DownloadBackend(
            base_dir=self.base_dir,
            workers=self.workers,
            status_cb=self.status_cb,
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
            self.urls, batch_name=self.batch_name, image_found_cb=_cb
        )
        if self.finished_cb:
            self.finished_cb(count[0])

    def stop(self):
        if self.backend:
            self.backend.cancel()

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()


class DownloadWorker:
    """Downloads a pre-resolved list of (album_title, img_dict) pairs."""

    def __init__(self, selected, base_dir, workers,
                 log_cb=None, status_cb=None, progress_cb=None, finished_cb=None):
        self.selected    = selected
        self.base_dir    = base_dir
        self.workers     = workers
        self.log_cb      = log_cb
        self.status_cb   = status_cb
        self.progress_cb = progress_cb
        self.finished_cb = finished_cb
        self.backend     = None
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        self.backend = DownloadBackend(
            base_dir=self.base_dir,
            workers=self.workers,
            logger=self.log_cb,
            status_cb=self.status_cb,
            progress_cb=self.progress_cb,
        )
        summary = self.backend.download_selected(self.selected)
        if self.finished_cb:
            self.finished_cb(summary)

    def stop(self):
        if self.backend:
            self.backend.cancel()

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()


class CdnThumbnailLoader:
    """Fetches a thumbnail image from CDN in a background thread."""

    def __init__(self, url: str, size: int, on_loaded):
        self.url      = url
        self.size     = size
        self.on_loaded = on_loaded  # callable(pil_image)

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


# ── Thumbnail card widget ─────────────────────────────────────────────────────
class ThumbnailCard(ctk.CTkFrame):
    """Single gallery card: thumbnail image + filename + checkbox."""

    PLACEHOLDER_COLOR = "#1e1535"

    def __init__(self, parent, album_title: str, url: str,
                 filename: str, thumb_url: str, thumb_size: int = 100, **kw):
        super().__init__(
            parent,
            fg_color=C_CARD,
            corner_radius=R,
            border_width=2,
            border_color=C_ACC1,   # checked by default → accent border
            **kw,
        )
        self.album_title = album_title
        self.url         = url
        self.filename    = filename
        self.thumb_url   = thumb_url
        self.thumb_size  = thumb_size
        self._pil_image: Image.Image | None = None
        self._ctk_image: ctk.CTkImage | None = None
        self._checked    = True

        self._build()

    # ── build ────────────────────────────────────────────────────────────────
    def _build(self):
        s = self.thumb_size
        self.configure(width=s + 20, height=s + 54)
        self.pack_propagate(False)
        self.grid_propagate(False)

        # Placeholder image
        placeholder = Image.new("RGB", (s, s), self.PLACEHOLDER_COLOR)
        self._ctk_image = ctk.CTkImage(
            light_image=placeholder, dark_image=placeholder, size=(s, s)
        )

        self._img_label = ctk.CTkLabel(
            self, image=self._ctk_image, text="",
            fg_color="transparent", cursor="hand2",
        )
        self._img_label.pack(pady=(10, 3))
        self._img_label.bind("<Button-1>", self._on_click)

        short = (self.filename or os.path.basename(self.url))[:20]
        self._name_label = ctk.CTkLabel(
            self, text=short, font=FONT_SM, text_color=C_MUTED,
            fg_color="transparent", wraplength=s + 10,
        )
        self._name_label.pack(padx=4, pady=(0, 6))
        self._name_label.bind("<Button-1>", self._on_click)

        self._check_var = ctk.BooleanVar(value=True)
        self._checkbox = ctk.CTkCheckBox(
            self, text="", variable=self._check_var,
            width=20, height=20, checkbox_width=18, checkbox_height=18,
            corner_radius=5, fg_color=C_ACC1, hover_color=C_ACC1_H,
            border_color=C_BORDER, command=self._on_checkbox_change,
        )
        self._checkbox.place(relx=1.0, rely=0.0, anchor="ne", x=-6, y=6)

    def _on_click(self, _event=None):
        self._check_var.set(not self._check_var.get())
        self._on_checkbox_change()

    def _on_checkbox_change(self):
        self._checked = self._check_var.get()
        self.configure(border_color=C_ACC1 if self._checked else C_BORDER)

    # ── public API ───────────────────────────────────────────────────────────
    def set_image(self, pil_img: Image.Image):
        self._pil_image = pil_img
        self._refresh_ctk_image()

    def _refresh_ctk_image(self):
        if self._pil_image is None:
            return
        s = self.thumb_size
        copy = self._pil_image.copy()
        copy.thumbnail((s, s), Image.LANCZOS)
        self._ctk_image = ctk.CTkImage(
            light_image=copy, dark_image=copy, size=(s, s)
        )
        self._img_label.configure(image=self._ctk_image)

    def set_checked(self, value: bool):
        self._check_var.set(value)
        self._checked = value
        self.configure(border_color=C_ACC1 if value else C_BORDER)

    def is_checked(self) -> bool:
        return self._check_var.get()

    def resize_thumb(self, new_size: int):
        self.thumb_size = new_size
        self.configure(width=new_size + 20, height=new_size + 54)
        self._refresh_ctk_image()


# ── Gallery scrollable container ──────────────────────────────────────────────
class GalleryFrame(ctk.CTkScrollableFrame):
    """Scrollable frame that lays ThumbnailCards in a responsive grid."""

    def __init__(self, parent, thumb_size: int = 100, **kw):
        super().__init__(
            parent,
            fg_color=C_SURF,
            scrollbar_button_color=C_BORDER,
            scrollbar_button_hover_color=C_ACC1,
            corner_radius=R,
            **kw,
        )
        self.thumb_size = thumb_size
        self._cards: list[ThumbnailCard] = []
        self._cols   = 4
        self._relayout_pending = False
        self.bind("<Configure>", self._on_configure)

    # ── card management ──────────────────────────────────────────────────────
    def add_card(self, album_title, url, filename, thumb_url) -> ThumbnailCard:
        card = ThumbnailCard(
            self, album_title, url, filename, thumb_url,
            thumb_size=self.thumb_size,
        )
        self._cards.append(card)
        # Place immediately in current grid
        idx     = len(self._cards) - 1
        r, c    = divmod(idx, max(1, self._cols))
        card.grid(row=r, column=c, padx=7, pady=7, sticky="n")
        return card

    def clear(self):
        for card in self._cards:
            card.destroy()
        self._cards.clear()

    def set_all_checked(self, value: bool):
        for card in self._cards:
            card.set_checked(value)

    def get_selected(self) -> list[tuple]:
        return [
            (c.album_title, {"url": c.url, "filename": c.filename})
            for c in self._cards if c.is_checked()
        ]

    def set_thumb_size(self, size: int):
        self.thumb_size = size
        for card in self._cards:
            card.resize_thumb(size)
        self._recompute_layout()

    def count(self) -> int:
        return len(self._cards)

    # ── layout ───────────────────────────────────────────────────────────────
    def _on_configure(self, event=None):
        if not self._relayout_pending:
            self._relayout_pending = True
            self.after(80, self._deferred_relayout)

    def _deferred_relayout(self):
        self._relayout_pending = False
        self._recompute_layout()

    def _recompute_layout(self):
        w = self.winfo_width()
        if w < 20:
            return
        card_w  = self.thumb_size + 22   # card width + padx*2
        new_cols = max(1, (w - 20) // card_w)
        if new_cols != self._cols:
            self._cols = new_cols
            self._relayout()

    def _relayout(self):
        for i, card in enumerate(self._cards):
            r, c = divmod(i, max(1, self._cols))
            card.grid(row=r, column=c, padx=7, pady=7, sticky="n")


# ── Main window ───────────────────────────────────────────────────────────────
class DownloaderCtkWindow(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.settings     = load_json(SETTINGS_FILE, {})
        self.lang: str    = self.settings.get("lang", "ru")
        if self.lang not in I18N:
            self.lang = "ru"

        self._worker: PreviewWorker | DownloadWorker | None = None
        self._batch_name: str | None = None
        self._queued_urls: list[str] = []
        self._thumb_size: int = 100
        self._log_job_id  = None

        self.title("JPG6 Downloader Pro")
        self.geometry("1300x840")
        self.minsize(920, 620)
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

    # ─────────────────────────────────────────────────────── SIDEBAR ──────────
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=C_SIDE, corner_radius=0, width=284)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        row = 0

        # Logo
        self._lbl_title = ctk.CTkLabel(
            sb, text="JPG6 Downloader", font=FONT_TITLE, text_color=C_TEXT,
        )
        self._lbl_title.grid(row=row, column=0, padx=22, pady=(26, 0), sticky="w")
        row += 1

        self._lbl_sub = ctk.CTkLabel(
            sb, text="", font=FONT_SUB, text_color=C_MUTED,
        )
        self._lbl_sub.grid(row=row, column=0, padx=22, pady=(2, 14), sticky="w")
        row += 1

        self._sep(sb, row); row += 1

        # Workers
        self._lbl_workers = ctk.CTkLabel(sb, text="", font=FONT_LBL, text_color=C_MUTED)
        self._lbl_workers.grid(row=row, column=0, padx=22, pady=(12, 2), sticky="w")
        row += 1

        wf = ctk.CTkFrame(sb, fg_color="transparent")
        wf.grid(row=row, column=0, padx=22, pady=(0, 2), sticky="ew")
        row += 1
        wf.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            wf, text="−", width=34, height=34, corner_radius=10,
            fg_color=C_CARD, hover_color=C_BORDER, text_color=C_TEXT,
            font=FONT_BTN, command=self._workers_dec,
        ).grid(row=0, column=0, padx=(0, 4))

        self._workers_var = ctk.StringVar(value="3")
        ctk.CTkEntry(
            wf, textvariable=self._workers_var, width=50, height=34,
            corner_radius=10, fg_color=C_CARD, border_color=C_BORDER,
            text_color=C_TEXT, justify="center", font=FONT_LBL,
        ).grid(row=0, column=1, padx=4, sticky="ew")

        ctk.CTkButton(
            wf, text="+", width=34, height=34, corner_radius=10,
            fg_color=C_CARD, hover_color=C_BORDER, text_color=C_TEXT,
            font=FONT_BTN, command=self._workers_inc,
        ).grid(row=0, column=2, padx=(4, 0))

        # Language
        self._lbl_lang = ctk.CTkLabel(sb, text="", font=FONT_LBL, text_color=C_MUTED)
        self._lbl_lang.grid(row=row, column=0, padx=22, pady=(10, 2), sticky="w")
        row += 1

        self._lang_var = ctk.StringVar(value="Русский")
        self._lang_menu = ctk.CTkOptionMenu(
            sb, values=["Русский", "English"], variable=self._lang_var,
            command=self._on_lang_changed,
            fg_color=C_CARD, button_color=C_ACC1, button_hover_color=C_ACC1_H,
            dropdown_fg_color=C_CARD, dropdown_text_color=C_TEXT,
            dropdown_hover_color=C_BORDER, text_color=C_TEXT,
            font=FONT_LBL, corner_radius=R, height=36,
        )
        self._lang_menu.grid(row=row, column=0, padx=22, pady=(0, 4), sticky="ew")
        row += 1

        # Folder
        self._lbl_folder = ctk.CTkLabel(sb, text="", font=FONT_LBL, text_color=C_MUTED)
        self._lbl_folder.grid(row=row, column=0, padx=22, pady=(10, 2), sticky="w")
        row += 1

        self._dir_var = ctk.StringVar()
        ctk.CTkEntry(
            sb, textvariable=self._dir_var, height=36, corner_radius=R,
            fg_color=C_CARD, border_color=C_BORDER, text_color=C_TEXT,
            placeholder_text="…", font=FONT_SM,
        ).grid(row=row, column=0, padx=22, pady=(0, 4), sticky="ew")
        row += 1

        self._btn_pick = ctk.CTkButton(
            sb, text="", height=36, corner_radius=R,
            fg_color=C_CARD, hover_color=C_BORDER, text_color=C_TEXT,
            font=FONT_LBL, command=self.pick_folder,
        )
        self._btn_pick.grid(row=row, column=0, padx=22, pady=(0, 4), sticky="ew")
        row += 1

        self._btn_save = ctk.CTkButton(
            sb, text="", height=36, corner_radius=R,
            fg_color=C_CARD, hover_color=C_BORDER, text_color=C_TEXT,
            font=FONT_LBL, command=self.save_settings,
        )
        self._btn_save.grid(row=row, column=0, padx=22, pady=(0, 4), sticky="ew")
        row += 1

        self._sep(sb, row); row += 1

        # Action buttons
        self._btn_import = ctk.CTkButton(
            sb, text="", height=40, corner_radius=R,
            fg_color=C_CARD, hover_color=C_BORDER, text_color=C_TEXT,
            font=FONT_BTN, command=self.import_urls,
        )
        self._btn_import.grid(row=row, column=0, padx=22, pady=(6, 6), sticky="ew")
        row += 1

        self._btn_scan = ctk.CTkButton(
            sb, text="", height=44, corner_radius=R,
            fg_color=C_ACC1, hover_color=C_ACC1_H, text_color="#ffffff",
            font=FONT_BTN, command=self.start_scan,
        )
        self._btn_scan.grid(row=row, column=0, padx=22, pady=(0, 8), sticky="ew")
        row += 1

        self._btn_start = ctk.CTkButton(
            sb, text="", height=44, corner_radius=R,
            fg_color=C_ACC2, hover_color=C_ACC2_H, text_color="#1a1000",
            font=FONT_BTN, command=self.start_download_selected,
            state="disabled",
        )
        self._btn_start.grid(row=row, column=0, padx=22, pady=(0, 8), sticky="ew")
        row += 1

        self._btn_stop = ctk.CTkButton(
            sb, text="", height=40, corner_radius=R,
            fg_color=C_STOP, hover_color=C_STOP_H, text_color="#ffffff",
            font=FONT_BTN, command=self.stop_worker,
            state="disabled",
        )
        self._btn_stop.grid(row=row, column=0, padx=22, pady=(0, 0), sticky="ew")
        row += 1

        # Spacer
        spacer = ctk.CTkFrame(sb, fg_color="transparent")
        spacer.grid(row=row, column=0, sticky="nsew")
        sb.grid_rowconfigure(row, weight=1)

    # ─────────────────────────────────────────────────────── CONTENT ──────────
    def _build_content(self):
        c = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        c.grid(row=0, column=1, sticky="nsew")
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(2, weight=3)    # gallery expands most
        c.grid_rowconfigure(4, weight=1)    # logs expand too

        # URL input row
        url_row = ctk.CTkFrame(c, fg_color="transparent")
        url_row.grid(row=0, column=0, padx=18, pady=(16, 8), sticky="ew")
        url_row.grid_columnconfigure(0, weight=1)

        self._url_var = ctk.StringVar()
        self._url_entry = ctk.CTkEntry(
            url_row, textvariable=self._url_var, height=42, corner_radius=R,
            fg_color=C_CARD, border_color=C_BORDER, text_color=C_TEXT,
            placeholder_text="…", font=FONT_LBL,
        )
        self._url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._url_entry.bind("<Return>", lambda _: self.add_url())

        self._btn_add = ctk.CTkButton(
            url_row, text="", width=120, height=42, corner_radius=R,
            fg_color=C_ACC1, hover_color=C_ACC1_H, text_color="#ffffff",
            font=FONT_BTN, command=self.add_url,
        )
        self._btn_add.grid(row=0, column=1, padx=(0, 6))

        self._btn_clear = ctk.CTkButton(
            url_row, text="", width=120, height=42, corner_radius=R,
            fg_color=C_CARD, hover_color=C_BORDER, text_color=C_MUTED,
            font=FONT_BTN, command=self.clear_queue,
        )
        self._btn_clear.grid(row=0, column=2)

        # Gallery toolbar
        gt = ctk.CTkFrame(c, fg_color="transparent")
        gt.grid(row=1, column=0, padx=18, pady=(0, 6), sticky="ew")

        self._btn_sel_all = ctk.CTkButton(
            gt, text="", width=110, height=30, corner_radius=10,
            fg_color=C_CARD, hover_color=C_BORDER, text_color=C_TEXT,
            font=FONT_SM, command=lambda: self.gallery.set_all_checked(True),
        )
        self._btn_sel_all.pack(side="left", padx=(0, 4))

        self._btn_desel = ctk.CTkButton(
            gt, text="", width=110, height=30, corner_radius=10,
            fg_color=C_CARD, hover_color=C_BORDER, text_color=C_TEXT,
            font=FONT_SM, command=lambda: self.gallery.set_all_checked(False),
        )
        self._btn_desel.pack(side="left", padx=(0, 16))

        self._btn_sz = {}
        for key, sz in (("size_small", 70), ("size_medium", 120), ("size_large", 200)):
            is_active = (sz == self._thumb_size)
            btn = ctk.CTkButton(
                gt, text="", width=38, height=30, corner_radius=10,
                fg_color=C_ACC1 if is_active else C_CARD,
                hover_color=C_ACC1_H,
                text_color="#ffffff" if is_active else C_TEXT,
                font=FONT_SM,
                command=lambda s=sz: self._set_thumb_size(s),
            )
            btn.pack(side="left", padx=(0, 3))
            self._btn_sz[sz] = btn

        self._btn_clear_gal = ctk.CTkButton(
            gt, text="", width=130, height=30, corner_radius=10,
            fg_color=C_CARD, hover_color=C_STOP, text_color=C_MUTED,
            font=FONT_SM, command=self._clear_gallery,
        )
        self._btn_clear_gal.pack(side="right")

        self._lbl_gallery = ctk.CTkLabel(
            gt, text="", font=FONT_SM, text_color=C_MUTED,
        )
        self._lbl_gallery.pack(side="left", padx=12)

        # Gallery
        self.gallery = GalleryFrame(c, thumb_size=self._thumb_size)
        self.gallery.grid(row=2, column=0, padx=18, pady=(0, 8), sticky="nsew")

        # Progress row
        pr = ctk.CTkFrame(c, fg_color="transparent")
        pr.grid(row=3, column=0, padx=18, pady=(0, 8), sticky="ew")
        pr.grid_columnconfigure(0, weight=1)

        self._progress = ctk.CTkProgressBar(
            pr, height=16, corner_radius=8,
            fg_color=C_CARD, progress_color=C_ACC1,
            mode="determinate",
        )
        self._progress.set(0)
        self._progress.grid(row=0, column=0, sticky="ew", padx=(0, 12))

        self._lbl_status = ctk.CTkLabel(
            pr, text="", width=220, font=FONT_LBL, text_color=C_ACC2, anchor="w",
        )
        self._lbl_status.grid(row=0, column=1)

        # Logs (tab view — English labels, no translation needed for technical tabs)
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
        self._log_tabs.grid(row=4, column=0, padx=18, pady=(0, 16), sticky="nsew")

        for tab_name, attr in (("Engine", "_log_engine"), ("Errors", "_log_error"), ("Debug", "_log_debug")):
            self._log_tabs.add(tab_name)
            tab_fr = self._log_tabs.tab(tab_name)
            tab_fr.grid_columnconfigure(0, weight=1)
            tab_fr.grid_rowconfigure(0, weight=1)
            txt = ctk.CTkTextbox(
                tab_fr, font=FONT_MONO,
                fg_color=C_SURF, text_color="#b8d4aa",
                scrollbar_button_color=C_BORDER,
                scrollbar_button_hover_color=C_ACC1,
                corner_radius=10, wrap="word", state="disabled",
            )
            txt.grid(row=0, column=0, sticky="nsew")
            setattr(self, attr, txt)

    @staticmethod
    def _sep(parent, row: int):
        ctk.CTkFrame(parent, height=1, fg_color=C_BORDER).grid(
            row=row, column=0, padx=22, pady=4, sticky="ew"
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
        # Lang menu value
        val = I18N[self.lang].get("lang_" + self.lang, "Русский")
        self._lang_var.set(val)

    def save_settings(self, quiet: bool = False):
        self.settings["base_dir"] = self._dir_var.get().strip() or os.path.join(SCRIPT_DIR, "downloads")
        self.settings["workers"]  = self._get_workers()
        self.settings["lang"]     = self.lang
        save_json(SETTINGS_FILE, self.settings)
        if not quiet:
            self._set_status(self._t("settings_saved"))

    def pick_folder(self):
        cur = self._dir_var.get().strip() or SCRIPT_DIR
        folder = filedialog.askdirectory(
            title=self._t("pick_folder_dialog"), initialdir=cur, parent=self
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
        self._btn_pick.configure(text=self._t("pick_folder"))
        self._btn_save.configure(text=self._t("save_settings"))
        self._btn_import.configure(text=self._t("import_txt"))
        self._btn_scan.configure(text=self._t("scan_preview"))
        self._btn_start.configure(text=self._t("start_download"))
        self._btn_stop.configure(text=self._t("stop"))
        self._url_entry.configure(placeholder_text=self._t("url_placeholder"))
        self._btn_add.configure(text=self._t("add"))
        self._btn_clear.configure(text=self._t("clear_queue"))
        self._btn_sel_all.configure(text=self._t("select_all"))
        self._btn_desel.configure(text=self._t("deselect_all"))
        self._btn_sz[70].configure(text=self._t("size_small"))
        self._btn_sz[120].configure(text=self._t("size_medium"))
        self._btn_sz[200].configure(text=self._t("size_large"))
        self._btn_clear_gal.configure(text=self._t("clear_gallery"))
        self._lbl_gallery.configure(text=self._t("gallery_title"))
        # Lang menu
        self._lang_menu.configure(values=[self._t("lang_ru"), self._t("lang_en")])
        self._lang_var.set(self._t("lang_" + self.lang))
        # Status (if empty / default)
        if not self._lbl_status.cget("text").strip():
            self._set_status(self._t("status_ready"))

    # ── Queue management ──────────────────────────────────────────────────────
    def add_url(self):
        url = self._url_var.get().strip()
        if not url:
            return
        if not url.startswith("http"):
            self._set_status(self._t("invalid_url"))
            return
        if url not in self._queued_urls:
            self._queued_urls.append(url)
        self._url_var.set("")
        self._set_status(self._t("queued_count", count=len(self._queued_urls)))

    def clear_queue(self):
        self._queued_urls.clear()
        self._batch_name = None
        self._progress.set(0)
        self._set_status(self._t("queue_cleared"))

    def import_urls(self):
        path = filedialog.askopenfilename(
            title=self._t("import_file_dialog"),
            initialdir=SCRIPT_DIR,
            filetypes=[("Text files", "*.txt")],
            parent=self,
        )
        if not path:
            return
        self._batch_name = os.path.splitext(os.path.basename(path))[0]
        added = 0
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line.startswith("http"):
                    continue
                if line not in self._queued_urls:
                    self._queued_urls.append(line)
                added += 1
        self._set_status(self._t("imported_count", count=added))

    # ── Gallery helpers ───────────────────────────────────────────────────────
    def _set_thumb_size(self, size: int):
        self._thumb_size = size
        self.gallery.set_thumb_size(size)
        for sz, btn in self._btn_sz.items():
            if sz == size:
                btn.configure(fg_color=C_ACC1, text_color="#ffffff", hover_color=C_ACC1_H)
            else:
                btn.configure(fg_color=C_CARD, text_color=C_TEXT, hover_color=C_ACC1)

    def _clear_gallery(self):
        self.gallery.clear()
        self._btn_start.configure(state="disabled")

    # ── Scan workflow ─────────────────────────────────────────────────────────
    def start_scan(self):
        if self._worker and self._worker.is_alive():
            self._set_status(self._t("backend_running"))
            return
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

        self._worker = PreviewWorker(
            list(self._queued_urls), base_dir, workers,
            batch_name=self._batch_name,
            image_found_cb=lambda at, u, fn, tu: self.after(
                0, lambda at=at, u=u, fn=fn, tu=tu: self._on_image_found(at, u, fn, tu)
            ),
            status_cb=lambda txt: self.after(0, lambda t=txt: self._set_status(t)),
            finished_cb=lambda cnt: self.after(0, lambda c=cnt: self._on_scan_finished(c)),
        )
        self._worker.start()

    def _on_image_found(self, album_title, url, filename, thumb_url):
        card = self.gallery.add_card(album_title, url, filename, thumb_url)
        CdnThumbnailLoader(
            thumb_url or url, self._thumb_size,
            on_loaded=lambda img, _c=card: self.after(0, lambda i=img, c=_c: c.set_image(i)),
        ).start()

    def _on_scan_finished(self, count: int):
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress.set(1.0 if count > 0 else 0.0)
        self._set_ui_busy(False)
        self._worker = None
        if count > 0:
            self._btn_start.configure(state="normal")
        self._set_status(self._t("scan_done", count=count))

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
        self._progress.set(0)
        self._set_ui_busy(True)
        self._set_status(self._t("starting_download"))

        self._worker = DownloadWorker(
            selected, base_dir, workers,
            log_cb=lambda msg: self.after(0, lambda m=msg: self._append_engine_log(m)),
            status_cb=lambda txt: self.after(0, lambda t=txt: self._set_status(t)),
            progress_cb=lambda d, t: self.after(0, lambda d=d, t=t: self._on_progress(d, t)),
            finished_cb=lambda s: self.after(0, lambda s=s: self._on_download_finished(s)),
        )
        self._worker.start()

    def stop_worker(self):
        if self._worker:
            self._worker.stop()
            self._set_status(self._t("stopping"))

    # ── Shared UI helpers ─────────────────────────────────────────────────────
    def _set_ui_busy(self, busy: bool):
        on  = "normal"
        off = "disabled"
        self._btn_scan.configure(state=off if busy else on)
        self._btn_import.configure(state=off if busy else on)
        self._btn_stop.configure(state=on if busy else off)

    def _set_status(self, text: str):
        self._lbl_status.configure(text=text)

    def _append_engine_log(self, msg: str):
        self._log_engine.configure(state="normal")
        self._log_engine.insert("end", msg + "\n")
        self._log_engine.see("end")
        self._log_engine.configure(state="disabled")

    def _on_progress(self, done: int, total: int):
        if total <= 0:
            self._progress.set(0)
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

    # ── Log refresh (replaces Qt QTimer) ─────────────────────────────────────
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
            current = widget.get("1.0", "end-1c")
            if current != data:
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

import json
import os
import sys
import urllib.request

from PySide6 import QtCore, QtGui, QtWidgets

from backend import CONFIG_DIR, DEBUG_LOG_FILE, ERROR_LOG_FILE, DownloadBackend

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")

I18N = {
    "en": {
        "window_title": "JPG6 Downloader Pro",
        "app_title": "JPG6 Downloader",
        "app_subtitle": "Qt + Direct Backend Engine",
        "workers": "Workers:",
        "language": "Language:",
        "download_folder_placeholder": "Download folder",
        "pick_folder": "Pick Folder",
        "save_settings": "Save Settings",
        "import_txt": "Import URLs from TXT",
        "scan_preview": "Scan & Preview",
        "start_download": "Download Selected",
        "stop": "Stop",
        "url_placeholder": "Paste album/profile/image URL and click Add",
        "add": "Add",
        "clear_queue": "Clear Queue",
        "status_ready": "Ready",
        "engine_log_placeholder": "Engine log",
        "engine_group": "Engine",
        "errors_tab": "Errors",
        "debug_tab": "Debug",
        "settings_saved": "Settings saved",
        "pick_folder_dialog": "Select download folder",
        "invalid_url": "Invalid URL",
        "queued_count": "Queued: {count}",
        "queue_cleared": "Queue cleared",
        "import_file_dialog": "Select TXT file",
        "imported_count": "Imported {count} URLs — click Scan & Preview",
        "backend_running": "Already running",
        "queue_empty": "Queue is empty",
        "starting_scan": "Scanning URLs…",
        "starting_download": "Downloading…",
        "stopping": "Stopping…",
        "scan_done": "Scan complete: {count} images found",
        "no_selected": "No images selected",
        "cancelled_summary": "Cancelled | albums={albums} downloaded={downloaded} skipped={skipped} errors={errors}",
        "done_summary": "Done | albums={albums} downloaded={downloaded} skipped={skipped} errors={errors}",
        "lang_ru": "Russian",
        "lang_en": "English",
        "select_all": "Select All",
        "deselect_all": "Deselect All",
        "size_small": "Small",
        "size_medium": "Medium",
        "size_large": "Large",
        "clear_gallery": "Clear Gallery",
        "gallery_group": "Gallery  (check images to download)",
    },
    "ru": {
        "window_title": "JPG6 Downloader Pro",
        "app_title": "JPG6 Downloader",
        "app_subtitle": "Qt + прямой backend-движок",
        "workers": "Потоки:",
        "language": "Язык:",
        "download_folder_placeholder": "Папка загрузки",
        "pick_folder": "Выбрать папку",
        "save_settings": "Сохранить настройки",
        "import_txt": "Импорт URL из TXT",
        "scan_preview": "Сканировать и просмотреть",
        "start_download": "Загрузить выбранные",
        "stop": "Стоп",
        "url_placeholder": "Вставьте ссылку и нажмите Добавить",
        "add": "Добавить",
        "clear_queue": "Очистить очередь",
        "status_ready": "Готово",
        "engine_log_placeholder": "Лог движка",
        "engine_group": "Движок",
        "errors_tab": "Ошибки",
        "debug_tab": "Отладка",
        "settings_saved": "Настройки сохранены",
        "pick_folder_dialog": "Выберите папку загрузки",
        "invalid_url": "Неверный URL",
        "queued_count": "В очереди: {count}",
        "queue_cleared": "Очередь очищена",
        "import_file_dialog": "Выберите TXT файл",
        "imported_count": "Импортировано {count} URL — нажмите Сканировать",
        "backend_running": "Уже запущено",
        "queue_empty": "Очередь пуста",
        "starting_scan": "Сканирование URL…",
        "starting_download": "Загрузка…",
        "stopping": "Остановка…",
        "scan_done": "Сканирование завершено: {count} изображений",
        "no_selected": "Нет выбранных изображений",
        "cancelled_summary": "Остановлено | альбомов={albums} скачано={downloaded} пропущено={skipped} ошибок={errors}",
        "done_summary": "Готово | альбомов={albums} скачано={downloaded} пропущено={skipped} ошибок={errors}",
        "lang_ru": "Русский",
        "lang_en": "Английский",
        "select_all": "Выбрать все",
        "deselect_all": "Снять все",
        "size_small": "Мелкие",
        "size_medium": "Средние",
        "size_large": "Крупные",
        "clear_gallery": "Очистить галерею",
        "gallery_group": "Галерея  (отметьте фото для загрузки)",
    },
}


def load_json(path, default=None):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------

class CdnThumbnailLoader(QtCore.QRunnable):
    """Fetches a thumbnail image from a CDN URL in a background thread."""

    class Signals(QtCore.QObject):
        loaded = QtCore.Signal(object, QtGui.QPixmap)  # (QListWidgetItem, pixmap)

    def __init__(self, item, url, size):
        super().__init__()
        self.item = item
        self.url = url
        self.size = size
        self.signals = CdnThumbnailLoader.Signals()
        self.setAutoDelete(True)

    def run(self):
        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            pixmap = QtGui.QPixmap()
            if not pixmap.loadFromData(data):
                return
            scaled = pixmap.scaled(
                self.size, self.size,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
            self.signals.loaded.emit(self.item, scaled)
        except Exception:
            pass


class PreviewWorker(QtCore.QObject):
    """Resolves input URLs to image lists (no download). Emits one signal per image."""
    image_found = QtCore.Signal(str, str, str, str)  # album_title, url, filename, thumb_url
    status = QtCore.Signal(str)
    finished = QtCore.Signal(int)  # total images found

    def __init__(self, urls, base_dir, workers, batch_name=None):
        super().__init__()
        self.urls = list(urls)
        self.base_dir = base_dir
        self.workers = workers
        self.batch_name = batch_name
        self.backend = None

    @QtCore.Slot()
    def run(self):
        self.backend = DownloadBackend(
            base_dir=self.base_dir,
            workers=self.workers,
            status_cb=self.status.emit,
        )
        count = [0]

        def image_found_cb(album_title, img):
            count[0] += 1
            self.image_found.emit(
                album_title,
                img.get("url", ""),
                img.get("filename", ""),
                img.get("thumb_url") or img.get("url", ""),
            )

        self.backend.scan_for_preview(
            self.urls,
            batch_name=self.batch_name,
            image_found_cb=image_found_cb,
        )
        self.finished.emit(count[0])

    @QtCore.Slot()
    def stop(self):
        if self.backend:
            self.backend.cancel()


class DownloadWorker(QtCore.QObject):
    """Downloads a pre-resolved list of (album_title, img_dict) pairs."""
    log = QtCore.Signal(str)
    status = QtCore.Signal(str)
    progress = QtCore.Signal(int, int)
    finished = QtCore.Signal(dict)

    def __init__(self, selected, base_dir, workers):
        super().__init__()
        self.selected = selected  # list of (album_title, img_dict)
        self.base_dir = base_dir
        self.workers = workers
        self.backend = None

    @QtCore.Slot()
    def run(self):
        self.backend = DownloadBackend(
            base_dir=self.base_dir,
            workers=self.workers,
            logger=self.log.emit,
            status_cb=self.status.emit,
            progress_cb=self.progress.emit,
        )
        summary = self.backend.download_selected(self.selected)
        self.finished.emit(summary)

    @QtCore.Slot()
    def stop(self):
        if self.backend:
            self.backend.cancel()


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------


class DownloaderQtWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1260, 800)

        self.settings = load_json(SETTINGS_FILE, {})
        self.lang = self.settings.get("lang", "ru")
        if self.lang not in I18N:
            self.lang = "ru"
        self.worker = None
        self.worker_thread = None
        self._batch_name = None
        self._queued_urls = []    # raw input URLs (from TXT or manual add)
        self._thumb_size = 100   # current gallery thumbnail size (px)

        self._build_ui()
        self._apply_styles()
        self._setup_timers()
        self._load_settings()

    def _build_ui(self):
        root = QtWidgets.QWidget()
        main = QtWidgets.QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────────────────
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(290)
        side_layout = QtWidgets.QVBoxLayout(sidebar)
        side_layout.setContentsMargins(18, 18, 18, 18)
        side_layout.setSpacing(10)

        self.title = QtWidgets.QLabel()
        self.title.setObjectName("AppTitle")
        self.subtitle = QtWidgets.QLabel()
        self.subtitle.setObjectName("AppSubtitle")

        self.btn_import_queue = QtWidgets.QPushButton()
        self.btn_import_queue.clicked.connect(self.import_urls)

        self.btn_scan = QtWidgets.QPushButton()
        self.btn_scan.clicked.connect(self.start_scan)

        self.btn_start = QtWidgets.QPushButton()
        self.btn_start.clicked.connect(self.start_download_selected)
        self.btn_start.setEnabled(False)

        self.btn_stop = QtWidgets.QPushButton()
        self.btn_stop.clicked.connect(self.stop_worker)
        self.btn_stop.setEnabled(False)

        self.workers_spin = QtWidgets.QSpinBox()
        self.workers_spin.setRange(1, 8)
        self.workers_spin.setValue(3)

        workers_wrap = QtWidgets.QHBoxLayout()
        self.workers_label = QtWidgets.QLabel()
        workers_wrap.addWidget(self.workers_label)
        workers_wrap.addWidget(self.workers_spin, 1)

        lang_wrap = QtWidgets.QHBoxLayout()
        self.lang_label = QtWidgets.QLabel()
        self.lang_combo = QtWidgets.QComboBox()
        self.lang_combo.addItem("", "ru")
        self.lang_combo.addItem("", "en")
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_wrap.addWidget(self.lang_label)
        lang_wrap.addWidget(self.lang_combo, 1)

        self.base_dir_edit = QtWidgets.QLineEdit()
        self.btn_pick_dir = QtWidgets.QPushButton()
        self.btn_pick_dir.clicked.connect(self.pick_folder)

        self.btn_save_settings = QtWidgets.QPushButton()
        self.btn_save_settings.clicked.connect(self.save_settings)

        side_layout.addWidget(self.title)
        side_layout.addWidget(self.subtitle)
        side_layout.addSpacing(12)
        side_layout.addLayout(workers_wrap)
        side_layout.addLayout(lang_wrap)
        side_layout.addWidget(self.base_dir_edit)
        side_layout.addWidget(self.btn_pick_dir)
        side_layout.addWidget(self.btn_save_settings)
        side_layout.addSpacing(8)
        side_layout.addWidget(self.btn_import_queue)
        side_layout.addWidget(self.btn_scan)
        side_layout.addWidget(self.btn_start)
        side_layout.addWidget(self.btn_stop)
        side_layout.addStretch(1)

        # ── Content ──────────────────────────────────────────────────────────
        content = QtWidgets.QFrame()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(12)

        # URL input bar (manual add + clear)
        top_bar = QtWidgets.QFrame()
        top_layout = QtWidgets.QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)
        self.url_input = QtWidgets.QLineEdit()
        self.btn_add = QtWidgets.QPushButton()
        self.btn_add.clicked.connect(self.add_url)
        self.btn_clear = QtWidgets.QPushButton()
        self.btn_clear.clicked.connect(self.clear_queue)
        top_layout.addWidget(self.url_input, 1)
        top_layout.addWidget(self.btn_add)
        top_layout.addWidget(self.btn_clear)

        # Gallery toolbar
        gallery_toolbar = QtWidgets.QFrame()
        gt_layout = QtWidgets.QHBoxLayout(gallery_toolbar)
        gt_layout.setContentsMargins(0, 0, 0, 0)
        gt_layout.setSpacing(6)
        self.btn_select_all = QtWidgets.QPushButton()
        self.btn_select_all.clicked.connect(lambda: self._select_all_gallery(True))
        self.btn_deselect_all = QtWidgets.QPushButton()
        self.btn_deselect_all.clicked.connect(lambda: self._select_all_gallery(False))
        self.btn_size_small = QtWidgets.QPushButton()
        self.btn_size_small.clicked.connect(lambda: self._set_thumb_size(70))
        self.btn_size_medium = QtWidgets.QPushButton()
        self.btn_size_medium.clicked.connect(lambda: self._set_thumb_size(120))
        self.btn_size_large = QtWidgets.QPushButton()
        self.btn_size_large.clicked.connect(lambda: self._set_thumb_size(200))
        self.btn_clear_gallery = QtWidgets.QPushButton()
        self.btn_clear_gallery.clicked.connect(self._clear_gallery)
        gt_layout.addWidget(self.btn_select_all)
        gt_layout.addWidget(self.btn_deselect_all)
        gt_layout.addSpacing(10)
        gt_layout.addWidget(self.btn_size_small)
        gt_layout.addWidget(self.btn_size_medium)
        gt_layout.addWidget(self.btn_size_large)
        gt_layout.addStretch(1)
        gt_layout.addWidget(self.btn_clear_gallery)

        # Gallery — the main view (thumbnails with checkboxes)
        self.gallery = QtWidgets.QListWidget()
        self.gallery.setViewMode(QtWidgets.QListWidget.IconMode)
        self.gallery.setIconSize(QtCore.QSize(self._thumb_size, self._thumb_size))
        self.gallery.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.gallery.setSpacing(6)
        self.gallery.setMovement(QtWidgets.QListWidget.Static)
        self.gallery.setWordWrap(True)
        self.gallery.setTextElideMode(QtCore.Qt.ElideRight)
        self.gallery.setUniformItemSizes(True)
        # Toggle check on click
        self.gallery.itemClicked.connect(self._toggle_item_check)

        self.gallery_group = QtWidgets.QGroupBox()
        ggl = QtWidgets.QVBoxLayout(self.gallery_group)
        ggl.setSpacing(6)
        ggl.addWidget(gallery_toolbar)
        ggl.addWidget(self.gallery)

        # Progress row
        progress_row = QtWidgets.QFrame()
        pr_layout = QtWidgets.QHBoxLayout(progress_row)
        pr_layout.setContentsMargins(0, 0, 0, 0)
        pr_layout.setSpacing(8)
        self.global_progress = QtWidgets.QProgressBar()
        self.global_progress.setRange(0, 100)
        self.global_progress.setValue(0)
        self.status_label = QtWidgets.QLabel()
        self.status_label.setObjectName("StatusLabel")
        pr_layout.addWidget(self.global_progress, 1)
        pr_layout.addWidget(self.status_label)

        # Logs
        logs_split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        logs_split.setChildrenCollapsible(False)
        self.engine_log = QtWidgets.QPlainTextEdit()
        self.engine_log.setReadOnly(True)
        self.error_log = QtWidgets.QPlainTextEdit()
        self.error_log.setReadOnly(True)
        self.error_log.setPlaceholderText("errors.log")
        self.debug_log = QtWidgets.QPlainTextEdit()
        self.debug_log.setReadOnly(True)
        self.debug_log.setPlaceholderText("debug.log")
        self.engine_group = QtWidgets.QGroupBox()
        lw = QtWidgets.QVBoxLayout(self.engine_group)
        lw.addWidget(self.engine_log)
        self.right_wrap = QtWidgets.QTabWidget()
        err_tab = QtWidgets.QWidget()
        et = QtWidgets.QVBoxLayout(err_tab)
        et.addWidget(self.error_log)
        dbg_tab = QtWidgets.QWidget()
        dt = QtWidgets.QVBoxLayout(dbg_tab)
        dt.addWidget(self.debug_log)
        self.right_wrap.addTab(err_tab, "")
        self.right_wrap.addTab(dbg_tab, "")
        logs_split.addWidget(self.engine_group)
        logs_split.addWidget(self.right_wrap)
        logs_split.setSizes([650, 500])

        # Gallery + logs in vertical splitter (gallery takes more space)
        v_split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        v_split.setChildrenCollapsible(False)
        v_split.addWidget(self.gallery_group)
        v_split.addWidget(logs_split)
        v_split.setSizes([480, 220])

        content_layout.addWidget(top_bar)
        content_layout.addWidget(v_split, 1)
        content_layout.addWidget(progress_row)

        main.addWidget(sidebar)
        main.addWidget(content, 1)
        self.setCentralWidget(root)

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QMainWindow { background: #0f172a; color: #e5e7eb; }
            #Sidebar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #111827, stop:1 #1f2937);
                border-right: 1px solid #334155;
            }
            #AppTitle { font-size: 21px; font-weight: 700; color: #f8fafc; }
            #AppSubtitle { font-size: 12px; color: #94a3b8; }
            #StatusLabel { color: #93c5fd; font-weight: 600; }
            QLineEdit, QPlainTextEdit, QGroupBox, QTabWidget::pane {
                background: #111827;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            QLineEdit { padding: 10px; font-size: 13px; }
            QPlainTextEdit { padding: 8px; font-family: Consolas, monospace; font-size: 12px; }
            QGroupBox { font-weight: 600; margin-top: 8px; padding-top: 8px; }
            QHeaderView::section { background: #0b1220; color: #cbd5e1; border: none; padding: 8px; }
            QProgressBar {
                background: #111827;
                border: 1px solid #334155;
                border-radius: 8px;
                text-align: center;
                color: #cbd5e1;
                min-height: 24px;
            }
            QProgressBar::chunk { background: #0b5ed7; border-radius: 7px; }
            QPushButton {
                background: #0b5ed7;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:pressed { background: #1e40af; }
            QPushButton:disabled { background: #334155; color: #94a3b8; }
            QListWidget {
                background: #0b1220;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #cbd5e1;
                font-size: 11px;
            }
            QListWidget::item { border-radius: 4px; padding: 2px; }
            QListWidget::item:selected { background: #1e3a5f; color: #93c5fd; }
            """
        )

    def _setup_timers(self):
        self._log_timer = QtCore.QTimer(self)
        self._log_timer.timeout.connect(self.refresh_logs)
        self._log_timer.start(1500)

    def _load_settings(self):
        base = self.settings.get("base_dir", os.path.join(SCRIPT_DIR, "downloads"))
        workers = int(self.settings.get("workers", 3))
        self.base_dir_edit.setText(base)
        self.workers_spin.setValue(max(1, min(8, workers)))
        idx = self.lang_combo.findData(self.lang)
        self.lang_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._apply_translations()

    def _t(self, key, **kwargs):
        table = I18N.get(self.lang, I18N["ru"])
        text = table.get(key, key)
        return text.format(**kwargs) if kwargs else text

    def _apply_translations(self):
        self.setWindowTitle(self._t("window_title"))
        self.title.setText(self._t("app_title"))
        self.subtitle.setText(self._t("app_subtitle"))
        self.workers_label.setText(self._t("workers"))
        self.lang_label.setText(self._t("language"))
        self.lang_combo.setItemText(0, self._t("lang_ru"))
        self.lang_combo.setItemText(1, self._t("lang_en"))
        self.base_dir_edit.setPlaceholderText(self._t("download_folder_placeholder"))
        self.btn_pick_dir.setText(self._t("pick_folder"))
        self.btn_save_settings.setText(self._t("save_settings"))
        self.btn_import_queue.setText(self._t("import_txt"))
        self.btn_scan.setText(self._t("scan_preview"))
        self.btn_start.setText(self._t("start_download"))
        self.btn_stop.setText(self._t("stop"))
        self.url_input.setPlaceholderText(self._t("url_placeholder"))
        self.btn_add.setText(self._t("add"))
        self.btn_clear.setText(self._t("clear_queue"))
        self.engine_log.setPlaceholderText(self._t("engine_log_placeholder"))
        self.engine_group.setTitle(self._t("engine_group"))
        self.right_wrap.setTabText(0, self._t("errors_tab"))
        self.right_wrap.setTabText(1, self._t("debug_tab"))
        self.btn_select_all.setText(self._t("select_all"))
        self.btn_deselect_all.setText(self._t("deselect_all"))
        self.btn_size_small.setText(self._t("size_small"))
        self.btn_size_medium.setText(self._t("size_medium"))
        self.btn_size_large.setText(self._t("size_large"))
        self.btn_clear_gallery.setText(self._t("clear_gallery"))
        self.gallery_group.setTitle(self._t("gallery_group"))
        if not self.status_label.text().strip():
            self.status_label.setText(self._t("status_ready"))

    def _on_language_changed(self, _index):
        lang = self.lang_combo.currentData()
        if lang in I18N and lang != self.lang:
            self.lang = lang
            self._apply_translations()
            self.save_settings(quiet=True)

    def save_settings(self, quiet=False):
        self.settings["base_dir"] = self.base_dir_edit.text().strip() or os.path.join(SCRIPT_DIR, "downloads")
        self.settings["workers"] = int(self.workers_spin.value())
        self.settings["lang"] = self.lang
        save_json(SETTINGS_FILE, self.settings)
        if not quiet:
            self.status_label.setText(self._t("settings_saved"))

    def pick_folder(self):
        cur = self.base_dir_edit.text().strip() or SCRIPT_DIR
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, self._t("pick_folder_dialog"), cur)
        if folder:
            self.base_dir_edit.setText(folder)

    # ── Queue management ──────────────────────────────────────────────────

    def add_url(self):
        url = self.url_input.text().strip()
        if not url:
            return
        if not url.startswith("http"):
            self.status_label.setText(self._t("invalid_url"))
            return
        if url not in self._queued_urls:
            self._queued_urls.append(url)
        self.url_input.clear()
        self.status_label.setText(self._t("queued_count", count=len(self._queued_urls)))

    def clear_queue(self):
        self._queued_urls.clear()
        self._batch_name = None
        self.global_progress.setValue(0)
        self.status_label.setText(self._t("queue_cleared"))

    def import_urls(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, self._t("import_file_dialog"), SCRIPT_DIR, "Text files (*.txt)"
        )
        if not file_path:
            return
        self._batch_name = os.path.splitext(os.path.basename(file_path))[0]
        added = 0
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line.startswith("http"):
                    continue
                if line not in self._queued_urls:
                    self._queued_urls.append(line)
                added += 1
        self.status_label.setText(self._t("imported_count", count=added))

    # ── Gallery helpers ───────────────────────────────────────────────────

    def _select_all_gallery(self, checked):
        state = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
        for i in range(self.gallery.count()):
            self.gallery.item(i).setCheckState(state)

    def _set_thumb_size(self, size):
        self._thumb_size = size
        self.gallery.setIconSize(QtCore.QSize(size, size))

    def _clear_gallery(self):
        self.gallery.clear()
        self.btn_start.setEnabled(False)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def _toggle_item_check(self, item):
        new = QtCore.Qt.Unchecked if item.checkState() == QtCore.Qt.Checked else QtCore.Qt.Checked
        item.setCheckState(new)

    # ── Scan workflow ─────────────────────────────────────────────────────

    @QtCore.Slot()
    def start_scan(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.status_label.setText(self._t("backend_running"))
            return
        if not self._queued_urls:
            self.status_label.setText(self._t("queue_empty"))
            return

        self.save_settings()
        base_dir = self.base_dir_edit.text().strip() or os.path.join(SCRIPT_DIR, "downloads")
        workers = int(self.workers_spin.value())

        self.engine_log.clear()
        self.global_progress.setValue(0)
        self._clear_gallery()

        self.worker = PreviewWorker(
            list(self._queued_urls), base_dir, workers, batch_name=self._batch_name
        )
        self.worker_thread = QtCore.QThread(self)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.image_found.connect(self._on_image_found)
        self.worker.status.connect(self._on_status)
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self._set_ui_busy(True)
        self.status_label.setText(self._t("starting_scan"))
        self.worker_thread.start()

    @QtCore.Slot(str, str, str, str)
    def _on_image_found(self, album_title, url, filename, thumb_url):
        """Called for each resolved image — adds checkable item, loads CDN thumbnail."""
        item = QtWidgets.QListWidgetItem(filename or os.path.basename(url))
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
        item.setCheckState(QtCore.Qt.Checked)
        item.setData(QtCore.Qt.UserRole, {"album_title": album_title, "url": url, "filename": filename})
        item.setToolTip(f"{album_title}\n{url}")
        self.gallery.addItem(item)

        loader = CdnThumbnailLoader(item, thumb_url or url, self._thumb_size)
        loader.signals.loaded.connect(self._on_thumbnail_loaded)
        QtCore.QThreadPool.globalInstance().start(loader)

    @QtCore.Slot(object, QtGui.QPixmap)
    def _on_thumbnail_loaded(self, item, pixmap):
        item.setIcon(QtGui.QIcon(pixmap))

    @QtCore.Slot(int)
    def _on_scan_finished(self, count):
        self._set_ui_busy(False)
        self.worker = None
        self.worker_thread = None
        self.btn_start.setEnabled(count > 0)
        self.status_label.setText(self._t("scan_done", count=count))

    # ── Download workflow ─────────────────────────────────────────────────

    @QtCore.Slot()
    def start_download_selected(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.status_label.setText(self._t("backend_running"))
            return

        selected = []
        for i in range(self.gallery.count()):
            item = self.gallery.item(i)
            if item and item.checkState() == QtCore.Qt.Checked:
                data = item.data(QtCore.Qt.UserRole)
                if data:
                    selected.append((data["album_title"], {"url": data["url"], "filename": data["filename"]}))

        if not selected:
            self.status_label.setText(self._t("no_selected"))
            return

        self.save_settings()
        base_dir = self.base_dir_edit.text().strip() or os.path.join(SCRIPT_DIR, "downloads")
        workers = int(self.workers_spin.value())

        self.engine_log.clear()
        self.global_progress.setValue(0)

        self.worker = DownloadWorker(selected, base_dir, workers)
        self.worker_thread = QtCore.QThread(self)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log.connect(self._append_engine_log)
        self.worker.status.connect(self._on_status)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_download_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self._set_ui_busy(True)
        self.status_label.setText(self._t("starting_download"))
        self.worker_thread.start()

    @QtCore.Slot()
    def stop_worker(self):
        if self.worker:
            self.worker.stop()
            self.status_label.setText(self._t("stopping"))

    # ── Shared UI helpers ─────────────────────────────────────────────────

    def _set_ui_busy(self, busy):
        self.btn_scan.setEnabled(not busy)
        self.btn_start.setEnabled(not busy)
        self.btn_import_queue.setEnabled(not busy)
        self.btn_stop.setEnabled(busy)

    @QtCore.Slot(str)
    def _on_status(self, text):
        self.status_label.setText(text)

    @QtCore.Slot(str)
    def _append_engine_log(self, msg):
        self.engine_log.appendPlainText(msg)
        cursor = self.engine_log.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.engine_log.setTextCursor(cursor)

    @QtCore.Slot(int, int)
    def _on_progress(self, done, total):
        if total <= 0:
            self.global_progress.setValue(0)
            return
        self.global_progress.setValue(max(0, min(100, int(done / total * 100))))

    @QtCore.Slot(dict)
    def _on_download_finished(self, summary):
        self._set_ui_busy(False)
        self.btn_start.setEnabled(True)
        self.worker = None
        self.worker_thread = None
        cancelled = summary.get("cancelled")
        key = "cancelled_summary" if cancelled else "done_summary"
        self.status_label.setText(self._t(
            key,
            albums=summary.get("albums", 0),
            downloaded=summary.get("downloaded", 0),
            skipped=summary.get("skipped", 0),
            errors=summary.get("errors", 0),
        ))

    def refresh_logs(self):
        self._set_log_text(self.error_log, ERROR_LOG_FILE)
        self._set_log_text(self.debug_log, DEBUG_LOG_FILE)

    @staticmethod
    def _set_log_text(widget: QtWidgets.QPlainTextEdit, path: str):
        if not os.path.exists(path):
            widget.setPlainText("")
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                data = fh.read()
            if widget.toPlainText() != data:
                widget.setPlainText(data)
                cursor = widget.textCursor()
                cursor.movePosition(QtGui.QTextCursor.End)
                widget.setTextCursor(cursor)
        except Exception:
            pass


def run_qt():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("JPG6 Downloader Pro")
    window = DownloaderQtWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_qt())

import json
import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from backend import CONFIG_DIR, DEBUG_LOG_FILE, ERROR_LOG_FILE, DownloadBackend, classify_url

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
        "start_download": "Start Download",
        "stop": "Stop",
        "url_placeholder": "Paste album/profile/image URL and click Add",
        "add": "Add",
        "remove_selected": "Remove Selected",
        "clear_queue": "Clear Queue",
        "table_url": "URL",
        "table_type": "Type",
        "table_status": "Status",
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
        "imported_count": "Imported {count} URLs",
        "backend_running": "Backend already running",
        "queue_empty": "Queue is empty",
        "starting_backend": "Starting backend...",
        "stopping": "Stopping...",
        "cancelled_summary": "Cancelled | albums={albums} downloaded={downloaded} skipped={skipped} errors={errors}",
        "done_summary": "Done | albums={albums} downloaded={downloaded} skipped={skipped} errors={errors}",
        "lang_ru": "Russian",
        "lang_en": "English",
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
        "start_download": "Начать загрузку",
        "stop": "Стоп",
        "url_placeholder": "Вставьте ссылку на альбом/профиль/изображение и нажмите Добавить",
        "add": "Добавить",
        "remove_selected": "Удалить выбранные",
        "clear_queue": "Очистить очередь",
        "table_url": "URL",
        "table_type": "Тип",
        "table_status": "Статус",
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
        "imported_count": "Импортировано URL: {count}",
        "backend_running": "Движок уже запущен",
        "queue_empty": "Очередь пуста",
        "starting_backend": "Запуск движка...",
        "stopping": "Остановка...",
        "cancelled_summary": "Остановлено | альбомов={albums} скачано={downloaded} пропущено={skipped} ошибок={errors}",
        "done_summary": "Готово | альбомов={albums} скачано={downloaded} пропущено={skipped} ошибок={errors}",
        "lang_ru": "Русский",
        "lang_en": "Английский",
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


class BackendWorker(QtCore.QObject):
    log = QtCore.Signal(str)
    status = QtCore.Signal(str)
    item_status = QtCore.Signal(str, str)
    progress = QtCore.Signal(int, int)
    finished = QtCore.Signal(dict)

    def __init__(self, urls, base_dir, workers):
        super().__init__()
        self.urls = list(urls)
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
            item_status_cb=self.item_status.emit,
            progress_cb=self.progress.emit,
        )
        summary = self.backend.run_batch(self.urls)
        self.finished.emit(summary)

    @QtCore.Slot()
    def stop(self):
        if self.backend:
            self.backend.cancel()


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

        self._build_ui()
        self._apply_styles()
        self._setup_timers()
        self._load_settings()

    def _build_ui(self):
        root = QtWidgets.QWidget()
        main = QtWidgets.QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

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

        self.btn_start = QtWidgets.QPushButton()
        self.btn_start.clicked.connect(self.start_backend)

        self.btn_stop = QtWidgets.QPushButton()
        self.btn_stop.clicked.connect(self.stop_backend)
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
        side_layout.addWidget(self.btn_start)
        side_layout.addWidget(self.btn_stop)
        side_layout.addStretch(1)

        content = QtWidgets.QFrame()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(12)

        top_bar = QtWidgets.QFrame()
        top_layout = QtWidgets.QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        self.url_input = QtWidgets.QLineEdit()
        self.btn_add = QtWidgets.QPushButton()
        self.btn_add.clicked.connect(self.add_url)
        self.btn_remove = QtWidgets.QPushButton()
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear = QtWidgets.QPushButton()
        self.btn_clear.clicked.connect(self.clear_queue)

        top_layout.addWidget(self.url_input, 1)
        top_layout.addWidget(self.btn_add)
        top_layout.addWidget(self.btn_remove)
        top_layout.addWidget(self.btn_clear)

        self.queue_table = QtWidgets.QTableWidget(0, 3)
        self.queue_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.queue_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.queue_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.queue_table.setAlternatingRowColors(True)

        progress_row = QtWidgets.QFrame()
        progress_layout = QtWidgets.QHBoxLayout(progress_row)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)

        self.global_progress = QtWidgets.QProgressBar()
        self.global_progress.setRange(0, 100)
        self.global_progress.setValue(0)

        self.status_label = QtWidgets.QLabel()
        self.status_label.setObjectName("StatusLabel")

        progress_layout.addWidget(self.global_progress, 1)
        progress_layout.addWidget(self.status_label)

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

        content_layout.addWidget(top_bar)
        content_layout.addWidget(self.queue_table, 4)
        content_layout.addWidget(progress_row)
        content_layout.addWidget(logs_split, 3)

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
            QLineEdit, QPlainTextEdit, QTableWidget, QGroupBox, QTabWidget::pane {
                background: #111827;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            QLineEdit { padding: 10px; font-size: 13px; }
            QPlainTextEdit { padding: 8px; font-family: Consolas, monospace; font-size: 12px; }
            QGroupBox { font-weight: 600; margin-top: 8px; padding-top: 8px; }
            QTableWidget { gridline-color: #334155; font-size: 13px; }
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
        self.btn_start.setText(self._t("start_download"))
        self.btn_stop.setText(self._t("stop"))

        self.url_input.setPlaceholderText(self._t("url_placeholder"))
        self.btn_add.setText(self._t("add"))
        self.btn_remove.setText(self._t("remove_selected"))
        self.btn_clear.setText(self._t("clear_queue"))

        self.queue_table.setHorizontalHeaderLabels([
            self._t("table_url"),
            self._t("table_type"),
            self._t("table_status"),
        ])

        self.engine_log.setPlaceholderText(self._t("engine_log_placeholder"))
        self.engine_group.setTitle(self._t("engine_group"))
        self.right_wrap.setTabText(0, self._t("errors_tab"))
        self.right_wrap.setTabText(1, self._t("debug_tab"))

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

    def add_url(self):
        url = self.url_input.text().strip()
        if not url:
            return
        if not url.startswith("http"):
            self.status_label.setText(self._t("invalid_url"))
            return

        row = self.queue_table.rowCount()
        self.queue_table.insertRow(row)
        self.queue_table.setItem(row, 0, QtWidgets.QTableWidgetItem(url))
        self.queue_table.setItem(row, 1, QtWidgets.QTableWidgetItem(classify_url(url)))
        self.queue_table.setItem(row, 2, QtWidgets.QTableWidgetItem("queued"))
        self.url_input.clear()
        self.status_label.setText(self._t("queued_count", count=self.queue_table.rowCount()))

    def remove_selected(self):
        rows = sorted({i.row() for i in self.queue_table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.queue_table.removeRow(row)
        self.status_label.setText(self._t("queued_count", count=self.queue_table.rowCount()))

    def clear_queue(self):
        self.queue_table.setRowCount(0)
        self.global_progress.setValue(0)
        self.status_label.setText(self._t("queue_cleared"))

    def import_urls(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, self._t("import_file_dialog"), SCRIPT_DIR, "Text files (*.txt)")
        if not file_path:
            return
        added = 0
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line.startswith("http"):
                    continue
                self.url_input.setText(line)
                self.add_url()
                added += 1
            self.status_label.setText(self._t("imported_count", count=added))

    def _collect_queue_urls(self):
        rows = self.queue_table.rowCount()
        result = []
        for i in range(rows):
            item = self.queue_table.item(i, 0)
            if item:
                result.append(item.text().strip())
        return result

    def _set_row_status(self, url, status):
        rows = self.queue_table.rowCount()
        for i in range(rows):
            item = self.queue_table.item(i, 0)
            if item and item.text().strip() == url:
                self.queue_table.setItem(i, 2, QtWidgets.QTableWidgetItem(status))

    @QtCore.Slot()
    def start_backend(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.status_label.setText(self._t("backend_running"))
            return

        urls = self._collect_queue_urls()
        if not urls:
            self.status_label.setText(self._t("queue_empty"))
            return

        self.save_settings()
        base_dir = self.base_dir_edit.text().strip() or os.path.join(SCRIPT_DIR, "downloads")
        workers = int(self.workers_spin.value())

        self.engine_log.clear()
        self.global_progress.setValue(0)

        self.worker = BackendWorker(urls, base_dir, workers)
        self.worker_thread = QtCore.QThread(self)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log.connect(self._append_engine_log)
        self.worker.status.connect(self._on_backend_status)
        self.worker.item_status.connect(self._set_row_status)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_backend_finished)

        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText(self._t("starting_backend"))

        self.worker_thread.start()

    @QtCore.Slot()
    def stop_backend(self):
        if self.worker:
            self.worker.stop()
            self.status_label.setText(self._t("stopping"))

    @QtCore.Slot(str)
    def _append_engine_log(self, msg):
        self.engine_log.appendPlainText(msg)
        cursor = self.engine_log.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.engine_log.setTextCursor(cursor)

    @QtCore.Slot(str)
    def _on_backend_status(self, text):
        self.status_label.setText(text)

    @QtCore.Slot(int, int)
    def _on_progress(self, done, total):
        if total <= 0:
            self.global_progress.setValue(0)
            return
        pct = int((done / total) * 100)
        self.global_progress.setValue(max(0, min(100, pct)))

    @QtCore.Slot(dict)
    def _on_backend_finished(self, summary):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.worker = None
        self.worker_thread = None

        cancelled = summary.get("cancelled")
        albums = summary.get("albums", 0)
        downloaded = summary.get("downloaded", 0)
        skipped = summary.get("skipped", 0)
        errors = summary.get("errors", 0)
        if cancelled:
            self.status_label.setText(self._t(
                "cancelled_summary",
                albums=albums,
                downloaded=downloaded,
                skipped=skipped,
                errors=errors,
            ))
        else:
            self.status_label.setText(self._t(
                "done_summary",
                albums=albums,
                downloaded=downloaded,
                skipped=skipped,
                errors=errors,
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

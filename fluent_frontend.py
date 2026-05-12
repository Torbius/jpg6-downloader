import json
import os
import urllib.request
from io import BytesIO
from PIL import Image
from backend import DownloadBackend
import sys

from PySide6.QtCore import Qt, QUrl, Signal, QThread
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QVBoxLayout, QWidget, QFileDialog

from qfluentwidgets import (NavigationItemPosition, MSFluentWindow,
                            SubtitleLabel, setFont, FluentIcon as FIF,
                            ScrollArea, SettingCardGroup, PushSettingCard,
                            ComboBoxSettingCard, SpinBox, SettingCard, InfoBar, InfoBarPosition)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(SCRIPT_DIR, "config")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")


class Widget(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(text.replace(' ', '-'))
        self.label = SubtitleLabel(text, self)
        self.label.setAlignment(Qt.AlignCenter)
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)
        self.vBoxLayout.setContentsMargins(0, 32, 0, 0)

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QSpacerItem, QSizePolicy, QFrame
from qfluentwidgets import (LineEdit, ToolButton, PushButton, PrimaryPushButton,
                            FlowLayout, ProgressBar, SegmentedWidget, TextEdit,
                            BodyLabel, CaptionLabel, CardWidget, TransparentToolButton)

from PySide6.QtCore import QThread, Signal
from backend import DownloadBackend
import urllib.request
from io import BytesIO
try:
    from PIL import Image
except ImportError:
    pass

class PreviewWorker(QThread):
    status_signal = Signal(str)
    log_signal = Signal(str)
    image_found_signal = Signal(str, str, str, str)  # album_title, url, filename, thumb_url
    finished_signal = Signal(int)

    def __init__(self, urls, base_dir, workers, batch_name=None, parent=None):
        super().__init__(parent)
        self.urls = list(urls)
        self.base_dir = base_dir
        self.workers = workers
        self.batch_name = batch_name
        self.backend = None

    def run(self):
        count = [0]
        self.backend = DownloadBackend(
            base_dir=self.base_dir,
            workers=self.workers,
            status_cb=lambda msg: self.status_signal.emit(msg),
            logger=lambda msg: self.log_signal.emit(msg)
        )

        def _cb(album_title, img):
            count[0] += 1
            self.image_found_signal.emit(
                album_title,
                img.get("url", ""),
                img.get("filename", ""),
                img.get("thumb_url") or img.get("url", "")
            )

        self.backend.scan_for_preview(
            self.urls, batch_name=self.batch_name, image_found_cb=_cb
        )
        self.finished_signal.emit(count[0])

    def stop(self):
        if self.backend:
            self.backend.cancel()
        self.quit()
        self.wait()

class DownloadWorker(QThread):
    status_signal = Signal(str)
    log_signal = Signal(str)
    progress_signal = Signal(int, int) # done, total
    file_progress_signal = Signal(str, int, int) # filename, done, total
    finished_signal = Signal(dict)

    def __init__(self, selected, base_dir, workers, batch_name=None, parent=None):
        super().__init__(parent)
        self.selected = selected
        self.base_dir = base_dir
        self.workers = workers
        self.batch_name = batch_name
        self.backend = None

    def run(self):
        self.backend = DownloadBackend(
            base_dir=self.base_dir,
            workers=self.workers,
            logger=lambda msg: self.log_signal.emit(msg),
            status_cb=lambda msg: self.status_signal.emit(msg),
            progress_cb=lambda d, t: self.progress_signal.emit(d, t),
            file_progress_cb=lambda fn, d, t: self.file_progress_signal.emit(fn, d, t)
        )
        if self.batch_name:
            self.backend._batch_name = self.batch_name
        summary = self.backend.download_selected(self.selected)
        self.finished_signal.emit(summary)

    def stop(self):
        if self.backend:
            self.backend.cancel()
        self.quit()
        self.wait()

class CdnThumbnailLoader(QThread):
    loaded_signal = Signal(object) # PIL Image

    def __init__(self, url: str, size: int, parent=None):
        super().__init__(parent)
        self.url = url
        self.size = size

    def run(self):
        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            img = Image.open(BytesIO(data)).convert("RGB")
            img.thumbnail((self.size, self.size), Image.LANCZOS)
            self.loaded_signal.emit(img)
        except Exception:
            pass


from PySide6.QtGui import QColor, QFont, QPixmap, QImage
from PySide6.QtWidgets import QSpacerItem, QSizePolicy, QFrame, QLabel
from qfluentwidgets import CheckBox, InfoBar, InfoBarPosition, Flyout, FlyoutAnimationType


class ThumbnailCard(CardWidget):
    def __init__(self, album_title, url, filename, thumb_url, parent=None):
        super().__init__(parent)
        self.album_title = album_title
        self.url = url
        self.filename = filename
        self.thumb_url = thumb_url
        self.setFixedSize(160, 200)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)

        self.imageLabel = QLabel(self)
        self.imageLabel.setFixedSize(144, 144)
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border-radius: 8px;")

        self.layout.addWidget(self.imageLabel)

        self.bottomLayout = QHBoxLayout()
        self.bottomLayout.setContentsMargins(0, 0, 0, 0)

        display_name = self.filename if self.filename else url.split("/")[-1]
        self.nameLabel = CaptionLabel(display_name, self)

        # truncate text to fit inside card width
        fontMetrics = self.nameLabel.fontMetrics()
        elidedText = fontMetrics.elidedText(display_name, Qt.ElideRight, 100)
        self.nameLabel.setText(elidedText)

        self.checkBox = CheckBox(self)
        self.checkBox.setChecked(True)

        self.bottomLayout.addWidget(self.nameLabel, 1)
        self.bottomLayout.addWidget(self.checkBox, 0)

        self.layout.addLayout(self.bottomLayout)

    def set_image(self, pil_image):
        import PIL.ImageQt
        qimage = PIL.ImageQt.ImageQt(pil_image)
        pixmap = QPixmap.fromImage(qimage)
        self.imageLabel.setPixmap(pixmap)

class DownloaderInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("DownloaderInterface")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(16)

        self._queued_urls = []
        self._queued_set = set()
        self._cards = []
        self._loaders = []
        self._worker = None
        self._batch_name = None

        self._build_top_bar()
        self._build_queue_area()
        self._build_gallery_area()
        self._build_bottom_bar()
        self._build_log_area()

        self._setup_bindings()

    def _build_top_bar(self):
        self.topBar = QFrame(self)
        self.topBarLayout = QHBoxLayout(self.topBar)
        self.topBarLayout.setContentsMargins(0, 0, 0, 0)

        self.urlInput = LineEdit(self.topBar)
        self.urlInput.setPlaceholderText("Paste album / profile / image URL...")
        self.urlInput.setClearButtonEnabled(True)
        self.topBarLayout.addWidget(self.urlInput, 1)

        self.btnPaste = ToolButton(FIF.PASTE, self.topBar)
        self.btnPaste.setToolTip("Smart Paste")
        self.topBarLayout.addWidget(self.btnPaste)

        self.btnAdd = PushButton(self.tr("Add URL"), self.topBar, FIF.ADD)
        self.topBarLayout.addWidget(self.btnAdd)

        self.btnImport = PushButton(self.tr("Import TXT"), self.topBar, FIF.DOCUMENT)
        self.topBarLayout.addWidget(self.btnImport)

        self.btnScan = PrimaryPushButton(self.tr("Scan & Preview"), self.topBar, FIF.SEARCH)
        self.topBarLayout.addWidget(self.btnScan)

        self.btnClearQueue = PushButton(self.tr("Clear Queue"), self.topBar, FIF.DELETE)
        self.topBarLayout.addWidget(self.btnClearQueue)

        self.layout.addWidget(self.topBar)

    def _build_queue_area(self):
        self.queueArea = ScrollArea(self)
        self.queueArea.setWidgetResizable(True)
        self.queueArea.setFixedHeight(120)
        self.queueArea.setStyleSheet("ScrollArea { background-color: transparent; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px;}")

        self.queueWidget = QWidget()
        self.queueLayout = QVBoxLayout(self.queueWidget)
        self.queueLayout.setAlignment(Qt.AlignTop)
        self.queueLayout.setContentsMargins(8, 8, 8, 8)
        self.queueArea.setWidget(self.queueWidget)

        self.layout.addWidget(self.queueArea)

    def _build_gallery_area(self):
        self.galleryArea = ScrollArea(self)
        self.galleryArea.setWidgetResizable(True)
        self.galleryArea.setStyleSheet("ScrollArea { background-color: transparent; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px;}")

        self.galleryWidget = QWidget()
        self.galleryLayout = FlowLayout(self.galleryWidget)
        self.galleryLayout.setContentsMargins(16, 16, 16, 16)
        self.galleryLayout.setVerticalSpacing(16)
        self.galleryLayout.setHorizontalSpacing(16)
        self.galleryArea.setWidget(self.galleryWidget)

        self.layout.addWidget(self.galleryArea, 1)

    def _build_bottom_bar(self):
        self.bottomBar = QFrame(self)
        self.bottomBarLayout = QHBoxLayout(self.bottomBar)
        self.bottomBarLayout.setContentsMargins(0, 0, 0, 0)

        self.progressBar = ProgressBar(self.bottomBar)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        self.bottomBarLayout.addWidget(self.progressBar, 1)

        self.statusLabel = BodyLabel(self.tr("Ready"), self.bottomBar)
        self.statusLabel.setFixedWidth(240)
        self.bottomBarLayout.addWidget(self.statusLabel)

        self.btnDownload = PrimaryPushButton(self.tr("Download Selected"), self.bottomBar, FIF.DOWNLOAD)
        self.btnDownload.setEnabled(False)
        self.bottomBarLayout.addWidget(self.btnDownload)

        self.btnStop = PushButton(self.tr("Stop"), self.bottomBar, FIF.CANCEL)
        self.btnStop.setEnabled(False)
        self.bottomBarLayout.addWidget(self.btnStop)

        self.layout.addWidget(self.bottomBar)

    def _build_log_area(self):
        self.logArea = QWidget(self)
        self.logLayout = QVBoxLayout(self.logArea)
        self.logLayout.setContentsMargins(0, 0, 0, 0)

        self.pivot = SegmentedWidget(self.logArea)
        self.logLayout.addWidget(self.pivot, 0, Qt.AlignLeft)

        self.logStack = QWidget(self.logArea)
        self.logStackLayout = QVBoxLayout(self.logStack)
        self.logStackLayout.setContentsMargins(0, 0, 0, 0)

        # Engine Log
        self.logEngine = TextEdit(self.logStack)
        self.logEngine.setReadOnly(True)
        self.logEngine.setFont(QFont("Consolas", 10))
        self.logStackLayout.addWidget(self.logEngine)

        # Error Log
        self.logError = TextEdit(self.logStack)
        self.logError.setReadOnly(True)
        self.logError.setFont(QFont("Consolas", 10))
        self.logError.hide()
        self.logStackLayout.addWidget(self.logError)

        # Debug Log
        self.logDebug = TextEdit(self.logStack)
        self.logDebug.setReadOnly(True)
        self.logDebug.setFont(QFont("Consolas", 10))
        self.logDebug.hide()
        self.logStackLayout.addWidget(self.logDebug)

        self.pivot.addItem("Engine", self.tr("Engine"), lambda: self._switch_log(self.logEngine))
        self.pivot.addItem("Errors", self.tr("Errors"), lambda: self._switch_log(self.logError))
        self.pivot.addItem("Debug", self.tr("Debug"), lambda: self._switch_log(self.logDebug))
        self.pivot.setCurrentItem("Engine")

        self.logLayout.addWidget(self.logStack)
        self.logArea.setFixedHeight(180)

        self.layout.addWidget(self.logArea)

    def _switch_log(self, widget):
        self.logEngine.hide()
        self.logError.hide()
        self.logDebug.hide()
        widget.show()



    def _setup_bindings(self):
        self.btnAdd.clicked.connect(self._on_add_url)
        self.btnPaste.clicked.connect(self._on_paste_url)
        self.btnImport.clicked.connect(self._on_import_urls)
        self.btnClearQueue.clicked.connect(self._on_clear_queue)
        self.btnScan.clicked.connect(self._on_start_scan)
        self.btnDownload.clicked.connect(self._on_start_download)
        self.btnStop.clicked.connect(self._on_stop)

        self.urlInput.returnPressed.connect(self._on_add_url)

    def _on_add_url(self):
        url = self.urlInput.text().strip()
        if not url:
            return
        if not url.startswith("http"):
            self.statusLabel.setText(self.tr("Invalid URL — must start with http"))
            return

        if url not in self._queued_set:
            self._queued_urls.append(url)
            self._queued_set.add(url)
            self._add_queue_item_ui(url)

        self.urlInput.clear()
        self.statusLabel.setText(self.tr(f"In queue: {len(self._queued_urls)}"))

    def _on_paste_url(self):
        clip = QApplication.clipboard().text()
        lines = [ln.strip() for ln in clip.splitlines() if ln.strip().startswith("http")]
        if len(lines) > 1:
            for url in lines:
                if url not in self._queued_set:
                    self._queued_urls.append(url)
                    self._queued_set.add(url)
                    self._add_queue_item_ui(url)
            self.urlInput.clear()
            self.statusLabel.setText(self.tr(f"In queue: {len(self._queued_urls)}"))
        elif len(lines) == 1:
            self.urlInput.setText(lines[0])
            self.urlInput.setFocus()

    def _on_import_urls(self):
        from PySide6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Select TXT files with URLs"), SCRIPT_DIR, "Text files (*.txt)")
        if not paths:
            return

        if len(paths) == 1:
            self._batch_name = os.path.splitext(os.path.basename(paths[0]))[0]
        else:
            self._batch_name = None

        added = 0
        for path in paths:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        line = line.strip()
                        if line.startswith("http") and line not in self._queued_set:
                            self._queued_urls.append(line)
                            self._queued_set.add(line)
                            self._add_queue_item_ui(line)
                            added += 1
            except Exception as e:
                print(e)

        self.statusLabel.setText(self.tr(f"Imported {added} URLs"))

    def _add_queue_item_ui(self, url):
        # We cap visual items to 50 for performance like original
        if self.queueLayout.count() >= 50:
            return

        itemLayout = QHBoxLayout()
        itemLayout.setContentsMargins(0, 0, 0, 0)

        display_text = url if len(url) <= 80 else url[:77] + "..."
        lbl = BodyLabel(display_text, self.queueWidget)

        btn = TransparentToolButton(FIF.CLOSE, self.queueWidget)
        btn.clicked.connect(lambda _, u=url, l=itemLayout: self._remove_queued_url(u, l))

        itemLayout.addWidget(lbl, 1)
        itemLayout.addWidget(btn, 0)

        self.queueLayout.addLayout(itemLayout)

    def _remove_queued_url(self, url, layout):
        if url in self._queued_urls:
            self._queued_urls.remove(url)
        if url in self._queued_set:
            self._queued_set.remove(url)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        layout.deleteLater()
        self.statusLabel.setText(self.tr(f"In queue: {len(self._queued_urls)}"))

    def _on_clear_queue(self):
        self._queued_urls.clear()
        self._queued_set.clear()
        self._batch_name = None

        while self.queueLayout.count():
            item = self.queueLayout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    subitem = item.layout().takeAt(0)
                    if subitem.widget():
                        subitem.widget().deleteLater()
                item.layout().deleteLater()

        self.statusLabel.setText(self.tr("Queue cleared"))

    def _clear_gallery(self):
        self.galleryLayout.removeAllWidgets()
        self._cards.clear()

    def _set_ui_busy(self, busy: bool):
        self.btnScan.setEnabled(not busy)
        self.btnImport.setEnabled(not busy)
        self.btnAdd.setEnabled(not busy)
        self.btnStop.setEnabled(busy)
        if busy:
            self.btnDownload.setEnabled(False)

    def _on_start_scan(self):
        if self._worker and self._worker.isRunning():
            return

        if self.urlInput.text().strip():
            self._on_add_url()

        if not self._queued_urls:
            self.statusLabel.setText(self.tr("Queue is empty — add URLs first"))
            return

        settings_widget = self.window().settingsInterface
        base_dir = settings_widget.base_dir
        workers = settings_widget.workers

        self.logEngine.clear()
        self.progressBar.setMaximum(0) # Indeterminate mode
        self._clear_gallery()
        self._set_ui_busy(True)
        self.statusLabel.setText(self.tr("Scanning URLs..."))

        urls_to_scan = list(self._queued_urls)
        self._on_clear_queue()

        self._worker = PreviewWorker(urls_to_scan, base_dir, workers, batch_name=self._batch_name)
        self._worker.status_signal.connect(lambda txt: self.statusLabel.setText(txt))
        self._worker.log_signal.connect(self._append_engine_log)
        self._worker.image_found_signal.connect(self._on_image_found)
        self._worker.finished_signal.connect(self._on_scan_finished)
        self._worker.start()

    def _on_image_found(self, album_title, url, filename, thumb_url):
        card = ThumbnailCard(album_title, url, filename, thumb_url, self.galleryWidget)
        self.galleryLayout.addWidget(card)
        self._cards.append(card)

        # Start thumbnail loader
        loader = CdnThumbnailLoader(thumb_url or url, 160)
        # Prevent GC of loader
        self._loaders.append(loader)
        loader.loaded_signal.connect(lambda img, c=card, l=loader: self._on_thumb_loaded(img, c, l))
        loader.start()

    def _on_thumb_loaded(self, img, card, loader):
        card.set_image(img)
        if loader in self._loaders:
            self._loaders.remove(loader)

    def _on_scan_finished(self, count):
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(100 if count > 0 else 0)
        self._set_ui_busy(False)
        self._worker = None
        if count > 0:
            self.btnDownload.setEnabled(True)
        self.statusLabel.setText(self.tr(f"Scan complete: {count} images found"))

    def _on_start_download(self):
        if self._worker and self._worker.isRunning():
            return

        selected = []
        for card in self._cards:
            if card.checkBox.isChecked():
                selected.append((card.album_title, {"url": card.url, "filename": card.filename}))

        if not selected:
            self.statusLabel.setText(self.tr("No images selected"))
            return

        settings_widget = self.window().settingsInterface
        base_dir = settings_widget.base_dir
        workers = settings_widget.workers

        self.logEngine.clear()
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        self._set_ui_busy(True)
        self.statusLabel.setText(self.tr("Downloading..."))

        self._worker = DownloadWorker(selected, base_dir, workers, batch_name=self._batch_name)
        self._worker.log_signal.connect(self._append_engine_log)
        self._worker.status_signal.connect(lambda txt: self.statusLabel.setText(txt))
        self._worker.progress_signal.connect(self._on_progress)
        # self._worker.file_progress_signal.connect(...) # Can implement later for fine grained logs
        self._worker.finished_signal.connect(self._on_download_finished)
        self._worker.start()

    def _on_progress(self, done, total):
        if total <= 0:
            self.progressBar.setValue(0)
            return
        self.progressBar.setValue(int(done / total * 100))

    def _on_download_finished(self, summary):
        self.progressBar.setValue(100)
        self._set_ui_busy(False)
        self.btnDownload.setEnabled(True)
        self._worker = None
        self.statusLabel.setText(self.tr("Done"))

    def _on_stop(self):
        if self._worker:
            self._worker.stop()
            self.statusLabel.setText(self.tr("Stopping..."))

    def _append_engine_log(self, msg):
        self.logEngine.append(msg)

class DownloaderWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()

        self.downloaderInterface = DownloaderInterface(self)
        self.settingsInterface = SettingsInterface(self)

        self.initNavigation()
        self.initWindow()

    def initNavigation(self):
        self.addSubInterface(self.downloaderInterface, FIF.DOWNLOAD, "Downloader")
        self.addSubInterface(self.settingsInterface, FIF.SETTING, "Settings", NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(1100, 800)
        self.setMinimumWidth(800)
        self.setWindowTitle('JPG6 Downloader Pro')

        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)




class SpinBoxSettingCard(SettingCard):
    """ Custom setting card with a SpinBox """

    def __init__(self, icon, title, content=None, parent=None):
        super().__init__(icon, title, content, parent)
        self.spinBox = SpinBox(self)
        self.hBoxLayout.addWidget(self.spinBox, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

class SettingsInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingsInterface")
        self.scrollWidget = QWidget()
        self.expandLayout = QVBoxLayout(self.scrollWidget)

        # Settings variables
        self.settings = self._load_settings()
        self.lang = self.settings.get("lang", "ru")
        self.workers = int(self.settings.get("workers", 3))
        self.base_dir = self.settings.get("base_dir", os.path.join(SCRIPT_DIR, "downloads"))

        self.settingGroup = SettingCardGroup(self.tr("Settings"), self.scrollWidget)

        from qfluentwidgets import ComboBox
        self.langCard = SettingCard(
            FIF.LANGUAGE,
            self.tr("Language"),
            self.tr("Select application language"),
            parent=self.settingGroup
        )
        self.langComboBox = ComboBox(self.langCard)
        self.langComboBox.addItems(["Русский", "English"])
        self.langComboBox.setCurrentIndex(0 if self.lang == "ru" else 1)
        self.langComboBox.currentIndexChanged.connect(self._on_lang_changed)
        self.langCard.hBoxLayout.addWidget(self.langComboBox, 0, Qt.AlignRight)
        self.langCard.hBoxLayout.addSpacing(16)

        self.workersCard = SpinBoxSettingCard(
            icon=FIF.SPEED_OFF,
            title=self.tr("Workers"),
            content=self.tr("Number of simultaneous downloads (1-8)"),
            parent=self.settingGroup
        )
        self.workersCard.spinBox.setRange(1, 8)
        self.workersCard.spinBox.setValue(self.workers)
        self.workersCard.spinBox.valueChanged.connect(self._on_workers_changed)

        self.downloadFolderCard = PushSettingCard(
            self.tr("Pick Folder"),
            FIF.FOLDER,
            self.tr("Download folder"),
            self.base_dir,
            self.settingGroup
        )
        self.downloadFolderCard.clicked.connect(self._on_pick_folder)

        self.settingGroup.addSettingCard(self.langCard)
        self.settingGroup.addSettingCard(self.workersCard)
        self.settingGroup.addSettingCard(self.downloadFolderCard)

        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        self.expandLayout.addWidget(self.settingGroup)
        self.expandLayout.addStretch(1)

        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        # Make the background transparent
        self.setStyleSheet("ScrollArea, #scrollWidget { background-color: transparent; border: none; }")


    def _load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_settings(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        data = {
            "lang": self.lang,
            "workers": self.workers,
            "base_dir": self.base_dir
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        InfoBar.success(
            title=self.tr('Success'),
            content=self.tr("Settings saved successfully"),
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )

    def _on_lang_changed(self, index):
        self.lang = "ru" if index == 0 else "en"
        self._save_settings()

    def _on_workers_changed(self, value):
        self.workers = value
        self._save_settings()

    def _on_pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.tr("Select download folder"), self.base_dir)
        if folder:
            self.base_dir = folder
            self.downloadFolderCard.setContent(folder)
            self._save_settings()


def run_fluent():
    app = QApplication(sys.argv)
    w = DownloaderWindow()
    w.show()
    return app.exec()

if __name__ == '__main__':
    sys.exit(run_fluent())

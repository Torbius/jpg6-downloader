import sys
from PySide6.QtWidgets import QApplication
from fluent_frontend import DownloaderWindow

def test_init():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # Instantiate the window but don't call show() or exec()
    try:
        window = DownloaderWindow()
        print("GUI loaded successfully without crashing.")
    except Exception as e:
        print(f"Crash during initialization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_init()

import argparse


def run_ctk_ui():
    from ctk_frontend import run_ctk
    raise SystemExit(run_ctk())


def run_qt_ui():
    from qt_frontend import run_qt
    raise SystemExit(run_qt())


def main():
    parser = argparse.ArgumentParser(description="JPG6 Downloader")
    parser.add_argument(
        "--ui",
        default="ctk",
        choices=["ctk", "qt"],
        help="UI backend: ctk (CustomTkinter, default) or qt (PySide6 legacy)",
    )
    args = parser.parse_args()

    if args.ui == "qt":
        run_qt_ui()
    else:
        run_ctk_ui()


if __name__ == "__main__":
    main()

import argparse


def run_qt_ui():
    from qt_frontend import run_qt

    raise SystemExit(run_qt())


def main():
    parser = argparse.ArgumentParser(description="JPG6 Downloader launcher (Qt)")
    parser.add_argument("--ui", default="qt", help="Legacy flag; only 'qt' is supported")
    args = parser.parse_args()

    if (args.ui or "qt").lower() != "qt":
        print("Classic UI has been removed. Starting Qt UI instead.")

    run_qt_ui()


if __name__ == "__main__":
    main()

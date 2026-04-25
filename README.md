# JPG6 Downloader Pro

> 🇷🇺 [Русский](#-русский) · 🇬🇧 [English](#-english)

---

## 🇷🇺 Русский

### Описание

**JPG6 Downloader Pro** — настольное приложение для массового скачивания изображений с хостинга [jpg6.su](https://jpg6.su) и его зеркал. Поддерживает альбомы, профили пользователей, страницы отдельных изображений и прямые ссылки на файлы.

### Возможности

- Скачивание альбомов, профилей, страниц изображений и прямых ссылок
- Параллельная загрузка (настраиваемое количество потоков)
- Умный двухэтапный поиск изображений: oEmbed-first → HTML-парсинг → резервный oEmbed
- Дедупликация URL — одна ссылка обрабатывается только один раз
- Пропуск уже скачанных файлов (по имени файла)
- Логи движка, ошибок и отладки прямо в интерфейсе
- Импорт очереди из TXT-файла
- Современный Qt-интерфейс с тёмной темой
- Переключение языка интерфейса (RU / EN) без перезапуска
- Сохранение настроек между сессиями

### Требования

- Windows 10 / 11
- Python 3.10 или новее
- Интернет-соединение

### Установка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/Torbius/jpg6-downloader.git
cd jpg6-downloader

# 2. Создать виртуальное окружение
python -m venv .venv
.venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt
```

### Запуск

**Двойной клик:**
```
start_qt.bat
```

**Или через терминал:**
```bash
python main.py
```

### Интерфейс

| Элемент | Описание |
|---|---|
| Поле URL + Добавить | Вставить ссылку и добавить в очередь |
| Импорт URL из TXT | Загрузить список ссылок из текстового файла (по одной на строку) |
| Потоки | Количество одновременных загрузок (1–8, рекомендуется 3–6) |
| Папка загрузки | Куда сохранять файлы |
| Начать загрузку | Запустить обработку всей очереди |
| Стоп | Мягкая остановка (текущие файлы докачиваются) |
| Лог движка | Подробный ход выполнения в реальном времени |
| Ошибки | Содержимое `config/errors.log` |
| Отладка | Содержимое `config/debug.log` — детали поиска URL изображений |

### Поддерживаемые типы ссылок

| Тип | Пример |
|---|---|
| Альбом | `https://jpg6.su/a/albumname` |
| Альбом (полный путь) | `https://jpg6.su/album/albumname` |
| Профиль пользователя | `https://jpg6.su/username` |
| Все альбомы пользователя | `https://jpg6.su/username/albums` |
| Страница изображения | `https://jpg6.su/img/XXXXX` |
| Прямая ссылка на файл | `https://.../image.jpg` |

### Скрипт для форума

В папке `userscripts/` находится скрипт для Tampermonkey/Greasemonkey:  
`simp_forum_jpg6_extractor.user.js`

Скрипт добавляет кнопку на страницы форума и автоматически собирает все ссылки на jpg6 в удобный текстовый файл для импорта в программу.

### Структура проекта

```
jpg6-downloader/
├── backend.py          # Движок: скрапинг, загрузка, логи
├── qt_frontend.py      # Qt UI (RU/EN)
├── main.py             # Точка входа
├── requirements.txt    # Зависимости Python
├── start_qt.bat        # Быстрый запуск (Windows)
├── config/             # Настройки и логи
│   ├── settings.json
│   ├── errors.log
│   └── debug.log
├── downloads/          # Скачанные файлы (создаётся автоматически)
└── userscripts/        # Пользовательский скрипт для браузера
```

### Зависимости

```
requests
beautifulsoup4
PySide6
```

---

## 🇬🇧 English

### Description

**JPG6 Downloader Pro** is a desktop application for bulk downloading images from [jpg6.su](https://jpg6.su) and its mirrors. It supports albums, user profiles, individual image pages, and direct file links.

### Features

- Download albums, profiles, image pages, and direct links
- Parallel downloading (configurable thread count)
- Smart two-stage image resolution: oEmbed-first → HTML parsing → fallback oEmbed
- URL deduplication — each link is processed only once
- Skip already downloaded files (by filename)
- Engine, error, and debug logs directly in the UI
- Import queue from a TXT file
- Modern Qt UI with dark theme
- Language switching (RU / EN) without restart
- Persistent settings between sessions

### Requirements

- Windows 10 / 11
- Python 3.10 or newer
- Internet connection

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Torbius/jpg6-downloader.git
cd jpg6-downloader

# 2. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Running

**Double-click:**
```
start_qt.bat
```

**Or via terminal:**
```bash
python main.py
```

### Interface

| Element | Description |
|---|---|
| URL field + Add | Paste a link and add it to the queue |
| Import URLs from TXT | Load a list of links from a text file (one per line) |
| Workers | Number of simultaneous downloads (1–8, recommended 3–6) |
| Download folder | Where to save files |
| Start Download | Begin processing the entire queue |
| Stop | Graceful stop (current files finish downloading) |
| Engine log | Detailed real-time progress |
| Errors | Contents of `config/errors.log` |
| Debug | Contents of `config/debug.log` — image URL resolution details |

### Supported Link Types

| Type | Example |
|---|---|
| Album | `https://jpg6.su/a/albumname` |
| Album (full path) | `https://jpg6.su/album/albumname` |
| User profile | `https://jpg6.su/username` |
| All user albums | `https://jpg6.su/username/albums` |
| Image page | `https://jpg6.su/img/XXXXX` |
| Direct file link | `https://.../image.jpg` |

### Browser Userscript

The `userscripts/` folder contains a Tampermonkey/Greasemonkey script:  
`simp_forum_jpg6_extractor.user.js`

The script adds a button to forum pages and automatically collects all jpg6 links into a convenient text file ready for import into the application.

### Project Structure

```
jpg6-downloader/
├── backend.py          # Engine: scraping, downloading, logging
├── qt_frontend.py      # Qt UI (RU/EN)
├── main.py             # Entry point
├── requirements.txt    # Python dependencies
├── start_qt.bat        # Quick launch (Windows)
├── config/             # Settings and logs
│   ├── settings.json
│   ├── errors.log
│   └── debug.log
├── downloads/          # Downloaded files (created automatically)
└── userscripts/        # Browser userscript
```

### Dependencies

```
requests
beautifulsoup4
PySide6
```

### License

This project is licensed under the [MIT License](LICENSE).  
You are free to use, modify, and distribute it. No warranty is provided.

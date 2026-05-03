import hashlib
import json
import os
import re
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(SCRIPT_DIR, "config")
ERROR_LOG_FILE = os.path.join(CONFIG_DIR, "errors.log")
DEBUG_LOG_FILE = os.path.join(CONFIG_DIR, "debug.log")

JPG_MIRRORS = [
    r"jpg\d*\.su", r"jpg\d*\.church", r"jpg\d*\.fish",
    r"jpg\d*\.fishing", r"jpg\d*\.pet", r"jpg\d*\.cr",
    r"jpeg\d*\.pet", r"jpeg\d*\.su", r"jpeg\d*\.cr",
    r"selti-delivery\.ru",
]
_MIRROR_RE = re.compile(r"^https?://(?:www\.)?(" + "|".join(JPG_MIRRORS) + r")", re.IGNORECASE)

# Bunkr hosting — matches bunkr.<any tld>
_BUNKR_HOST_RE = re.compile(r"^bunkr\.[a-z]{2,10}$", re.IGNORECASE)


def is_bunkr_url(url):
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
        return bool(_BUNKR_HOST_RE.match(host))
    except Exception:
        return False


def is_bunkr_album(url):
    return is_bunkr_url(url) and urlparse(url).path.strip("/").startswith("a/")


def is_bunkr_file_page(url):
    return is_bunkr_url(url) and urlparse(url).path.strip("/").startswith("f/")

DEFAULT_WORKERS = 3
DOWNLOAD_DELAY = 0.05
MAX_RETRIES = 3
RETRY_DELAYS = [1.0, 3.0, 7.0]


def is_jpg_mirror(url):
    return bool(_MIRROR_RE.match(url))


def thumb_to_original(url):
    return url.replace(".th.", ".").replace(".md.", ".")


def original_to_thumb(url):
    """Return .th. thumbnail URL for a CDN image URL, or original if not applicable."""
    try:
        p = urlparse(url)
        base, ext = os.path.splitext(p.path)
        if ext.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif'):
            from urllib.parse import urlunparse
            new_path = f"{base}.th{ext}"
            return urlunparse(p._replace(path=new_path))
    except Exception:
        pass
    return url


def format_size(n: int) -> str:
    """Human-readable file size."""
    if n < 1024:
        return f"{n} B"
    if n < 1_048_576:
        return f"{n / 1024:.1f} KB"
    if n < 1_073_741_824:
        return f"{n / 1_048_576:.1f} MB"
    return f"{n / 1_073_741_824:.2f} GB"


def file_md5(path: str) -> str:
    """Return MD5 hex digest of a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _unique_filename(base_name: str, existing: set) -> str:
    """Return base_name, or base_name (N).ext if base_name is already taken."""
    if base_name not in existing:
        return base_name
    stem, ext = os.path.splitext(base_name)
    i = 1
    while True:
        candidate = f"{stem} ({i}){ext}"
        if candidate not in existing:
            return candidate
        i += 1


def sanitize_filename(name, fallback="image.jpg"):
    if not name:
        name = fallback
    name = os.path.basename(str(name).replace("\\", "/"))
    if not name:
        name = fallback
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = name.strip().strip(".")
    if not name:
        name = fallback
    if len(name) > 180:
        stem, ext = os.path.splitext(name)
        name = stem[:160] + ext[:20]
    return name


def sanitize_dirname(name, fallback="album"):
    if not name:
        name = fallback
    name = str(name).replace("\n", " ").replace("\r", " ").replace("\t", " ")
    name = re.sub(r"[\x00-\x1f]", " ", name)
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = re.sub(r"\s+", " ", name).strip().rstrip(" .")
    if not name:
        name = fallback
    if len(name) > 80:
        name = name[:80].rstrip(" .")
    if not name:
        name = fallback
    return name


def classify_url(url):
    p = urlparse(url)
    lower_path = p.path.lower()
    if re.search(r"\.(jpg|jpeg|png|webp|gif|bmp|avif|jfif)$", lower_path):
        return "direct_image"
    if is_bunkr_album(url):
        return "bunkr_album"
    if not is_jpg_mirror(url):
        return "unknown"
    path = p.path.strip("/")
    seg = path.split("/") if path else []
    if not seg:
        return "unknown"
    if seg[0] == "img":
        return "image_page"
    if seg[0] in ("a", "album"):
        return "album"
    if len(seg) == 2 and seg[1] == "albums":
        return "user_albums"
    if len(seg) == 1:
        return "user_profile"
    return "album"


def should_skip_batch_url(url):
    try:
        path = urlparse(url).path.lower()
    except Exception:
        return True
    if "favicon" in path:
        return True
    if "/data/avatars/" in path:
        return True
    if "/content/images/users/" in path:
        return True
    if "/content/images/system/" in path:
        return True
    return False


def filename_from_url(url, fallback="image.jpg"):
    name = os.path.basename(urlparse(url).path)
    if not name:
        name = fallback
    return sanitize_filename(name, fallback=fallback)


def is_content_image_url(url):
    try:
        p = urlparse(url)
    except Exception:
        return False
    host = p.netloc.lower()
    path = p.path.lower()
    if not re.search(r"\.(jpg|jpeg|png|webp|gif|bmp|avif|jfif)$", path):
        return False
    if should_skip_batch_url(url):
        return False
    if "/content/images/users/" in path:
        return False
    if "bncloudfl.com" in host:
        return False
    if "selti-delivery.ru" in host:
        return True
    if is_jpg_mirror(url):
        return True
    return False


def is_oembed_first_candidate(page_url):
    """Return True for /img short-code links where oEmbed is usually faster and sufficient."""
    try:
        p = urlparse(page_url)
        segs = p.path.strip("/").split("/")
        if len(segs) != 2 or segs[0] != "img":
            return False
        token = segs[1]
        if "." in token:
            return False
        return bool(re.fullmatch(r"[A-Za-z0-9_-]{5,16}", token))
    except Exception:
        return False


def _request_with_retry(session, url, max_retries=MAX_RETRIES, **kwargs):
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, **kwargs)
            if resp.status_code == 429:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                time.sleep(delay)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_exc = e
            if attempt < max_retries:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                time.sleep(delay)
    raise last_exc


class DownloadBackend:
    def __init__(
        self,
        base_dir=None,
        workers=DEFAULT_WORKERS,
        logger=None,
        status_cb=None,
        item_status_cb=None,
        progress_cb=None,
        image_downloaded_cb=None,
        file_progress_cb=None,
    ):
        self.base_dir = os.path.normpath(base_dir or os.path.join(SCRIPT_DIR, "downloads"))
        self.workers = int(max(1, workers))
        self.logger = logger or (lambda msg: None)
        self.status_cb = status_cb or (lambda msg: None)
        self.item_status_cb = item_status_cb or (lambda url, status: None)
        self.progress_cb = progress_cb or (lambda done, total: None)
        self.image_downloaded_cb = image_downloaded_cb or (lambda path: None)
        # file_progress_cb(filename, bytes_done, bytes_total)
        self.file_progress_cb = file_progress_cb or (lambda fn, done, total: None)
        self._cancel_event = threading.Event()
        self._lock = threading.Lock()
        self._batch_name = None

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

    def cancel(self):
        self._cancel_event.set()

    def is_cancelled(self):
        return self._cancel_event.is_set()

    def _log_exception(self, err, context="", extra=""):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            with self._lock:
                with open(ERROR_LOG_FILE, "a", encoding="utf-8") as fh:
                    line = f"[{ts}]"
                    if context:
                        line += f" {context}"
                    fh.write(line + "\n")
                    if extra:
                        fh.write(str(extra) + "\n")
                    fh.write(f"{type(err).__name__}: {err}\n")
                    fh.write(traceback.format_exc())
                    fh.write("\n" + "-" * 90 + "\n")
        except Exception:
            pass

    def _log_debug(self, context="", **fields):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            with self._lock:
                with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as fh:
                    line = f"[{ts}]"
                    if context:
                        line += f" {context}"
                    fh.write(line + "\n")
                    for k, v in fields.items():
                        fh.write(f"{k}: {v}\n")
                    fh.write("-" * 90 + "\n")
        except Exception:
            pass

    @staticmethod
    def _is_password_protected(html):
        soup = BeautifulSoup(html, "html.parser")
        return bool(
            soup.select_one('input[name="content-password"]') or
            soup.select_one('input[name="album-password"]') or
            soup.select_one('#form-album-password') or
            "This content is password protected" in html or
            "请输入您的密码以继续浏览" in html
        )

    @staticmethod
    def _extract_title(soup, fallback="album"):
        for sel in ["h1.album-name", ".album-title", "h1"]:
            el = soup.select_one(sel)
            if el:
                return el.get_text(strip=True)
        return fallback

    def _fetch_user_albums(self, albums_url):
        album_urls = []
        page_url = albums_url
        page_num = 1

        while page_url and not self.is_cancelled():
            self.logger(f"📄 Страница альбомов {page_num}...")
            try:
                resp = _request_with_retry(self.session, page_url, timeout=15)
            except Exception as e:
                self._log_exception(e, "_fetch_user_albums", f"page_url={page_url}")
                self.logger(f"❌ Ошибка загрузки списка альбомов: {e}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                full = urljoin(page_url, href)
                fp = urlparse(full).path.strip("/")
                segs = fp.split("/")
                if is_jpg_mirror(full) and len(segs) >= 2 and segs[0] not in ("img",):
                    if segs[0] in ("a", "album") or (len(segs) == 2 and segs[1] != "albums"):
                        if full not in album_urls:
                            album_urls.append(full)

            nxt = soup.select_one("li.pagination-next > a[href]") or soup.select_one('a[data-pagination="next"][href]')
            if nxt and nxt.get("href"):
                next_url = urljoin(page_url, nxt["href"])
                if next_url != page_url:
                    page_url = next_url
                    page_num += 1
                    time.sleep(DOWNLOAD_DELAY)
                    continue
            break

        self.logger(f"📊 Найдено {len(album_urls)} альбомов")
        return album_urls

    # ------------------------------------------------------------------
    # Bunkr support
    # ------------------------------------------------------------------

    def _resolve_bunkr_file_cdn_url(self, file_page_url):
        """Fetch a bunkr /f/<id> page and return the direct CDN image URL."""
        try:
            resp = _request_with_retry(self.session, file_page_url, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            # "Enlarge image" link → direct CDN (c1fr.scdn.st, c2fr.scdn.st, …)
            enlarge = soup.find("a", href=re.compile(r"https?://[a-z0-9]+\.scdn\.st/", re.I))
            if enlarge and enlarge.get("href") and "static.scdn.st" not in enlarge["href"]:
                return enlarge["href"]
            # Fallback: download button on get.bunkrr.su
            dl = soup.find("a", href=re.compile(r"https?://get\.bunkrr\.", re.I))
            if dl and dl.get("href"):
                return dl["href"]
        except Exception as e:
            self._log_exception(e, "_resolve_bunkr_file_cdn_url", f"url={file_page_url}")
        return None

    def _collect_bunkr_album(self, album_url):
        """Parse a bunkr album page; returns (album_title, images).
        Each image dict has url=file_page_url (resolved to CDN on download),
        thumb_url=static CDN thumbnail, filename from the page.
        Only image files are included (videos are skipped).
        """
        images = []
        p = urlparse(album_url)
        base_url = f"{p.scheme}://{p.netloc}"
        try:
            resp = _request_with_retry(self.session, album_url, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            title_el = soup.select_one("h1")
            album_title = title_el.get_text(strip=True) if title_el else "bunkr_album"

            for card in soup.select("div.theItem"):
                # Only download image files — skip video/pdf etc.
                type_span = card.select_one("span[class*='type-']")
                if type_span:
                    span_classes = " ".join(type_span.get("class", []))
                    if "type-Image" not in span_classes:
                        continue

                # Filename (visible label)
                name_el = card.select_one("p.theName")
                filename = name_el.get_text(strip=True) if name_el else ""
                if not filename:
                    hidden = card.find("p", style=re.compile(r"display\s*:\s*none", re.I))
                    filename = hidden.get_text(strip=True) if hidden else "image.jpg"
                filename = sanitize_filename(filename)

                # Thumbnail URL
                thumb_img = card.select_one("img.grid-images_box-img")
                thumb_url = thumb_img.get("src", "") if thumb_img else ""

                # File page link (/f/<id>)
                file_link = card.find("a", href=re.compile(r"^/f/"))
                if not file_link:
                    file_link = card.find("a", attrs={"aria-label": "download"})
                if not file_link or not file_link.get("href"):
                    continue

                file_page_url = urljoin(base_url, file_link["href"])
                images.append({
                    "url": file_page_url,   # resolved to CDN during download
                    "thumb_url": thumb_url,
                    "filename": filename,
                })

            self.logger(f"   → {len(images)} фото в альбоме Bunkr")
        except Exception as e:
            self._log_exception(e, "_collect_bunkr_album", f"url={album_url}")
            self.logger(f"❌ Ошибка загрузки альбома Bunkr: {e}")
            return "bunkr_album", []

        return album_title, images

    def _collect_album_images(self, album_url):
        images = []
        page_url = album_url
        page_num = 1
        seen_ids = set()

        while page_url and not self.is_cancelled():
            self.logger(f"📄 Стр. {page_num}...")
            try:
                resp = _request_with_retry(self.session, page_url, timeout=15)
            except Exception as e:
                self._log_exception(e, "_collect_album_images", f"page_url={page_url}")
                self.logger(f"❌ Ошибка загрузки страницы: {e}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            found = 0
            for item in soup.select(".list-item[data-object]"):
                data_id = item.get("data-id", "")
                if data_id in seen_ids:
                    continue
                seen_ids.add(data_id)
                try:
                    raw = unquote(item["data-object"])
                    obj = json.loads(raw)
                    img_url = obj.get("image", {}).get("url") if isinstance(obj.get("image"), dict) else None
                    if not img_url:
                        img_url = obj.get("url")
                    filename = obj.get("image", {}).get("filename") if isinstance(obj.get("image"), dict) else None
                    if not filename:
                        filename = obj.get("filename")
                    if img_url:
                        raw_url = str(img_url)
                        full_url = thumb_to_original(raw_url)
                        thumb_url = raw_url if ".th." in raw_url else original_to_thumb(full_url)
                        images.append({"url": full_url, "thumb_url": thumb_url, "filename": filename or f"{data_id}.jpg"})
                        found += 1
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

            self.logger(f"   → {found} фото")
            nxt = soup.select_one("li.pagination-next > a[href]") or soup.select_one('a[data-pagination="next"][href]')
            if nxt and nxt.get("href"):
                next_url = urljoin(page_url, nxt["href"])
                if next_url != page_url:
                    page_url = next_url
                    page_num += 1
                    time.sleep(DOWNLOAD_DELAY)
                    continue
            break

        return images

    def _collect_profile_images(self, profile_url):
        images = []
        page_url = profile_url
        page_num = 1
        seen_ids = set()

        while page_url and not self.is_cancelled():
            self.logger(f"📄 Профиль — стр. {page_num}...")
            try:
                resp = _request_with_retry(self.session, page_url, timeout=15)
            except Exception as e:
                self._log_exception(e, "_collect_profile_images", f"page_url={page_url}")
                self.logger(f"❌ Ошибка: {e}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            found = 0

            for item in soup.select(".list-item[data-object]"):
                data_id = item.get("data-id", "")
                if data_id in seen_ids:
                    continue
                seen_ids.add(data_id)
                try:
                    raw = unquote(item["data-object"])
                    obj = json.loads(raw)
                    img_url = obj.get("image", {}).get("url") if isinstance(obj.get("image"), dict) else None
                    if not img_url:
                        img_url = obj.get("url")
                    filename = obj.get("image", {}).get("filename") if isinstance(obj.get("image"), dict) else None
                    if not filename:
                        filename = obj.get("filename")
                    if img_url:
                        raw_url = str(img_url)
                        full_url = thumb_to_original(raw_url)
                        thumb_url = raw_url if ".th." in raw_url else original_to_thumb(full_url)
                        images.append({"url": full_url, "thumb_url": thumb_url, "filename": filename or f"{data_id}.jpg"})
                        found += 1
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

            self.logger(f"   → {found} фото")

            album_links_on_page = []
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                full = urljoin(page_url, href)
                if is_jpg_mirror(full):
                    fp = urlparse(full).path.strip("/")
                    segs = fp.split("/")
                    if len(segs) >= 2 and segs[0] in ("a", "album") and full not in album_links_on_page:
                        album_links_on_page.append(full)

            if not found and album_links_on_page:
                self.logger(f"   → Найдено {len(album_links_on_page)} ссылок на альбомы, собираю из них...")
                for aurl in album_links_on_page:
                    if self.is_cancelled():
                        break
                    time.sleep(DOWNLOAD_DELAY)
                    images.extend(self._collect_album_images(aurl))

            nxt = soup.select_one("li.pagination-next > a[href]") or soup.select_one('a[data-pagination="next"][href]')
            if nxt and nxt.get("href"):
                next_url = urljoin(page_url, nxt["href"])
                if next_url != page_url:
                    page_url = next_url
                    page_num += 1
                    time.sleep(DOWNLOAD_DELAY)
                    continue
            break

        return images

    def _collect_single_image_page(self, page_url):
        images = []
        html_candidate_total = 0
        html_valid_total = 0
        oembed_candidate_total = 0
        oembed_valid_total = 0
        oembed_url = ""
        strategy = "html_then_oembed"
        tried_oembed_urls = set()

        def _fetch_from_oembed(target_url):
            nonlocal oembed_url, oembed_candidate_total, oembed_valid_total
            if not target_url or target_url in tried_oembed_urls:
                return []
            tried_oembed_urls.add(target_url)
            # Use the target URL's own host for oEmbed (mirrors have their own endpoint)
            parsed_target = urlparse(target_url)
            oembed_base = f"{parsed_target.scheme}://{parsed_target.netloc}/oembed/"
            query_url = oembed_base + "?url=" + requests.utils.quote(target_url, safe="") + "&format=json"
            try:
                oembed_resp = _request_with_retry(self.session, query_url, timeout=15)
                data = oembed_resp.json()
                oembed_candidates = [data.get("url"), data.get("thumbnail_url")]
                oembed_url = query_url
                oembed_candidate_total += len([x for x in oembed_candidates if x])

                thumb_raw = data.get("thumbnail_url", "")
                found = []
                seen_oembed = set()
                for raw in oembed_candidates:
                    if not raw:
                        continue
                    full = thumb_to_original(str(raw))
                    if full in seen_oembed:
                        continue
                    seen_oembed.add(full)
                    if is_content_image_url(full):
                        thumb_url = str(thumb_raw) if thumb_raw else original_to_thumb(full)
                        found.append({"url": full, "thumb_url": thumb_url, "filename": filename_from_url(full)})
                        oembed_valid_total += 1
                return found
            except Exception:
                return []

        # Smart path: for short /img links, oEmbed often resolves directly.
        # If it fails, we still do full HTML parsing + extra oEmbed fallback.
        if is_oembed_first_candidate(page_url):
            strategy = "oembed_first"
            images = _fetch_from_oembed(page_url)
            if images:
                chosen = images[0]["url"] if images else ""
                self._log_debug(
                    "image_page_resolve",
                    strategy="oembed_first_hit",
                    page_url=page_url,
                    html_candidate_total=html_candidate_total,
                    html_valid_total=html_valid_total,
                    oembed_url=oembed_url,
                    oembed_candidate_total=oembed_candidate_total,
                    oembed_valid_total=oembed_valid_total,
                    found_total=len(images),
                    chosen=chosen,
                )
                return images

        try:
            resp = _request_with_retry(self.session, page_url, timeout=15)
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            candidates = []
            candidates.extend(re.findall(r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp|gif|bmp|avif|jfif)', html, re.IGNORECASE))
            og = soup.select_one('meta[property="og:image"][content]')
            if og:
                candidates.append(og.get("content", ""))
            tw = soup.select_one('meta[name="twitter:image"][content]')
            if tw:
                candidates.append(tw.get("content", ""))

            for sel in [".image-container img[src]", ".image-content img[src]", "img.main-image[src]", "img[src]"]:
                for img in soup.select(sel):
                    src = img.get("src", "")
                    if src:
                        candidates.append(src)

            script_text = "\n".join(s.get_text(" ", strip=True) for s in soup.select("script"))
            candidates.extend(re.findall(r'https?://[^\s"\'<>]+', script_text))
            html_candidate_total = len(candidates)

            seen = set()
            for raw in candidates:
                full = thumb_to_original(urljoin(page_url, raw))
                if full in seen:
                    continue
                seen.add(full)
                if is_content_image_url(full):
                    images.append({"url": full, "filename": filename_from_url(full)})
                    html_valid_total += 1

            if not images and classify_url(page_url) == "direct_image":
                images.append({"url": page_url, "filename": filename_from_url(page_url)})

            if not images:
                canonical_page = page_url
                og_url = soup.select_one('meta[property="og:url"][content]')
                if og_url and og_url.get("content"):
                    canonical_page = og_url.get("content")

                for candidate in (canonical_page, page_url):
                    extra = _fetch_from_oembed(candidate)
                    if extra:
                        images.extend(extra)
                        break
        except Exception as e:
            self._log_exception(e, "_collect_single_image_page", f"page_url={page_url}")

        chosen = images[0]["url"] if images else ""
        self._log_debug(
            "image_page_resolve",
            strategy=strategy,
            page_url=page_url,
            html_candidate_total=html_candidate_total,
            html_valid_total=html_valid_total,
            oembed_url=oembed_url,
            oembed_candidate_total=oembed_candidate_total,
            oembed_valid_total=oembed_valid_total,
            found_total=len(images),
            chosen=chosen,
        )
        return images

    def _download_images(self, images, album_title, global_offset=0, global_total=None):
        safe_title = sanitize_dirname(album_title, fallback="album")
        save_dir = os.path.join(self.base_dir, safe_title)

        try:
            os.makedirs(save_dir, exist_ok=True)
            if not os.path.isdir(save_dir):
                raise FileNotFoundError(f"Directory was not created: {save_dir}")
        except Exception as e:
            fallback_dir = os.path.join(self.base_dir, f"album_{int(time.time())}")
            self._log_exception(e, "_download_images:mkdir", f"attempted={save_dir}; fallback={fallback_dir}")
            os.makedirs(fallback_dir, exist_ok=True)
            save_dir = fallback_dir
            self.logger(f"⚠ Папка альбома проблемная, использую: {os.path.basename(save_dir)}")

        self.logger(f"📁 {save_dir}")

        try:
            existing = set(os.listdir(save_dir))
        except Exception as e:
            self._log_exception(e, "_download_images:listdir", f"save_dir={save_dir}")
            existing = set()

        # Build hash index of already-downloaded files for content-based dedup
        existing_hashes: dict[str, str] = {}  # md5 hex → filename
        for _name in list(existing):
            _fpath = os.path.join(save_dir, _name)
            try:
                existing_hashes[file_md5(_fpath)] = _name
            except Exception:
                pass

        total = len(images)
        effective_total = global_total if global_total is not None else total
        if total == 0:
            return {"downloaded": 0, "skipped": 0, "errors": 0, "total_bytes": 0}

        self.logger(f"🔗 {total} фото. Скачиваю...")

        downloaded = 0
        skipped = 0
        errors = 0
        completed = 0
        total_bytes = 0

        def _download_one(idx_img):
            nonlocal downloaded, skipped, errors, completed, total_bytes
            idx, img = idx_img
            if self.is_cancelled():
                return

            img_url = thumb_to_original(img["url"])

            # Resolve bunkr /f/<id> page → direct CDN image URL
            if is_bunkr_file_page(img_url):
                resolved = self._resolve_bunkr_file_cdn_url(img_url)
                if resolved:
                    img_url = resolved
                else:
                    self.logger(f"❌ [{idx}/{total}] Не удалось получить CDN URL: {img_url}")
                    with self._lock:
                        errors += 1
                        completed += 1
                        self.progress_cb(global_offset + completed, effective_total)
                    return

            fallback_name = os.path.basename(urlparse(img_url).path) or f"image_{idx}.jpg"
            filename = sanitize_filename(img.get("filename") or fallback_name, fallback=f"image_{idx}.jpg")

            time.sleep(DOWNLOAD_DELAY)
            last_err = None
            for attempt in range(MAX_RETRIES + 1):
                if self.is_cancelled():
                    return
                try:
                    req_headers = {}
                    if "scdn.st" in img_url:
                        req_headers["Referer"] = "https://bunkr.cr/"
                    r = self.session.get(img_url, headers=req_headers, timeout=60, stream=True)
                    if r.status_code == 429:
                        delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                        time.sleep(delay)
                        continue
                    r.raise_for_status()

                    content_length = int(r.headers.get("Content-Length", 0) or 0)
                    self.file_progress_cb(filename, 0, content_length)

                    # Download to a temp file; compute MD5 inline
                    filepath_tmp = os.path.join(save_dir, f"{filename}.{idx}.tmp")
                    bytes_written = 0
                    last_cb_time = 0.0
                    h = hashlib.md5()
                    with open(filepath_tmp, "wb") as f:
                        for chunk in r.iter_content(65536):
                            if self.is_cancelled():
                                break
                            f.write(chunk)
                            h.update(chunk)
                            bytes_written += len(chunk)
                            if content_length > 0:
                                now = time.monotonic()
                                if now - last_cb_time >= 0.12:
                                    self.file_progress_cb(filename, bytes_written, content_length)
                                    last_cb_time = now

                    if self.is_cancelled():
                        try:
                            os.remove(filepath_tmp)
                        except OSError:
                            pass
                        return

                    file_hash = h.hexdigest()
                    size_str = format_size(bytes_written)
                    final_filename = None
                    filepath = None

                    with self._lock:
                        if file_hash in existing_hashes:
                            # Identical content already on disk — true duplicate, skip
                            skipped += 1
                            completed += 1
                            self.progress_cb(global_offset + completed, effective_total)
                        else:
                            # New content: resolve name (handle collision by appending (N))
                            final_filename = _unique_filename(filename, existing)
                            filepath = os.path.join(save_dir, final_filename)
                            os.rename(filepath_tmp, filepath)
                            downloaded += 1
                            completed += 1
                            total_bytes += bytes_written
                            existing.add(final_filename)
                            existing_hashes[file_hash] = final_filename
                            self.progress_cb(global_offset + completed, effective_total)

                    if final_filename is None:
                        # Was a duplicate — delete temp
                        try:
                            os.remove(filepath_tmp)
                        except OSError:
                            pass
                        self.logger(f"⏭ [{idx}/{total}] {filename}  (уже скачан)")
                    else:
                        if final_filename != filename:
                            self.logger(f"✅ [{idx}/{total}] {filename} → {final_filename}  •  {size_str}")
                        else:
                            self.logger(f"✅ [{idx}/{total}] {final_filename}  •  {size_str}")
                        self.image_downloaded_cb(filepath)
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    try:
                        os.remove(os.path.join(save_dir, f"{filename}.{idx}.tmp"))
                    except OSError:
                        pass
                    if attempt < MAX_RETRIES:
                        delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                        time.sleep(delay)

            if last_err:
                self._log_exception(last_err, "_download_images:_download_one", f"url={img_url}; filename={filename}")
                with self._lock:
                    errors += 1
                    completed += 1
                    self.progress_cb(global_offset + completed, effective_total)
                self.logger(f"❌ [{idx}/{total}] {last_err}")

        # Use 1 worker for bunkr (each file needs a pre-fetch of the /f/ page)
        bunkr_mode = bool(images and is_bunkr_file_page(images[0].get("url", "")))
        effective_workers = 1 if bunkr_mode else self.workers
        with ThreadPoolExecutor(max_workers=effective_workers) as pool:
            futures = [pool.submit(_download_one, (i, img)) for i, img in enumerate(images, 1)]
            for future in as_completed(futures):
                if self.is_cancelled():
                    pool.shutdown(wait=False, cancel_futures=True)
                    break
                try:
                    future.result()
                except Exception as e:
                    self._log_exception(e, "_download_images:future")

        return {"downloaded": downloaded, "skipped": skipped, "errors": errors, "total_bytes": total_bytes}

    def _resolve_images_for_url(self, url):
        url_type = classify_url(url)

        if url_type == "bunkr_album":
            title, images = self._collect_bunkr_album(url)
            return title, images

        if url_type == "direct_image":
            folder = self._batch_name or "direct_images"
            return folder, [{"url": url, "filename": filename_from_url(url)}]

        if url_type == "image_page":
            imgs = self._collect_single_image_page(url)
            self._log_debug("batch_image_page_result", page_url=url, found_total=len(imgs), first=(imgs[0]["url"] if imgs else ""))
            folder = self._batch_name or "image_pages"
            return folder, imgs

        if url_type == "user_profile":
            images = self._collect_profile_images(url)
            username = urlparse(url).path.strip("/").split("/")[0] or "profile"
            return username, images

        if url_type == "user_albums":
            all_images = []
            subs = self._fetch_user_albums(url)
            for su in subs:
                if self.is_cancelled():
                    break
                st, imgs = self._resolve_images_for_url(su)
                if imgs:
                    all_images.extend(imgs)
            return "user_albums", all_images

        # Album-like page
        try:
            resp = _request_with_retry(self.session, url, timeout=15)
            final_url = resp.url.split("?")[0].rstrip("/")
            html = resp.text
            if self._is_password_protected(html):
                self.logger("🔒 Защищён паролем, пропускаю")
                return "protected", []
            soup = BeautifulSoup(html, "html.parser")
            title = self._extract_title(soup, fallback="album")
            images = self._collect_album_images(final_url)
            return title, images
        except Exception as e:
            self._log_exception(e, "_resolve_images_for_url", f"url={url}")
            self.logger(f"❌ Ошибка: {e}")
            return "error", []

    def scan_for_preview(self, urls, batch_name=None, image_found_cb=None):
        """Resolve all URLs to image lists WITHOUT downloading.
        Calls image_found_cb(album_title, img_dict) for each resolved image.
        Returns list of (album_title, images).
        """
        if image_found_cb is None:
            image_found_cb = lambda title, img: None

        self._batch_name = sanitize_dirname(batch_name) if batch_name else None

        seen_urls = set()
        clean_urls = []
        for raw in urls:
            if not raw:
                continue
            u = raw.strip()
            if not u or not u.startswith("http") or should_skip_batch_url(u):
                continue
            if u in seen_urls:
                continue
            seen_urls.add(u)
            clean_urls.append(u)

        total = len(clean_urls)
        if total == 0:
            self.status_cb("Нет валидных URL")
            return []

        results = []
        for i, url in enumerate(clean_urls, 1):
            if self.is_cancelled():
                break
            self.status_cb(f"Сканирую {i}/{total}…")
            self.logger(f"🔍 [{i}/{total}] {url}")
            try:
                album_title, images = self._resolve_images_for_url(url)
                results.append((album_title, images))
                for img in images:
                    if self.is_cancelled():
                        break
                    image_found_cb(album_title, img)
            except Exception as e:
                self._log_exception(e, "scan_for_preview", f"url={url}")
                self.logger(f"❌ Ошибка при сканировании: {e}")

        total_found = sum(len(imgs) for _, imgs in results)
        self.status_cb(f"Сканирование завершено: {total_found} изображений")
        return results

    def download_selected(self, selected):
        """Download from a list of (album_title, img_dict) pairs.
        Groups by album_title for folder organisation.
        """
        from collections import defaultdict
        grouped = defaultdict(list)
        order = []
        for album_title, img in selected:
            if album_title not in grouped:
                order.append(album_title)
            grouped[album_title].append(img)

        global_total = len(selected)
        global_offset = 0
        total_downloaded = 0
        total_skipped = 0
        total_errors = 0
        total_bytes_all = 0

        for album_title in order:
            images = grouped[album_title]
            if self.is_cancelled():
                self.logger("⛔ Остановлено")
                break
            self.logger(f"\n{'=' * 50}")
            self.logger(f"📁 {album_title} — {len(images)} фото")
            stats = self._download_images(
                images, album_title,
                global_offset=global_offset,
                global_total=global_total,
            )
            global_offset += len(images)
            total_downloaded += stats["downloaded"]
            total_skipped += stats["skipped"]
            total_errors += stats["errors"]
            total_bytes_all += stats.get("total_bytes", 0)

        summary = {
            "albums": len(order),
            "downloaded": total_downloaded,
            "skipped": total_skipped,
            "errors": total_errors,
            "total_bytes": total_bytes_all,
            "cancelled": self.is_cancelled(),
        }
        self.status_cb("Finished" if not self.is_cancelled() else "Cancelled")
        size_str = format_size(total_bytes_all) if total_bytes_all > 0 else ""
        size_part = f"  ({size_str})" if size_str else ""
        self.logger(
            f"🎉 Готово! Альбомов: {summary['albums']}, скачано: {summary['downloaded']}{size_part}, "
            f"пропущено: {summary['skipped']}, ошибок: {summary['errors']}"
        )
        return summary

    def run_batch(self, urls, batch_name=None):
        self._batch_name = sanitize_dirname(batch_name) if batch_name else None
        clean_urls = []
        seen_urls = set()
        for raw in urls:
            if not raw:
                continue
            u = raw.strip()
            if not u or not u.startswith("http") or should_skip_batch_url(u):
                continue
            if u in seen_urls:
                continue
            seen_urls.add(u)
            clean_urls.append(u)
        total = len(clean_urls)

        if total == 0:
            self.status_cb("No valid URLs")
            return {"albums": 0, "downloaded": 0, "skipped": 0, "errors": 0}

        self.status_cb(f"Анализ {total} URL...")
        total_downloaded = 0
        total_skipped = 0
        total_errors = 0

        # Phase 1: Resolve all URLs → collect (url, title, images)
        resolved = []
        for i, url in enumerate(clean_urls, 1):
            if self.is_cancelled():
                self.logger("⛔ Остановлено")
                break

            self.item_status_cb(url, "analyzing")
            self.logger(f"\n{'=' * 50}")
            self.logger(f"📦 URL {i}/{total}")
            self.logger(f"🔗 {url}")

            album_title, images = self._resolve_images_for_url(url)
            resolved.append((url, album_title, images))
            if not images:
                self.item_status_cb(url, "empty")
                self.logger("⚠ Нет изображений, пропускаю")

        # Phase 2: Download with true global progress
        if not self.is_cancelled():
            global_total = sum(len(imgs) for _, _, imgs in resolved)
            global_offset = 0
            for url, album_title, images in resolved:
                if self.is_cancelled():
                    self.logger("⛔ Остановлено")
                    break
                if not images:
                    continue
                self.item_status_cb(url, "downloading")
                stats = self._download_images(
                    images, album_title,
                    global_offset=global_offset,
                    global_total=global_total,
                )
                global_offset += len(images)
                total_downloaded += stats["downloaded"]
                total_skipped += stats["skipped"]
                total_errors += stats["errors"]
                self.item_status_cb(url, "done")

        summary = {
            "albums": total,
            "downloaded": total_downloaded,
            "skipped": total_skipped,
            "errors": total_errors,
            "cancelled": self.is_cancelled(),
        }
        self.status_cb("Finished" if not self.is_cancelled() else "Cancelled")
        self.logger(
            f"🎉 Готово! Альбомов: {summary['albums']}, скачано: {summary['downloaded']}, "
            f"пропущено: {summary['skipped']}, ошибок: {summary['errors']}"
        )
        return summary

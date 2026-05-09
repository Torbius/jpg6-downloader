// ==UserScript==
// @name         Simp Forum JPG6 Extractor
// @namespace    https://local.jpg6.downloader
// @version      0.4.0
// @description  Собирает JPG6 и Bunkr ссылки из темы форума и экспортирует в TXT.
// @author       local
// @run-at       document-end
// @noframes
// @grant        none
// @match        *://simptown.su/*
// @match        *://*.simptown.su/*
// @match        *://simpcity.su/*
// @match        *://*.simpcity.su/*
// @match        *://simpcity.cr/*
// @match        *://*.simpcity.cr/*
// @match        *://simpcity.is/*
// @match        *://*.simpcity.is/*
// @match        *://simpcity.to/*
// @match        *://*.simpcity.to/*
// @match        *://simpcity.ph/*
// @match        *://*.simpcity.ph/*
// @match        *://simpcity.net/*
// @match        *://*.simpcity.net/*
// @include      /^https?:\/\/([^/]+\.)?(simptown|simpcity)\.[^/]+\/.*/
// ==/UserScript==

(function () {
  'use strict';

  const HOST_RE = /(^|\.)simp(town|city)\.[a-z0-9.-]+$/i;
  const JPG_HOST_RE = /(^|\.)(jpg\d*\.(su|church|fish|fishing|pet|cr)|jpeg\d*\.(su|pet|cr)|selti-delivery\.ru)$/i;
  const BUNKR_HOST_RE = /^(bunkrr?)\.[a-z]{2,10}$/i;
  const URL_TEXT_RE = /https?:\/\/[^\s"'<>`]+/gi;
  const URL_IN_HTML_RE = /https?:\\?\/\\?\/[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+/gi;
  const POST_ROOT_SELECTOR = [
    'article.message',
    '.message-inner',
    '.message-content',
    '.message-body',
    '.bbWrapper',
    '.post',
    '.postbody',
    '.content',
  ].join(',');
  const NOISE_SELECTOR = [
    '.signature',
    '.message-signature',
    '.message-attribution',
    '.message-footer',
    '.p-footer',
    '.p-header',
    '.breadcrumb',
    '.shareButtons',
    '.advertisement',
    '.ad',
    '.ads',
    '.adblock',
    '.banner',
    '#banner',
    '[id*="banner"]',
    '[class*="banner"]',
    '[id*="ad-"]',
    '[class*="ad-"]',
    '[class*=" ad "]',
    '[class*="sponsor"]',
    '[class*="promo"]',
    'aside',
    'nav',
  ].join(',');

  if (!HOST_RE.test(location.hostname)) {
    return;
  }

  const state = {
    imgPageLinks: new Set(),   // /img/TOKEN — jpg mirrors
    albumLinks:   new Set(),   // album / profile links
    directImages: new Set(),   // raw CDN image URLs
    bunkrLinks:   new Set(),   // bunkr album + /f/ file links
    _seenCdnKeys: new Set(),   // cross-post CDN filename dedup
    running: false,
  };

  // All links union for export
  function allLinks() {
    return [
      ...state.imgPageLinks,
      ...state.albumLinks,
      ...state.directImages,
      ...state.bunkrLinks,
    ];
  }

  function toAbsoluteUrl(raw, baseUrl) {
    if (!raw || typeof raw !== 'string') return null;
    const cleaned = raw.trim()
      .replace(/^\((.*)\)$/, '$1')
      .replace(/[),.;]+$/, '')
      .replace(/\\\//g, '/')
      .replace(/&amp;/g, '&');

    if (!cleaned) return null;

    try {
      return new URL(cleaned, baseUrl).href;
    } catch {
      return null;
    }
  }

  function isJpgMirror(urlString) {
    try {
      const u = new URL(urlString);
      return JPG_HOST_RE.test(u.hostname);
    } catch {
      return false;
    }
  }

  function decodeMaybeUrl(raw) {
    if (!raw || typeof raw !== 'string') return raw;
    let v = raw.trim().replace(/\\\//g, '/').replace(/&amp;/g, '&');
    for (let i = 0; i < 2; i += 1) {
      try {
        const decoded = decodeURIComponent(v);
        if (decoded === v) break;
        v = decoded;
      } catch {
        break;
      }
    }
    return v;
  }

  function unwrapForumRedirect(urlString, baseUrl) {
    try {
      const u = new URL(urlString, baseUrl);
      const sameForumHost = HOST_RE.test(u.hostname);
      if (!sameForumHost) {
        return u.href;
      }

      const paramNames = ['url', 'u', 'target', 'to', 'link', 'redirect', 'r'];
      for (const p of paramNames) {
        const raw = u.searchParams.get(p);
        if (!raw) continue;
        const cand = decodeMaybeUrl(raw);
        try {
          const nested = new URL(cand, baseUrl).href;
          if (isJpgMirror(nested)) return nested;
        } catch {
          // ignore malformed nested url
        }
      }

      const m = u.href.match(/https?:%2F%2F[^\s&]+/i);
      if (m) {
        const nested = decodeMaybeUrl(m[0]);
        if (isJpgMirror(nested)) return nested;
      }

      return u.href;
    } catch {
      return urlString;
    }
  }

  function normalizeJpgUrl(urlString) {
    try {
      const u = new URL(urlString);
      u.pathname = u.pathname.replace('.th.', '.').replace('.md.', '.');

      if (u.searchParams.has('download')) {
        u.searchParams.delete('download');
      }

      if (!u.searchParams.toString()) {
        u.search = '';
      }
      return u.toString();
    } catch {
      return urlString;
    }
  }

  // Classify a jpg-mirror URL into one of three categories:
  // 'img_page'        — /img/TOKEN  (resolves to a single image via oEmbed)
  // 'direct_image'    — direct CDN file URL (.jpg/.png/etc.)
  // 'album_or_profile'— album, user profile, all-albums page
  // null              — not a jpg-mirror URL
  function classifyJpgLink(urlString) {
    if (!isJpgMirror(urlString)) return null;
    try {
      const u = new URL(urlString);
      if (/\.(jpg|jpeg|png|webp|gif|bmp|avif|jfif)(\?|$)/i.test(u.pathname)) {
        return 'direct_image';
      }
      const segs = u.pathname.split('/').filter(Boolean);
      if (segs.length >= 1 && segs[0] === 'img') return 'img_page';
      return 'album_or_profile';
    } catch {
      return null;
    }
  }

  function isBunkrHost(urlString) {
    try { return BUNKR_HOST_RE.test(new URL(urlString).hostname); } catch { return false; }
  }

  // 'bunkr_album' — /a/ID or /album/ID
  // 'bunkr_file'  — /f/ID (single file page, resolved to CDN on download)
  // null          — not a recognised bunkr link
  function classifyBunkrLink(urlString) {
    if (!isBunkrHost(urlString)) return null;
    try {
      const segs = new URL(urlString).pathname.split('/').filter(Boolean);
      if (!segs.length) return null;
      if (segs[0] === 'f') return 'bunkr_file';
      if (segs[0] === 'a' || segs[0] === 'album') return 'bunkr_album';
      return null;
    } catch { return null; }
  }

  // Canonical key for cross-post CDN dedup: strips numeric CDN subdomain
  // so img3.jpg6.su/x.jpg and img7.jpg6.su/x.jpg are treated as the same file.
  function cdnKey(urlString) {
    try {
      const u = new URL(urlString);
      const host = u.hostname.replace(/^[a-z]+\d+\./, '');
      const path = u.pathname.replace(/\.th\./, '.').replace(/\.md\./, '.');
      return `${host}${path}`;
    } catch { return urlString; }
  }

  function getScanRoots(doc) {
    const roots = Array.from(doc.querySelectorAll(POST_ROOT_SELECTOR))
      .filter((el) => !el.closest(NOISE_SELECTOR));

    if (roots.length > 0) {
      return roots;
    }

    if (doc.body) {
      return [doc.body];
    }

    return [doc.documentElement];
  }

  function shouldSkipElement(el) {
    return Boolean(el.closest(NOISE_SELECTOR));
  }

  function collectCandidatesFromDocument(doc, baseUrl) {
    const roots = getScanRoots(doc);
    let added = 0;

    function addGlobal(norm, kind) {
      if (kind === 'img_page') {
        if (!state.imgPageLinks.has(norm)) { state.imgPageLinks.add(norm); added++; }
      } else if (kind === 'album_or_profile') {
        if (!state.albumLinks.has(norm)) { state.albumLinks.add(norm); added++; }
      } else if (kind === 'direct_image') {
        // Cross-post CDN dedup: same file on different CDN mirrors → skip
        const key = cdnKey(norm);
        if (!state._seenCdnKeys.has(key)) {
          state._seenCdnKeys.add(key);
          state.directImages.add(norm);
          added++;
        }
      } else if (kind === 'bunkr_album' || kind === 'bunkr_file') {
        if (!state.bunkrLinks.has(norm)) { state.bunkrLinks.add(norm); added++; }
      }
    }

    for (const root of roots) {
      const imgPageLinks  = new Set();
      const albumLinks    = new Set();
      const directCdnLinks = new Set();
      const bunkrPostLinks = [];  // [{url, kind}]

      function processRaw(raw) {
        if (!raw || typeof raw !== 'string') return;
        const abs = toAbsoluteUrl(raw.trim(), baseUrl);
        if (!abs) return;
        const unwrapped = unwrapForumRedirect(abs, baseUrl);

        // Bunkr check first (before jpg-mirror normalisation)
        const bunkrKind = classifyBunkrLink(unwrapped);
        if (bunkrKind) { bunkrPostLinks.push({ url: unwrapped, kind: bunkrKind }); return; }

        const norm = normalizeJpgUrl(unwrapped);
        const kind = classifyJpgLink(norm);
        if (kind === 'img_page') imgPageLinks.add(norm);
        else if (kind === 'direct_image') directCdnLinks.add(norm);
        else if (kind === 'album_or_profile') albumLinks.add(norm);
      }

      // DOM attribute scan
      const attrMap = [
        ['a[href]', 'href'],
        ['img[src]', 'src'],
        ['img[data-src]', 'data-src'],
        ['img[data-url]', 'data-url'],
        ['img[data-full]', 'data-full'],
        ['*[data-href]', 'data-href'],
        ['*[data-url]', 'data-url'],
      ];
      for (const [selector, attr] of attrMap) {
        for (const el of root.querySelectorAll(selector)) {
          if (shouldSkipElement(el)) continue;
          const val = el.getAttribute(attr);
          if (val) processRaw(val);
        }
      }
      for (const el of root.querySelectorAll('source[srcset]')) {
        if (shouldSkipElement(el)) continue;
        const first = (el.getAttribute('srcset') || '').split(',')[0]?.trim().split(/\s+/)[0];
        if (first) processRaw(first);
      }

      // Text and innerHTML scan
      for (const m of ((root.innerText || '').match(URL_TEXT_RE) || [])) processRaw(m);
      for (const m of ((root.innerHTML || '').match(URL_IN_HTML_RE) || [])) processRaw(decodeMaybeUrl(m));

      // Flush per-post to global state
      for (const l of albumLinks) addGlobal(l, 'album_or_profile');
      for (const l of imgPageLinks) addGlobal(l, 'img_page');
      // If post has /img/ links, skip its raw CDN links (same images, duplicate embeds)
      if (imgPageLinks.size === 0) {
        for (const l of directCdnLinks) addGlobal(l, 'direct_image');
      }
      for (const { url, kind } of bunkrPostLinks) addGlobal(url, kind);
    }

    // Script tags: only /img/, album, bunkr — skip bare CDN URLs
    for (const scriptEl of doc.querySelectorAll('script')) {
      const s = scriptEl.textContent || '';
      for (const m of (s.match(URL_IN_HTML_RE) || [])) {
        const abs = toAbsoluteUrl(decodeMaybeUrl(m), baseUrl);
        if (!abs) continue;
        const unwrapped = unwrapForumRedirect(abs, baseUrl);
        const bunkrKind = classifyBunkrLink(unwrapped);
        if (bunkrKind) { addGlobal(unwrapped, bunkrKind); continue; }
        const norm = normalizeJpgUrl(unwrapped);
        const kind = classifyJpgLink(norm);
        if (kind === 'img_page' || kind === 'album_or_profile') addGlobal(norm, kind);
      }
    }

    return added;
  }

  function threadKey(urlString) {
    const u = new URL(urlString, location.href);
    const path = u.pathname
      .replace(/\/page-\d+\/?$/i, '/')
      .replace(/\/$/, '');
    return `${u.origin}${path}`;
  }

  function getThreadPageUrlsFromDocument(doc, currentUrl) {
    const baseOrigin = new URL(currentUrl).origin;
    const baseKey = threadKey(currentUrl);
    let maxPage = 1;
    let pathPattern = null; // 'path' (/page-N) or 'query' (?page=N)
    let basePath = '';

    // Scan all <a> links to find the maximum page number and detect URL pattern.
    // XenForo shows smart pagination (e.g. 1 … 60 61 [62] 63 64 … 100),
    // so we find maxPage and then generate ALL page URLs from 1 to maxPage.
    for (const a of doc.querySelectorAll('a[href]')) {
      const href = a.getAttribute('href');
      const full = toAbsoluteUrl(href, currentUrl);
      if (!full) continue;

      try {
        const u = new URL(full);
        if (u.origin !== baseOrigin) continue;
        if (threadKey(full) !== baseKey) continue;

        const pageNum = pageNumber(full);
        if (pageNum > maxPage) {
          maxPage = pageNum;
          if (u.pathname.match(/\/page-\d+\/?$/i)) {
            pathPattern = 'path';
            basePath = u.pathname.replace(/\/page-\d+\/?$/i, '/');
          } else if (u.searchParams.has('page')) {
            pathPattern = 'query';
            basePath = u.pathname;
          }
        }
      } catch {
        // ignore parse errors
      }
    }

    if (maxPage === 1 || !pathPattern) {
      // Single page or unrecognised pagination — just return current page
      return [new URL(currentUrl).href];
    }

    // Generate all page URLs
    const urls = [];
    for (let p = 1; p <= maxPage; p++) {
      if (pathPattern === 'path') {
        urls.push(p === 1
          ? `${baseOrigin}${basePath}`
          : `${baseOrigin}${basePath}page-${p}`);
      } else {
        urls.push(p === 1
          ? `${baseOrigin}${basePath}`
          : `${baseOrigin}${basePath}?page=${p}`);
      }
    }
    return urls;
  }

  function pageNumber(urlString) {
    try {
      const u = new URL(urlString, location.href);
      const m = u.pathname.match(/\/page-(\d+)\/?$/i);
      if (m) return Number(m[1]) || 1;
      const q = Number(u.searchParams.get('page'));
      return Number.isFinite(q) && q > 0 ? q : 1;
    } catch {
      return 1;
    }
  }

  async function fetchDocument(url) {
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status} for ${url}`);
    }
    const html = await res.text();
    const parser = new DOMParser();
    return parser.parseFromString(html, 'text/html');
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function scanCurrentPage() {
    const added = collectCandidatesFromDocument(document, location.href);
    renderCount();
    return added;
  }

  async function scanWholeThread() {
    const pageUrls = getThreadPageUrlsFromDocument(document, location.href);
    let totalAdded = 0;

    setStatus(`Найдено страниц: ${pageUrls.length}. Сканирую...`);
    await sleep(50);

    for (let i = 0; i < pageUrls.length; i += 1) {
      const pageUrl = pageUrls[i];
      const pct = Math.round(((i + 1) / pageUrls.length) * 100);
      setStatus(`Стр. ${i + 1} / ${pageUrls.length} (${pct}%)...`);
      setProgress(pct);

      try {
        let doc = document;
        if (pageUrl !== location.href) {
          doc = await fetchDocument(pageUrl);
          await sleep(400);
        }

        const added = collectCandidatesFromDocument(doc, pageUrl);
        totalAdded += added;
        renderCount();
      } catch (err) {
        console.error('[JPG6 Extractor] scan error on', pageUrl, ':', err);
        setStatus(`Ошибка стр. ${i + 1}: ${err.message}`);
        await sleep(200);
      }
    }

    setProgress(0);
    renderCount();
    return { pages: pageUrls.length, added: totalAdded };
  }

  function linksAsText() {
    const lines = allLinks();
    if (!lines.length) return '';
    return lines.sort().join('\n');
  }

  function safeFileName(input) {
    return input
      .replace(/[\\/:*?"<>|]/g, '_')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 100) || 'jpg6_links';
  }

  function downloadTxt() {
    const text = linksAsText();
    if (!text) {
      setStatus('Ссылок пока нет.');
      return;
    }

    const topic = safeFileName(document.title);
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
    const fileName = `${topic}_${stamp}.txt`;

    const blob = new Blob([text + '\n'], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
    setStatus(`Скачан файл: ${fileName}`);
  }

  async function copyToClipboard() {
    const text = linksAsText();
    if (!text) {
      setStatus('Ссылок пока нет.');
      return;
    }
    await navigator.clipboard.writeText(text);
    const total = state.imgPageLinks.size + state.albumLinks.size +
                  state.directImages.size + state.bunkrLinks.size;
    setStatus(`Скопировано ссылок: ${total}`);
  }

  function makeButton(label, onClick) {
    const btn = document.createElement('button');
    btn.textContent = label;
    btn.style.cssText = [
      'border:1px solid #2f3b4d',
      'border-radius:8px',
      'padding:8px 10px',
      'background:#0e1624',
      'color:#e5ecf5',
      'font:600 12px/1.2 system-ui, -apple-system, Segoe UI, sans-serif',
      'cursor:pointer',
    ].join(';');
    btn.addEventListener('click', onClick);
    return btn;
  }

  let statusEl;
  let countEl;
  let progressEl;

  function setStatus(text) {
    if (statusEl) statusEl.textContent = text;
  }

  function setProgress(pct) {
    if (progressEl) {
      progressEl.style.width = pct > 0 ? `${pct}%` : '0%';
      progressEl.style.display = pct > 0 ? 'block' : 'none';
    }
  }

  function renderCount() {
    if (!countEl) return;
    const img  = state.imgPageLinks.size + state.directImages.size;
    const alb  = state.albumLinks.size;
    const bunk = state.bunkrLinks.size;
    const parts = [];
    if (img  > 0) parts.push(`${img} фото`);
    if (alb  > 0) parts.push(`${alb} альб.`);
    if (bunk > 0) parts.push(`${bunk} bunkr`);
    countEl.textContent = parts.length ? `Найдено: ${parts.join(' / ')}` : 'Найдено: 0';
  }

  function lockUi(flag) {
    state.running = flag;
    panel.querySelectorAll('button').forEach((b) => {
      b.disabled = flag;
      b.style.opacity = flag ? '0.65' : '1';
    });
  }

  const panel = document.createElement('div');
  panel.id = 'jpg6-extractor-panel';
  panel.style.cssText = [
    'position:fixed',
    'right:16px',
    'bottom:16px',
    'z-index:2147483647',
    'width:260px',
    'background:#0b1220',
    'border:1px solid #25324a',
    'border-radius:12px',
    'box-shadow:0 12px 30px rgba(0,0,0,.35)',
    'padding:12px',
    'color:#e5ecf5',
    'font:12px/1.35 system-ui, -apple-system, Segoe UI, sans-serif',
  ].join(';');

  const title = document.createElement('div');
  title.textContent = 'JPG6 Extractor';
  title.style.cssText = 'font-weight:700;font-size:13px;margin-bottom:8px;';

  countEl = document.createElement('div');
  countEl.style.cssText = 'margin-bottom:4px;color:#c8d4e5;';
  countEl.textContent = 'Найдено: 0';

  // Progress bar (hidden by default, shown during scanWholeThread)
  const progressWrap = document.createElement('div');
  progressWrap.style.cssText = 'background:#1a2a40;border-radius:4px;height:4px;margin-bottom:8px;overflow:hidden;';
  progressEl = document.createElement('div');
  progressEl.style.cssText = 'height:4px;background:#4a90d9;border-radius:4px;width:0%;display:none;transition:width 0.3s;';
  progressWrap.appendChild(progressEl);

  statusEl = document.createElement('div');
  statusEl.style.cssText = 'min-height:16px;margin-top:8px;color:#8fb1d6;';
  statusEl.textContent = 'Готово';

  const grid = document.createElement('div');
  grid.style.cssText = 'display:grid;grid-template-columns:1fr 1fr;gap:6px;';

  const btnScanPage = makeButton('Скан страницы', async () => {
    if (state.running) return;
    lockUi(true);
    setStatus('Сканирую текущую страницу...');
    try {
      const added = await scanCurrentPage();
      setStatus(`Добавлено: ${added}`);
    } finally {
      lockUi(false);
    }
  });

  const btnScanThread = makeButton('Скан темы', async () => {
    if (state.running) return;
    lockUi(true);
    setStatus('Ищу страницы темы...');
    try {
      const info = await scanWholeThread();
      setStatus(`Страниц: ${info.pages}, добавлено: ${info.added}`);
    } finally {
      lockUi(false);
    }
  });

  const btnCopy = makeButton('Копировать', async () => {
    if (state.running) return;
    try {
      await copyToClipboard();
    } catch (err) {
      console.error('[JPG6 Extractor] clipboard error:', err);
      setStatus('Не удалось скопировать');
    }
  });

  const btnDownload = makeButton('Скачать TXT', () => {
    if (state.running) return;
    downloadTxt();
  });

  const btnClear = makeButton('Очистить', () => {
    if (state.running) return;
    state.imgPageLinks.clear();
    state.albumLinks.clear();
    state.directImages.clear();
    state.bunkrLinks.clear();
    state._seenCdnKeys.clear();
    renderCount();
    setStatus('Очищено');
  });
  btnClear.style.gridColumn = '1 / span 2';

  grid.append(btnScanPage, btnScanThread, btnCopy, btnDownload, btnClear);
  panel.append(title, countEl, progressWrap, grid, statusEl);
  document.documentElement.appendChild(panel);

  setStatus('Готово к сбору');
})();

// ==UserScript==
// @name         Simp Forum JPG6 Extractor
// @namespace    https://local.jpg6.downloader
// @version      0.3.0
// @description  Собирает оригинальные JPG6 ссылки из темы форума и экспортирует в TXT.
// @author       local
// @run-at       document-end
// @noframes
// @grant        none
// @match        *://simptown.su/*
// @match        *://*.simptown.su/*
// @match        *://simpcity.cr/*
// @match        *://*.simpcity.cr/*
// @include      /^https?:\/\/([^/]+\.)?simpcity\.[^/]+\/.*/
// ==/UserScript==

(function () {
  'use strict';

  const HOST_RE = /(^|\.)simptown\.su$|(^|\.)simpcity\.[a-z0-9.-]+$/i;
  const JPG_HOST_RE = /(^|\.)(jpg\d*\.(su|church|fish|fishing|pet|cr)|jpeg\d*\.(su|pet|cr)|selti-delivery\.ru)$/i;
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
    links: new Set(),
    running: false,
  };

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
    const allLinks = new Set();
    const roots = getScanRoots(doc);

    for (const root of roots) {
      // Per-post buckets
      const imgPageLinks = new Set();    // jpg6.su/img/TOKEN — preferred
      const albumLinks = new Set();      // albums / profiles — always included
      const directCdnLinks = new Set();  // raw CDN image URLs — only if no /img/ links

      function processRaw(raw) {
        if (!raw || typeof raw !== 'string') return;
        const abs = toAbsoluteUrl(raw.trim(), baseUrl);
        if (!abs) return;
        const unwrapped = unwrapForumRedirect(abs, baseUrl);
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

      // Preference rule: if this post has /img/ page links, ignore its raw CDN links
      // (they are the same images, just duplicate embeds by different users in the thread).
      // If the post has NO /img/ links, keep the raw CDN links (standalone embeds).
      for (const l of albumLinks) allLinks.add(l);
      for (const l of imgPageLinks) allLinks.add(l);
      if (imgPageLinks.size === 0) {
        for (const l of directCdnLinks) allLinks.add(l);
      }
    }

    // Script tags are page-global (not per-post).
    // Only collect /img/ and album links from scripts; skip bare CDN URLs.
    for (const scriptEl of doc.querySelectorAll('script')) {
      const s = scriptEl.textContent || '';
      for (const m of (s.match(URL_IN_HTML_RE) || [])) {
        const abs = toAbsoluteUrl(decodeMaybeUrl(m), baseUrl);
        if (!abs) continue;
        const unwrapped = unwrapForumRedirect(abs, baseUrl);
        const norm = normalizeJpgUrl(unwrapped);
        const kind = classifyJpgLink(norm);
        if (kind === 'img_page' || kind === 'album_or_profile') allLinks.add(norm);
      }
    }

    return allLinks;
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
    const found = collectCandidatesFromDocument(document, location.href);
    for (const link of found) state.links.add(link);
    renderCount();
    return found.size;
  }

  async function scanWholeThread() {
    const pageUrls = getThreadPageUrlsFromDocument(document, location.href);
    let totalAdded = 0;

    setStatus(`Найдено страниц: ${pageUrls.length}. Сканирую...`);
    await sleep(50);

    for (let i = 0; i < pageUrls.length; i += 1) {
      const pageUrl = pageUrls[i];
      setStatus(`Стр. ${i + 1} / ${pageUrls.length}...`);

      try {
        let doc = document;
        if (pageUrl !== location.href) {
          doc = await fetchDocument(pageUrl);
          await sleep(400);
        }

        const found = collectCandidatesFromDocument(doc, pageUrl);
        const before = state.links.size;
        for (const link of found) state.links.add(link);
        totalAdded += state.links.size - before;
        renderCount();
      } catch (err) {
        console.error('[JPG6 Extractor] scan error on', pageUrl, ':', err);
        setStatus(`Ошибка стр. ${i + 1}: ${err.message}`);
        await sleep(200);
      }
    }

    renderCount();
    return { pages: pageUrls.length, added: totalAdded };
  }

  function linksAsText() {
    return Array.from(state.links).sort().join('\n');
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
    setStatus(`Скопировано ссылок: ${state.links.size}`);
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

  function setStatus(text) {
    if (statusEl) statusEl.textContent = text;
  }

  function renderCount() {
    if (countEl) countEl.textContent = `Найдено: ${state.links.size}`;
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
  countEl.style.cssText = 'margin-bottom:8px;color:#c8d4e5;';
  countEl.textContent = 'Найдено: 0';

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
    state.links.clear();
    renderCount();
    setStatus('Очищено');
  });
  btnClear.style.gridColumn = '1 / span 2';

  grid.append(btnScanPage, btnScanThread, btnCopy, btnDownload, btnClear);
  panel.append(title, countEl, grid, statusEl);
  document.documentElement.appendChild(panel);

  setStatus('Готово к сбору');
})();

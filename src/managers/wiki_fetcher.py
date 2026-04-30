import os
import json
import re
import time
import threading
import shutil
import urllib.request
import urllib.parse

from ..config.config import get_app_data_dir

WIKI_API = "https://helldivers.wiki.gg/api.php"
CACHE_DIR_NAME = "wiki_cache"
ICONS_DIR_NAME = "icons"
DATA_FILE_NAME = "stratagems.json"
CACHE_MAX_AGE_SECONDS = 24 * 60 * 60

BATCH_SIZE = 50
REQUEST_DELAY = 0.5
RETRY_DELAYS = [2, 5, 15]
MAXLAG = 5
CHECK_INTERVAL_SECONDS = 6 * 60 * 60
REQUEST_LIMIT_PER_FETCH = 120

_cache_lock = threading.Lock()
_request_local = threading.local()


def get_cache_dir():
    return os.path.join(get_app_data_dir(), CACHE_DIR_NAME)


def get_icons_dir():
    return os.path.join(get_cache_dir(), ICONS_DIR_NAME)


def get_data_file():
    return os.path.join(get_cache_dir(), DATA_FILE_NAME)


def clear_cache():
    cache_dir = get_cache_dir()
    with _cache_lock:
        if os.path.isdir(cache_dir):
            shutil.rmtree(cache_dir, ignore_errors=True)
    return not os.path.exists(cache_dir)


def get_request_limit_per_fetch():
    return REQUEST_LIMIT_PER_FETCH


def _init_request_tracking(on_request_count=None):
    _request_local.count = 0
    _request_local.on_request_count = on_request_count
    callback = getattr(_request_local, "on_request_count", None)
    if callable(callback):
        callback(0, REQUEST_LIMIT_PER_FETCH)


def _track_request():
    if not hasattr(_request_local, "count"):
        return

    _request_local.count += 1
    callback = getattr(_request_local, "on_request_count", None)
    if callable(callback):
        callback(_request_local.count, REQUEST_LIMIT_PER_FETCH)


def _api_get(params, _retries=0):
    _track_request()
    params = dict(params)
    params["format"] = "json"
    params["maxlag"] = str(MAXLAG)
    url = WIKI_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "HelldiversMacro/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 429 and _retries < len(RETRY_DELAYS):
            delay = RETRY_DELAYS[_retries]
            print(f"[WikiFetcher] Rate limited (429), retrying in {delay}s...")
            time.sleep(delay)
            return _api_get(params, _retries + 1)
        raise
    data = json.loads(raw)
    if "error" in data and data["error"].get("code") == "maxlag" and _retries < len(RETRY_DELAYS):
        delay = RETRY_DELAYS[_retries]
        print(f"[WikiFetcher] Server busy (maxlag), retrying in {delay}s...")
        time.sleep(delay)
        return _api_get(params, _retries + 1)
    return data


def _is_excluded_title(title):
    if "(disambiguation)" in title:
        return True
    if title.startswith("Template:") or title.startswith("April Fools"):
        return True
    if re.search(r"/[a-z]{2}(?:-[a-z]{2})?$", title, re.IGNORECASE):
        return True
    if title in ("Stratagems", "Exosuit (disambiguation)", "Equipment Traits", "Reinforcement Pods"):
        return True
    return False


def _parse_stratagem_code(wikitext):
    m = re.search(r'\{\{Stratagem[_ ]code\|([^}]+)\}\}', wikitext, re.IGNORECASE)
    if not m:
        return None
    parts = [p.strip().lower() for p in m.group(1).split("|")]
    valid = {"up", "down", "left", "right"}
    sequence = [p for p in parts if p in valid]
    return sequence if sequence else None


def _parse_source(wikitext):
    m = re.search(r'\|\s*source\s*=\s*([^\n]+)', wikitext)
    if not m:
        return None
    source_raw = m.group(1).strip()
    link_m = re.search(r'\[\[.*?\|([^\]<]+)', source_raw)
    if link_m:
        return link_m.group(1).strip()
    plain = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', source_raw)
    plain = re.sub(r'<[^>]+>', '', plain).strip()
    plain = re.sub(r'\{\{[^}]+\}\}', '', plain).strip()
    return plain if plain else None


def _parse_icon_filename(wikitext):
    for field in ("stratagem_image", "image"):
        m = re.search(rf'\|\s*{field}\s*=\s*([^\n|}}]+)', wikitext)
        if m:
            fn = m.group(1).strip()
            if fn.lower().endswith(".svg"):
                return fn
    return None


def _parse_stratagem_type(wikitext):
    m = re.search(r'\|\s*stratagem_type\s*=\s*([^\n|}}]+)', wikitext)
    return m.group(1).strip() if m else None


def _fetch_all_wikitext_via_generator():
    results = {}
    params = {
        "action": "query",
        "generator": "categorymembers",
        "gcmtitle": "Category:Stratagems",
        "gcmlimit": str(BATCH_SIZE),
        "gcmtype": "page",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
    }
    page_num = 0
    while True:
        page_num += 1
        print(f"[WikiFetcher] Fetching page {page_num} of stratagems...")
        try:
            data = _api_get(params)
        except Exception as e:
            print(f"[WikiFetcher] Generator fetch error: {e}")
            break
        pages = data.get("query", {}).get("pages", {})
        for page_data in pages.values():
            if str(page_data.get("pageid", "-1")) == "-1":
                continue
            title = page_data.get("title", "")
            if _is_excluded_title(title):
                continue
            revisions = page_data.get("revisions", [])
            if not revisions:
                continue
            slots = revisions[0].get("slots", {})
            content = slots.get("main", {}).get("*", "") if slots else revisions[0].get("*", "")
            if content:
                results[title] = content
        cont = data.get("continue", {})
        if not cont:
            break
        params.update(cont)
        time.sleep(REQUEST_DELAY)
    return results


def _fetch_image_urls_for_new_icons(filenames, existing_icons_dir):
    results = {}
    need_url = [fn for fn in set(filenames) if not os.path.exists(os.path.join(existing_icons_dir, fn.replace(" ", "_")))]
    if not need_url:
        return results
    print(f"[WikiFetcher] Fetching URLs for {len(need_url)} new icons...")
    for i in range(0, len(need_url), BATCH_SIZE):
        batch = need_url[i:i + BATCH_SIZE]
        file_titles = "|".join(f"File:{fn}" for fn in batch)
        params = {
            "action": "query",
            "titles": file_titles,
            "prop": "imageinfo",
            "iiprop": "url",
        }
        try:
            data = _api_get(params)
        except Exception as e:
            print(f"[WikiFetcher] Image URL fetch error: {e}")
            time.sleep(REQUEST_DELAY)
            continue
        pages = data.get("query", {}).get("pages", {})
        for page_data in pages.values():
            title = page_data.get("title", "")
            if not title.startswith("File:"):
                continue
            fn = title[5:]
            imageinfo = page_data.get("imageinfo", [])
            if imageinfo:
                url = imageinfo[0].get("url", "")
                if url:
                    results[fn] = url
        if i + BATCH_SIZE < len(need_url):
            time.sleep(REQUEST_DELAY)
    return results


def _download_file(url, dest_path):
    req = urllib.request.Request(url, headers={"User-Agent": "HelldiversMacro/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        content = r.read()
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(content)


def _source_to_department(source, stratagem_type):
    if source:
        return source
    if stratagem_type:
        if stratagem_type.lower() in ("ship", "objective", "other"):
            return "Mission Specific"
    return "Mission Specific"


def fetch_and_cache(on_request_count=None):
    _init_request_tracking(on_request_count)
    print("[WikiFetcher] Fetching stratagems from wiki...")
    wikitext_map = _fetch_all_wikitext_via_generator()
    print(f"[WikiFetcher] Got wikitext for {len(wikitext_map)} pages.")

    stratagems_by_department = {}
    icon_filename_map = {}
    stratagem_type_map = {}

    for title, wikitext in wikitext_map.items():
        code = _parse_stratagem_code(wikitext)
        if code is None:
            continue
        source = _parse_source(wikitext)
        stratagem_type = _parse_stratagem_type(wikitext)
        department = _source_to_department(source, stratagem_type)
        icon_fn = _parse_icon_filename(wikitext)

        if department not in stratagems_by_department:
            stratagems_by_department[department] = {}
        stratagems_by_department[department][title] = code

        if icon_fn:
            icon_filename_map[title] = icon_fn
        if stratagem_type:
            stratagem_type_map[title] = stratagem_type

    icons_dir = get_icons_dir()
    os.makedirs(icons_dir, exist_ok=True)

    image_urls = _fetch_image_urls_for_new_icons(list(icon_filename_map.values()), icons_dir)

    downloaded_icons = {}
    for strat_name, icon_fn in icon_filename_map.items():
        safe_fn = icon_fn.replace(" ", "_")
        dest = os.path.join(icons_dir, safe_fn)
        if not os.path.exists(dest):
            url = image_urls.get(icon_fn, "")
            if not url:
                continue
            try:
                _download_file(url, dest)
                time.sleep(0.1)
            except Exception as e:
                print(f"[WikiFetcher] Failed downloading {icon_fn}: {e}")
                continue
        downloaded_icons[strat_name] = safe_fn

    cache_data = {
        "timestamp": time.time(),
        "latest_page_timestamp": _fetch_latest_category_timestamp() or "",
        "stratagems_by_department": stratagems_by_department,
        "icon_filename_map": downloaded_icons,
        "stratagem_type_map": stratagem_type_map,
    }

    cache_dir = get_cache_dir()
    os.makedirs(cache_dir, exist_ok=True)

    with _cache_lock:
        with open(get_data_file(), "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)

    total = sum(len(v) for v in stratagems_by_department.values())
    print(f"[WikiFetcher] Done. Cached {total} stratagems across {len(stratagems_by_department)} departments.")
    return stratagems_by_department, downloaded_icons


def load_cache():
    stratagems_by_department, icon_filename_map, _ = load_cache_with_metadata()
    return stratagems_by_department, icon_filename_map


def load_cache_with_metadata():
    path = get_data_file()
    if not os.path.exists(path):
        return None, None, {}
    try:
        with _cache_lock:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        return (
            data.get("stratagems_by_department"),
            data.get("icon_filename_map", {}),
            data.get("stratagem_type_map", {}),
        )
    except Exception as e:
        print(f"[WikiFetcher] Cache load error: {e}")
        return None, None, {}


def is_cache_stale():
    path = get_data_file()
    if not os.path.exists(path):
        return True
    try:
        with _cache_lock:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        age = time.time() - data.get("timestamp", 0)
        return age > CACHE_MAX_AGE_SECONDS
    except Exception:
        return True


def _fetch_latest_category_timestamp():
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:Stratagems",
        "cmlimit": "1",
        "cmsort": "timestamp",
        "cmdir": "desc",
        "cmprop": "timestamp",
        "cmtype": "page",
    }
    try:
        data = _api_get(params)
        members = data.get("query", {}).get("categorymembers", [])
        if members:
            return members[0].get("timestamp", "")
    except Exception as e:
        print(f"[WikiFetcher] Could not fetch latest category timestamp: {e}")
    return None


def _get_cached_page_timestamp():
    path = get_data_file()
    if not os.path.exists(path):
        return None
    try:
        with _cache_lock:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        return data.get("latest_page_timestamp") or None
    except Exception:
        return None


def _is_check_due():
    path = get_data_file()
    if not os.path.exists(path):
        return True
    try:
        with _cache_lock:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        age = time.time() - data.get("timestamp", 0)
        return age > CHECK_INTERVAL_SECONDS
    except Exception:
        return True


def has_new_content():
    if not os.path.exists(get_data_file()):
        return True
    if not _is_check_due():
        print("[WikiFetcher] Check interval not reached, skipping.")
        return False
    cached_ts = _get_cached_page_timestamp()
    wiki_ts = _fetch_latest_category_timestamp()
    if wiki_ts is None:
        return False
    if cached_ts is None or wiki_ts > cached_ts:
        print(f"[WikiFetcher] New content detected (wiki: {wiki_ts}, cached: {cached_ts}).")
        return True
    print(f"[WikiFetcher] No new content (wiki: {wiki_ts}).")
    return False


def get_cache_timestamp():
    path = get_data_file()
    if not os.path.exists(path):
        return None
    try:
        with _cache_lock:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        ts = data.get("timestamp")
        return ts
    except Exception:
        return None


def get_wiki_icon_path(name):
    path = get_data_file()
    if not os.path.exists(path):
        return None
    try:
        with _cache_lock:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        icon_filename_map = data.get("icon_filename_map", {})
        fn = icon_filename_map.get(name)
        if fn:
            return os.path.join(get_icons_dir(), fn)
        return None
    except Exception:
        return None


def refresh_in_background(on_complete=None, on_error=None, on_request_count=None):
    def _worker():
        try:
            stratagems, icons = fetch_and_cache(on_request_count=on_request_count)
            if on_complete:
                on_complete(stratagems, icons)
        except Exception as e:
            print(f"[WikiFetcher] Background refresh failed: {e}")
            if on_error:
                on_error(str(e))

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t

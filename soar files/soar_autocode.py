#!/usr/bin/env python3
from __future__ import annotations

import ast
import difflib
import html.parser
import json
import os
import random
import re
import shutil
import socket
import subprocess
import sys
import threading
import queue
import importlib.util
import time
import traceback
import urllib.request
from datetime import datetime
from pathlib import Path
from textwrap import dedent

APP_NAME = "SOAR AUTOCODE PRIME"
VERSION = "1.00.4"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "soar_data"
AUTOCODE_DIR = BASE_DIR / "Autocode"
PROJECTS_DIR = BASE_DIR 
TRASH_DIR = AUTOCODE_DIR / "_trash"

STATE_FILE = DATA_DIR / "state.json"
LOG_FILE = DATA_DIR / "autocode_log.txt"
SOURCES_FILE = DATA_DIR / "sources.txt"
SNIPPET_CACHE = DATA_DIR / "snippets_cache.json"
GENERATED_COMMANDS_JSON = DATA_DIR / "generated_commands.json"

AUTO_INTERVAL = int(os.getenv("SOAR_INTERVAL_SECONDS", "90"))
SYNC_INTERVAL = int(os.getenv("SOAR_SYNC_SECONDS", "600"))

# Keep awake-session generation light, but allow the system to run forever over time.
MIN_BATCH_FOLDERS = 1
MAX_BATCH_FOLDERS = 3

MAX_MEMORY = 120
MAX_RECENT = 30
MAX_SNIPPETS = 250
MAX_SNIPPET_CHARS = 6000

DEDUP_RECENT_WINDOW = 24
DEDUP_HIGH = 0.84
DEDUP_HARD = 0.92

TRASH_CUTOFF = 35
KEEP_CUTOFF = 65
PROMOTE_CUTOFF = 80

# Headless / background behavior.
AUTO_RUN_GENERATED = True
AUTO_RUN_TIMEOUT = 10
AUTO_START_API_SERVICES = False
AUTO_OPEN_WEB_APPS = False
AUTO_OPEN_FOLDERS = False
AUTO_OPEN_OUTPUT = False

stop_event = threading.Event()
manual_event = threading.Event()
sync_event = threading.Event()
state_lock = threading.Lock()

SOAR_AUTOCODE_TWO = None
SOAR_AUTOCODE_TWO_PATH = BASE_DIR / "soar_autocodetwo.py"
execution_queue = queue.Queue()

try:
    import queue
except Exception:
    queue = None

GOAL_SERIOUS_BOOSTS = {
    "productivity": ("notes_app", "file_tool", "python_cli", "launcher", "data_tool", "api_service"),
    "automation": ("python_cli", "file_tool", "api_service", "data_tool", "launcher"),
    "api": ("api_service", "python_cli", "data_tool"),
    "data": ("data_tool", "api_service", "python_cli"),
    "dashboard": ("web_app", "data_tool", "api_service"),
    "tooling": ("python_cli", "file_tool", "launcher", "api_service"),
    "workflow": ("python_cli", "launcher", "data_tool", "api_service"),
    "report": ("data_tool", "web_app", "api_service"),
    "sync": ("api_service", "python_cli", "data_tool"),
    "memory": ("notes_app", "data_tool", "python_cli"),
    "builder": ("python_cli", "launcher", "file_tool"),
    "system": ("python_cli", "api_service", "launcher"),
}

SERIOUS_WORDS = {
    "automation", "api", "tool", "tools", "dashboard", "data", "workflow", "pipeline",
    "report", "reports", "sync", "builder", "system", "assistant", "productivity",
    "suite", "platform", "service", "utility", "framework", "analysis", "monitor",
}
TOY_WORDS = {
    "game", "games", "mini game", "toy", "toy project", "pong", "snake", "clicker",
    "guess", "quiz", "arcade", "demo", "clone", "practice",
}


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    AUTOCODE_DIR.mkdir(parents=True, exist_ok=True)
    TRASH_DIR.mkdir(parents=True, exist_ok=True)


def stamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    line = f"[{stamp()}] {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line)


def default_state():
    return {
        "run_count": 0,
        "last_run": None,
        "last_project": None,
        "recent_projects": [],
        "memory": [],
        "template_weights": {
            "python_cli": 5,
            "web_app": 4,
            "api_service": 5,
            "file_tool": 5,
            "notes_app": 4,
            "data_tool": 5,
            "launcher": 3,
            "mini_game": 1,
        },
        "template_stats": {},
        "command_hits": {},
        "project_history": [],
        "sources": [
            "https://docs.python.org/3/",
            "https://realpython.com/",
            "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
            "https://fastapi.tiangolo.com/",
            "https://flask.palletsprojects.com/en/stable/",
            "https://nodejs.org/en/docs/",
            "https://react.dev/",
            "https://docs.github.com/en",
            "https://pypi.org/",
        ],
        "source_status": {},
        "web_library": [],
        "pattern_index": {"keywords": [], "signals": {}, "sources": []},
        "settings": {
            "sync_on_start": True,
            "use_web_when_online": True,
            "cache_web_code": True,
            "goal_mode": "",
        },
    }


def load_state():
    with state_lock:
        if not STATE_FILE.exists():
            return default_state()
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return default_state()
        except Exception:
            return default_state()

        state = default_state()
        state.update(data)
        for key, value in default_state().items():
            state.setdefault(key, value)
        state.setdefault("settings", default_state()["settings"])
        return state


def save_state(state):
    with state_lock:
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(STATE_FILE)


def clean_words(text):
    text = str(text or "")
    text = re.sub(r"[^A-Za-z0-9\s_-]+", " ", text)
    text = re.sub(r"[\s_-]+", " ", text).strip()
    return text


def safe_folder_base(name):
    name = clean_words(name)
    return name or "Project"


def unique_folder_name(name, root=AUTOCODE_DIR):
    base = safe_folder_base(name)
    folder = root / base
    if not folder.exists():
        return folder
    for i in range(1, 10000):
        candidate = root / f"{base} {i}"
        if not candidate.exists():
            return candidate
    return root / f"{base} {int(time.time())}"


def online_available(timeout=2.5):
    for host in [("1.1.1.1", 53), ("8.8.8.8", 53)]:
        try:
            with socket.create_connection(host, timeout=timeout):
                return True
        except Exception:
            pass
    return False


def read_sources(state):
    urls = []
    env = os.getenv("SOAR_SOURCE_URLS", "").strip()
    if env:
        for item in re.split(r"[\n,; ]+", env):
            item = item.strip()
            if item:
                urls.append(item)
    if SOURCES_FILE.exists():
        try:
            for line in SOURCES_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
        except Exception:
            pass
    for item in state.get("sources", []):
        item = str(item).strip()
        if item:
            urls.append(item)

    out = []
    seen = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def write_sources(state):
    urls = read_sources(state)
    SOURCES_FILE.write_text("\n".join(urls) + ("\n" if urls else ""), encoding="utf-8")


class CodeHTMLParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.capture = False
        self.buffers = []
        self.current = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        if tag in ("pre", "code"):
            self.capture = True
            self.current = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        if tag in ("pre", "code"):
            if self.capture and self.current:
                text = "".join(self.current).strip()
                if text:
                    self.buffers.append(text)
            self.capture = False
            self.current = []

    def handle_data(self, data):
        if self.in_title:
            self.title += data.strip() + " "
        if self.capture:
            self.current.append(data)


def fetch_url(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        content_type = resp.headers.get_content_type()
        charset = resp.headers.get_content_charset() or "utf-8"
    text = raw.decode(charset, errors="replace")
    return text, content_type


def stable_id(text):
    import hashlib
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def extract_snippets(text, source_url="", title=""):
    snippets = []
    if any(tag in text.lower() for tag in ["<html", "<pre", "<code", "<body"]):
        parser = CodeHTMLParser()
        try:
            parser.feed(text)
        except Exception:
            pass
        title = (parser.title.strip() or title or source_url).strip()
        chunks = parser.buffers
    else:
        title = title or source_url
        chunks = re.split(r"\n{3,}", text)

    for chunk in chunks:
        chunk = str(chunk).replace("\r\n", "\n").strip()
        if len(chunk) < 20:
            continue
        snippets.append({"source": source_url, "title": title, "text": chunk[:MAX_SNIPPET_CHARS]})

    unique = []
    seen = set()
    for item in snippets:
        key = stable_id(item["text"][:1200])
        if key in seen:
            continue
        seen.add(key)
        item["id"] = key
        unique.append(item)
    return unique


def profile_text(text):
    lower = text.lower()
    tokens = re.findall(r"[a-z_][a-z0-9_]{2,}", lower)
    freq = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1

    keywords = [k for k, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:30]]
    signals = {
        "python": int(any(x in lower for x in ["import ", "def ", "pathlib", "async def", 'if __name__ == "__main__"', "if __name__ == '__main__'"])),
        "web": int(any(x in lower for x in ["document.", "window.", "fetch(", "<html", "button", "localstorage"])),
        "api": int(any(x in lower for x in ["fastapi", "flask", "route", "endpoint", "request.json", "jsonify"])),
        "data": int(any(x in lower for x in ["json", "csv", "sqlite", "pandas", "yaml", "pickle"])),
        "game": int(any(x in lower for x in ["pygame", "score", "random.randint", "sprite", "collision"])),
        "automation": int(any(x in lower for x in ["subprocess", "os.system", "threading", "schedule", "watchdog", "shutil"])),
        "ui": int(any(x in lower for x in ["tkinter", "customtkinter", "pyqt", "widget", "frame"])),
        "cli": int(any(x in lower for x in ["argparse", "input(", "print(", "sys.argv"])),
        "db": int(any(x in lower for x in ["sqlite3", "sqlalchemy", "database", "cursor.execute", "insert into"])),
        "test": int(any(x in lower for x in ["pytest", "unittest", "assert ", "mock"])),
    }
    return {"keywords": keywords, "signals": signals}


def merge_pattern_index(existing, profile, source_name):
    existing = existing or {"keywords": [], "signals": {}, "sources": []}
    keywords = existing.get("keywords", [])
    for kw in profile.get("keywords", []):
        if kw not in keywords:
            keywords.append(kw)

    signals = existing.get("signals", {})
    for key, val in profile.get("signals", {}).items():
        signals[key] = int(signals.get(key, 0)) + int(val)

    sources = existing.get("sources", [])
    if source_name and source_name not in sources:
        sources.append(source_name)

    return {"keywords": keywords[:300], "signals": signals, "sources": sources[:50]}


def load_cached_snippets():
    if not SNIPPET_CACHE.exists():
        return []
    try:
        data = json.loads(SNIPPET_CACHE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_cached_snippets(snippets):
    SNIPPET_CACHE.write_text(json.dumps(snippets[-MAX_SNIPPETS:], indent=2, ensure_ascii=False), encoding="utf-8")


def sync_sources(state, force=False):
    urls = read_sources(state)
    if not urls:
        state.setdefault("source_status", {})["message"] = "no sources configured"
        state["source_status"]["last_sync"] = datetime.now().isoformat()
        save_state(state)
        return state, []

    if not force and not online_available():
        cached = load_cached_snippets()
        if cached:
            state["web_library"] = cached[-MAX_SNIPPETS:]
            state.setdefault("source_status", {})["message"] = "offline, using cache"
            state["source_status"]["last_sync"] = datetime.now().isoformat()
            save_state(state)
            return state, cached
        state.setdefault("source_status", {})["message"] = "offline, no cache"
        state["source_status"]["last_sync"] = datetime.now().isoformat()
        save_state(state)
        return state, []

    library = list(state.get("web_library", []))
    seen = {item.get("id") for item in library if isinstance(item, dict)}
    new_items = []
    status = state.get("source_status", {})

    for url in urls:
        try:
            text, ctype = fetch_url(url)
            snippets = extract_snippets(text, source_url=url, title=url)
            if not snippets and ctype.startswith("text/"):
                snippets = [{
                    "id": stable_id(url + text[:1000]),
                    "source": url,
                    "title": url,
                    "text": text[:MAX_SNIPPET_CHARS],
                }]

            for snippet in snippets:
                text_snip = snippet.get("text", "").strip()
                if len(text_snip) < 20:
                    continue
                sid = snippet.get("id") or stable_id(url + text_snip[:1200])
                if sid in seen:
                    continue
                seen.add(sid)
                record = {
                    "id": sid,
                    "source": url,
                    "title": snippet.get("title") or url,
                    "text": text_snip,
                    "profile": profile_text(text_snip),
                    "fetched_at": datetime.now().isoformat(),
                }
                library.append(record)
                new_items.append(record)
                state["pattern_index"] = merge_pattern_index(state.get("pattern_index", {}), record["profile"], url)

            status[url] = {"ok": True, "snippets": len(snippets), "fetched_at": datetime.now().isoformat()}
        except Exception as e:
            status[url] = {"ok": False, "error": str(e), "fetched_at": datetime.now().isoformat()}
            log(f"sync failed for {url}: {e}")

    state["web_library"] = library[-MAX_SNIPPETS:]
    state["source_status"] = status
    state["source_status"]["message"] = f"synced {len(new_items)} new snippets"
    state["source_status"]["last_sync"] = datetime.now().isoformat()
    save_cached_snippets(state["web_library"])
    save_state(state)
    return state, new_items


def weighted_pick(weights):
    items = list(weights.items())
    if not items:
        return "python_cli"
    total = sum(max(1, int(v)) for _, v in items)
    roll = random.uniform(0, total)
    upto = 0
    for key, value in items:
        upto += max(1, int(value))
        if upto >= roll:
            return key
    return random.choice(items)[0]


def smart_words():
    return {
        "smart", "upgrade", "learn", "core", "engine", "assistant", "builder", "system",
        "automation", "framework", "library", "scale", "memory", "knowledge", "codebase",
        "refactor", "orchestrator", "architecture", "tooling", "capability", "analysis",
        "intelligence", "parser", "scanner", "analyzer", "scheduler", "workflow", "pipeline",
        "dashboard", "api", "service", "report", "monitor", "generator", "search", "index",
        "validator", "export", "import", "sync", "productivity", "suite", "data", "utility",
    }


def toy_words():
    return {
        "pong", "ping pong", "game", "mini", "toy", "guess", "demo", "clone", "arcade",
        "practice", "prototype", "simple", "clicker", "snake", "tic tac toe",
    }


IMPORTANT_TEMPLATES = {
    "api_service": 18,
    "data_tool": 16,
    "python_cli": 15,
    "file_tool": 14,
    "notes_app": 10,
    "launcher": 9,
    "web_app": 9,
    "mini_game": 2,
}

SERIOUS_TEMPLATE_BIAS = {
    "api_service": 2,
    "data_tool": 2,
    "python_cli": 2,
    "file_tool": 2,
    "notes_app": 1,
    "launcher": 1,
    "web_app": 1,
}

TOY_TEMPLATE_BIAS = {"mini_game": 1, "web_app": 1}


def goal_text(state):
    goal = str(state.get("settings", {}).get("goal_mode", "") or "").strip()
    if not goal:
        goal = str(os.getenv("SOAR_GOAL", "") or "").strip()
    return goal


def goal_keywords(goal):
    goal = clean_words(goal).lower()
    if not goal:
        return []
    words = re.findall(r"[a-z0-9]+", goal)
    stop = {"a", "an", "and", "the", "to", "of", "for", "with", "build", "make", "create", "project", "suite"}
    return [w for w in words if w not in stop]


def similarity_score(a, b):
    a = clean_words(a).lower()
    b = clean_words(b).lower()
    if not a or not b:
        return 0.0
    seq = difflib.SequenceMatcher(None, a, b).ratio()
    ta = set(a.split())
    tb = set(b.split())
    jacc = len(ta & tb) / max(1, len(ta | tb))
    return (seq * 0.7) + (jacc * 0.3)


def dedupe_similarity(state, name, focus, template=None, goal=None):
    history = list(state.get("project_history", []))[-DEDUP_RECENT_WINDOW:]
    target = f"{name} {focus} {template or ''} {goal or ''}"
    best = 0.0
    best_hit = None
    for item in history:
        text = f"{item.get('name', '')} {item.get('focus', '')} {item.get('template', '')}"
        s = similarity_score(target, text)
        if s > best:
            best = s
            best_hit = item
    return best, best_hit


def project_importance_score(state, spec):
    template = str(spec.get("template", "")).strip()
    focus = str(spec.get("focus", "")).strip()
    desc = str(spec.get("description", "")).strip()
    goal = str(spec.get("goal", "")).strip()
    text = f"{template} {focus} {desc} {goal}".lower()

    score = 36
    score += int(IMPORTANT_TEMPLATES.get(template, 0))

    for word in smart_words():
        if word in text:
            score += 4

    for word in toy_words():
        if word in text:
            score -= 4

    if any(phrase in text for phrase in ("ping pong", "pong", "snake", "guess the number", "clicker", "tiny game", "mini game")):
        score -= 12

    if any(phrase in text for phrase in ("upgrade", "smart", "core", "assistant", "memory", "refactor", "engine", "architecture", "automation", "framework", "validator", "analyzer", "dashboard", "pipeline", "workflow", "productivity", "suite", "api", "data")):
        score += 10

    signals = state.get("pattern_index", {}).get("signals", {}) or {}
    score += int(signals.get("automation", 0)) * 4
    score += int(signals.get("api", 0)) * 3
    score += int(signals.get("data", 0)) * 3
    score += int(signals.get("python", 0)) * 2
    score += int(signals.get("ui", 0)) * 2
    score += int(signals.get("web", 0)) * 2
    score += int(signals.get("cli", 0)) * 2
    score += int(signals.get("db", 0)) * 3
    score += int(signals.get("test", 0)) * 3
    score -= int(signals.get("game", 0)) * 4

    if goal:
        lowered = goal.lower()
        if any(k in lowered for k in SERIOUS_WORDS):
            score += 8
        if any(k in lowered for k in TOY_WORDS):
            score -= 8

    memory_count = len(state.get("memory", []))
    history_count = len(state.get("project_history", []))
    score += min(10, memory_count // 15)
    score += min(10, history_count // 20)
    return max(0, min(100, score))


def importance_label(score):
    if score >= PROMOTE_CUTOFF:
        return "promote"
    if score >= KEEP_CUTOFF:
        return "keep"
    if score >= TRASH_CUTOFF:
        return "normal"
    return "trash"


def choose_batch_size(state, spec):
    score = project_importance_score(state, spec)
    size = 1 if score < 40 else 2 if score < 75 else 3
    return max(MIN_BATCH_FOLDERS, min(MAX_BATCH_FOLDERS, size)), score


def think_delay_for_importance(score):
    base = 0.20 + (score / 100.0) * 2.2
    jitter = random.uniform(0.0, 0.5)
    return round(base + jitter, 2)


def focus_pool_from_state(state, template, goal="", avoid_words=None):
    avoid_words = {w.lower() for w in (avoid_words or set()) if w}
    pattern = state.get("pattern_index", {}) or {}
    keywords = list(pattern.get("keywords", []) or [])
    signals = pattern.get("signals", {}) or {}

    goal_words = goal_keywords(goal)
    pool = []

    for key in ["web", "api", "data", "automation", "ui", "cli", "db", "test"]:
        if int(signals.get(key, 0)) > 0:
            pool.append(key)

    pool.extend(goal_words[:20])
    pool.extend(keywords[:24])
    pool.extend([x for x in state.get("recent_projects", [])[-10:] if x])

    history = state.get("project_history", [])[-12:]
    for item in history:
        pool.extend(goal_keywords(f"{item.get('name','')} {item.get('focus','')}"))

    if template == "web_app":
        pool.extend(["dashboard", "studio", "planner", "tracker", "portal"])
    elif template == "api_service":
        pool.extend(["service", "endpoint", "sync", "json", "crud", "bridge"])
    elif template == "mini_game":
        pool.extend(["arcade", "quest", "runner", "match"])
    elif template == "file_tool":
        pool.extend(["sort", "organize", "clean", "archive", "preview"])
    elif template == "notes_app":
        pool.extend(["notes", "memory", "journal", "capture", "search"])
    elif template == "data_tool":
        pool.extend(["report", "insight", "metrics", "csv", "analysis"])
    elif template == "launcher":
        pool.extend(["launcher", "hub", "menu", "dock"])
    else:
        pool.extend(["helper", "tool", "builder", "starter"])

    cleaned = []
    for item in pool:
        item = clean_words(item).lower()
        if not item or item in avoid_words:
            continue
        cleaned.append(item)

    if not cleaned:
        cleaned = ["tool", "builder", "system"]
    return cleaned


def derive_focus(state, template, goal="", avoid_words=None):
    pool = focus_pool_from_state(state, template, goal=goal, avoid_words=avoid_words)
    if goal:
        goal_line = clean_words(goal).lower()
        if template == "web_app":
            pool = [x for x in pool if x not in {"game", "cli"}] or pool
        elif template == "api_service":
            pool = [x for x in pool if x not in {"game"}] or pool
        elif template == "mini_game":
            pool = [x for x in pool if x not in {"api", "cli"}] or pool
        elif template == "file_tool":
            pool = [x for x in pool if x not in {"game", "web"}] or pool
        if goal_line:
            pool = [goal_line] + pool
    return random.choice(pool)


def build_description(template, focus, goal=""):
    text = focus.replace("_", " ")
    goal_part = f" for {clean_words(goal).lower()}" if goal else ""
    if template == "web_app":
        return f"a polished interactive web app for {text}{goal_part}"
    if template == "api_service":
        return f"a local JSON API for {text}{goal_part}"
    if template == "mini_game":
        return f"a small text game about {text}{goal_part}"
    if template == "file_tool":
        return f"a file helper for {text}{goal_part}"
    if template == "notes_app":
        return f"a memory app for {text}{goal_part}"
    if template == "data_tool":
        return f"a data utility for {text}{goal_part}"
    if template == "launcher":
        return f"a launcher hub built around {text}{goal_part}"
    return f"a useful command line starter for {text}{goal_part}"


def readable_project_name(template, focus, goal=""):
    prefix_map = {
        "python_cli": ["Core", "Signal", "Nova", "Prime", "Orbit", "Pulse"],
        "web_app": ["Studio", "Vista", "Panel", "Beacon", "Flow", "Atlas"],
        "api_service": ["Gateway", "Bridge", "Kernel", "Relay", "Nexus", "Link"],
        "mini_game": ["Arcade", "Quest", "Sprint", "Loop", "Dash"],
        "file_tool": ["File", "Folder", "Clean", "Sort", "Archive", "Sweep"],
        "notes_app": ["Notes", "Memory", "Journal", "Recall", "Trace"],
        "data_tool": ["Data", "Report", "Metric", "Grid", "Insight", "Chart"],
        "launcher": ["Launch", "Hub", "Dock", "Menu", "Board"],
    }
    noun_map = {
        "python_cli": ["Assistant", "Engine", "Tool", "Builder", "System"],
        "web_app": ["Board", "Dashboard", "Studio", "Space", "Center"],
        "api_service": ["Service", "API", "Node", "Engine", "Link"],
        "mini_game": ["Game", "Run", "Play", "Match", "Quest"],
        "file_tool": ["Helper", "Manager", "Organizer", "Cleaner", "Tool"],
        "notes_app": ["Vault", "Book", "Keeper", "Hub", "Pad"],
        "data_tool": ["Tool", "Analyzer", "Reporter", "Lab", "View"],
        "launcher": ["Hub", "Board", "Dock", "Panel", "Starter"],
    }

    focus_words = clean_words(focus).split()
    goal_words = goal_keywords(goal)
    key_part = " ".join(word.capitalize() for word in (goal_words[:2] or focus_words[:2] or ["Project"]))
    focus_part = " ".join(word.capitalize() for word in focus_words[:2]) if focus_words else "Project"

    prefix = random.choice(prefix_map.get(template, ["Core"]))
    noun = random.choice(noun_map.get(template, ["Project"]))

    parts = [prefix]
    if goal_words and random.random() < 0.7:
        parts.append(key_part)
    else:
        parts.append(focus_part)
    parts.append(noun)

    name = " ".join(parts).strip()
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > 40:
        name = f"{prefix} {noun} {focus_part}".strip()
        name = re.sub(r"\s+", " ", name).strip()
    return name


def choose_template(state, importance_score, goal="", avoid_template=None):
    weights = dict(state.get("template_weights", {}) or {})
    goal_lower = goal.lower().strip()

    if importance_score >= 70:
        for key in ["api_service", "data_tool", "python_cli", "file_tool", "notes_app"]:
            weights[key] = int(weights.get(key, 1)) + 2
    elif importance_score <= 25:
        weights["mini_game"] = int(weights.get("mini_game", 1)) + 2

    for word, templates in GOAL_SERIOUS_BOOSTS.items():
        if word in goal_lower:
            for template in templates:
                weights[template] = int(weights.get(template, 1)) + 3

    if goal_lower and any(w in goal_lower for w in SERIOUS_WORDS):
        for key in ["api_service", "data_tool", "python_cli", "file_tool", "launcher"]:
            weights[key] = int(weights.get(key, 1)) + 2
        weights["mini_game"] = max(1, int(weights.get("mini_game", 1)) - 1)

    if goal_lower and any(w in goal_lower for w in TOY_WORDS):
        weights["mini_game"] = int(weights.get("mini_game", 1)) + 2

    if avoid_template and avoid_template in weights:
        weights[avoid_template] = max(1, int(weights[avoid_template]) - 3)

    weights["mini_game"] = max(1, int(weights.get("mini_game", 1)) // 2)
    return weighted_pick(weights)


def template_python_cli(name, desc, focus, snippets):
    template = dedent("""
    from __future__ import annotations

    import argparse
    import json
    from datetime import datetime
    from pathlib import Path

    APP_NAME = "__NAME__"
    DESCRIPTION = "__DESC__"
    FOCUS = "__FOCUS__"
    DATA_DIR = Path(__file__).resolve().parent / "data"
    DATA_DIR.mkdir(exist_ok=True)
    STATE_FILE = DATA_DIR / "state.json"
    NOTES_FILE = DATA_DIR / "notes.json"

    def load_json(path, default):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return default

    def save_json(path, data):
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def status():
        state = load_json(STATE_FILE, {"runs": 0, "focus": FOCUS, "notes": []})
        print(APP_NAME)
        print(DESCRIPTION)
        print("focus:", FOCUS)
        print("runs:", state.get("runs", 0))
        print("notes:", len(state.get("notes", [])))
        print("time:", datetime.now().isoformat(timespec="seconds"))

    def add_note(text):
        state = load_json(STATE_FILE, {"runs": 0, "focus": FOCUS, "notes": []})
        state.setdefault("notes", []).append({"text": text, "time": datetime.now().isoformat(timespec="seconds")})
        state["runs"] = int(state.get("runs", 0)) + 1
        state["focus"] = FOCUS
        save_json(STATE_FILE, state)
        save_json(NOTES_FILE, state.get("notes", []))
        print("saved note")

    def list_notes():
        notes = load_json(NOTES_FILE, [])
        if not notes:
            print("no notes")
            return
        for i, note in enumerate(notes[-50:], 1):
            if isinstance(note, dict):
                print(f"{i}. {note.get('text', '')}")
            else:
                print(f"{i}. {note}")

    def main():
        parser = argparse.ArgumentParser(prog=APP_NAME.lower().replace(" ", "-"))
        sub = parser.add_subparsers(dest="cmd")

        sub.add_parser("status")
        note = sub.add_parser("note")
        note.add_argument("text", nargs="+")
        sub.add_parser("notes")

        args = parser.parse_args()

        state = load_json(STATE_FILE, {"runs": 0, "focus": FOCUS, "notes": []})
        state["runs"] = int(state.get("runs", 0)) + 1
        state["focus"] = FOCUS
        save_json(STATE_FILE, state)

        if args.cmd == "note":
            add_note(" ".join(args.text).strip())
        elif args.cmd == "notes":
            list_notes()
        else:
            status()

    if __name__ == "__main__":
        main()
    """).replace("__NAME__", name).replace("__DESC__", desc).replace("__FOCUS__", focus)
    readme = f"# {name}\n\n{desc}\n\n## Focus\n{focus}\n\n## Inspired by\n" + ("\n".join(f"- {s}" for s in snippets) if snippets else "- local knowledge") + "\n\n## Quick start\n- python main.py status\n- python main.py note \"hello\"\n- python main.py notes\n"
    return {"main.py": template, "README.md": readme, "requirements.txt": "", "project_manifest.json": json.dumps({"type": "python_cli", "name": name, "description": desc, "focus": focus, "snippets": snippets, "features": ["argparse", "notes", "state"]}, indent=2)}


def template_web_app(name, desc, focus, snippets):
    index = dedent("""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>__NAME__</title>
      <link rel="stylesheet" href="style.css">
    </head>
    <body>
      <main class="app">
        <section class="card">
          <div class="head">
            <div>
              <h1>__NAME__</h1>
              <p>__DESC__</p>
              <p class="focus">__FOCUS__</p>
            </div>
            <button id="clear">Clear</button>
          </div>
          <div class="row">
            <input id="note" placeholder="Write a note or task">
            <button id="add">Add</button>
          </div>
          <div class="row">
            <input id="search" placeholder="Search">
          </div>
          <div id="list" class="list"></div>
          <pre id="out"></pre>
        </section>
      </main>
      <script src="script.js"></script>
    </body>
    </html>
    """).replace("__NAME__", name).replace("__DESC__", desc).replace("__FOCUS__", focus)

    css = dedent("""
    :root {
      color-scheme: dark;
      font-family: Inter, system-ui, sans-serif;
    }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: linear-gradient(180deg, #10131a, #05070a);
      color: #eef2ff;
    }
    .app { width: min(980px, calc(100vw - 32px)); padding: 24px; }
    .card {
      padding: 28px;
      border-radius: 24px;
      background: rgba(18, 21, 31, 0.94);
      box-shadow: 0 20px 80px rgba(0, 0, 0, 0.4);
      border: 1px solid rgba(255,255,255,0.08);
    }
    .head { display: flex; justify-content: space-between; gap: 12px; align-items: start; }
    .row { display: flex; gap: 12px; flex-wrap: wrap; margin: 16px 0; }
    input {
      flex: 1;
      min-width: 220px;
      box-sizing: border-box;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.1);
      background: rgba(255,255,255,0.05);
      color: inherit;
    }
    button {
      border: 0;
      border-radius: 14px;
      padding: 12px 18px;
      font: inherit;
      cursor: pointer;
      background: #f8fafc;
      color: #0f172a;
    }
    .list { display: grid; gap: 10px; margin-top: 14px; }
    .item { padding: 14px 16px; border-radius: 16px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); }
    .small { opacity: 0.72; font-size: 0.92rem; }
    pre { white-space: pre-wrap; word-break: break-word; padding: 14px 16px; border-radius: 16px; background: rgba(255,255,255,0.05); }
    .focus { opacity: 0.8; }
    """)

    js = dedent("""
    const note = document.getElementById("note");
    const add = document.getElementById("add");
    const clear = document.getElementById("clear");
    const search = document.getElementById("search");
    const list = document.getElementById("list");
    const out = document.getElementById("out");

    const state = { items: JSON.parse(localStorage.getItem("items") || "[]") };

    function save() { localStorage.setItem("items", JSON.stringify(state.items)); }

    function render() {
      const q = (search && search.value || "").trim().toLowerCase();
      const items = state.items.filter(x => !q || x.text.toLowerCase().includes(q));
      if (list) {
        list.innerHTML = items.map((x) => `
          <div class="item">
            <div>${x.text}</div>
            <div class="small">${x.kind} · ${x.time}</div>
          </div>
        `).join("") || "<div class='small'>No items yet.</div>";
      }
      if (out) out.textContent = `items: ${state.items.length}\nfiltered: ${items.length}`;
    }

    if (add) {
      add.addEventListener("click", () => {
        const text = (note && note.value || "").trim();
        if (!text) return;
        state.items.unshift({ text, kind: text.length > 40 ? "note" : "task", time: new Date().toLocaleString() });
        state.items = state.items.slice(0, 200);
        save();
        if (note) note.value = "";
        render();
      });
    }

    if (clear) clear.addEventListener("click", () => { state.items = []; save(); render(); });
    if (search) search.addEventListener("input", render);
    render();
    """)

    readme = f"# {name}\n\n{desc}\n\n## Focus\n{focus}\n\n## Inspired by\n" + ("\n".join(f"- {s}" for s in snippets) if snippets else "- local knowledge") + "\n\n## Quick start\nOpen index.html in a browser.\n"
    return {"index.html": index, "style.css": css, "script.js": js, "README.md": readme, "project_manifest.json": json.dumps({"type": "web_app", "name": name, "description": desc, "focus": focus, "snippets": snippets, "features": ["localStorage", "search", "notes"]}, indent=2)}


def template_api_service(name, desc, focus, snippets):
    app = dedent("""
    from __future__ import annotations

    import json
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from pathlib import Path

    APP_NAME = "__NAME__"
    DESCRIPTION = "__DESC__"
    FOCUS = "__FOCUS__"
    DATA_DIR = Path(__file__).resolve().parent / "data"
    DATA_DIR.mkdir(exist_ok=True)
    DB_FILE = DATA_DIR / "db.json"

    def load_db():
        if DB_FILE.exists():
            try:
                return json.loads(DB_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"items": []}

    def save_db(db):
        DB_FILE.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, payload):
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _read_body(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b"{}"
            try:
                return json.loads(body.decode("utf-8"))
            except Exception:
                return {}

        def do_GET(self):
            db = load_db()
            if self.path in ("/", "/health"):
                self._send(200, {"name": APP_NAME, "description": DESCRIPTION, "focus": FOCUS, "items": len(db.get("items", []))})
                return
            if self.path == "/items":
                self._send(200, db)
                return
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/items":
                self._send(404, {"error": "not found"})
                return
            data = self._read_body()
            db = load_db()
            item = {"id": len(db.get("items", [])) + 1, "title": str(data.get("title", "")).strip(), "body": str(data.get("body", "")).strip(), "created_at": data.get("created_at") or ""}
            db.setdefault("items", []).append(item)
            save_db(db)
            self._send(201, {"ok": True, "item": item})

        def do_PUT(self):
            parts = self.path.split("/")
            if len(parts) != 3 or parts[1] != "items":
                self._send(404, {"error": "not found"})
                return
            try:
                item_id = int(parts[2])
            except Exception:
                self._send(400, {"error": "bad id"})
                return
            data = self._read_body()
            db = load_db()
            items = db.get("items", [])
            for item in items:
                if int(item.get("id", 0)) == item_id:
                    item["title"] = str(data.get("title", item.get("title", ""))).strip()
                    item["body"] = str(data.get("body", item.get("body", ""))).strip()
                    save_db(db)
                    self._send(200, {"ok": True, "item": item})
                    return
            self._send(404, {"error": "not found"})

        def do_DELETE(self):
            parts = self.path.split("/")
            if len(parts) != 3 or parts[1] != "items":
                self._send(404, {"error": "not found"})
                return
            try:
                item_id = int(parts[2])
            except Exception:
                self._send(400, {"error": "bad id"})
                return
            db = load_db()
            items = db.get("items", [])
            before = len(items)
            items = [item for item in items if int(item.get("id", 0)) != item_id]
            db["items"] = items
            save_db(db)
            if len(items) == before:
                self._send(404, {"error": "not found"})
            else:
                self._send(200, {"ok": True})

    def main():
        server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
        print(f"{APP_NAME} running on http://127.0.0.1:8000")
        server.serve_forever()

    if __name__ == "__main__":
        main()
    """).replace("__NAME__", name).replace("__DESC__", desc).replace("__FOCUS__", focus)

    readme = f"# {name}\n\n{desc}\n\n## Focus\n{focus}\n\n## Inspired by\n" + ("\n".join(f"- {s}" for s in snippets) if snippets else "- local knowledge") + "\n\n## Quick start\n- python app.py\n- GET /health\n- POST /items\n- PUT /items/1\n- DELETE /items/1\n"
    return {"app.py": app, "requirements.txt": "", "README.md": readme, "project_manifest.json": json.dumps({"type": "api_service", "name": name, "description": desc, "focus": focus, "snippets": snippets, "features": ["CRUD", "health", "json"]}, indent=2)}


def template_file_tool(name, desc, focus, snippets):
    main = dedent("""
    from __future__ import annotations

    from dataclasses import dataclass
    from datetime import datetime
    from pathlib import Path

    APP_NAME = "__NAME__"
    DESCRIPTION = "__DESC__"
    FOCUS = "__FOCUS__"

    @dataclass
    class FileInfo:
        path: Path
        size: int
        modified: float

        @property
        def age_days(self) -> float:
            return max(0.0, (datetime.now().timestamp() - self.modified) / 86400.0)

    def scan(root: Path):
        items = []
        for path in root.rglob("*"):
            if path.is_file():
                try:
                    stat = path.stat()
                    items.append(FileInfo(path=path, size=stat.st_size, modified=stat.st_mtime))
                except Exception:
                    pass
        return items

    def categorize(path: Path):
        ext = path.suffix.lower()
        if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            return "Images"
        if ext in {".mp4", ".mov", ".mkv", ".avi"}:
            return "Videos"
        if ext in {".mp3", ".wav", ".m4a", ".flac"}:
            return "Audio"
        if ext in {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf"}:
            return "Documents"
        if ext in {".zip", ".rar", ".7z", ".tar", ".gz"}:
            return "Archives"
        if ext in {".py", ".js", ".html", ".css", ".json", ".ts", ".java", ".cpp"}:
            return "Code"
        return "Other"

    def main():
        root = Path.home() / "Desktop"
        items = scan(root)
        print(APP_NAME)
        print(DESCRIPTION)
        print("focus:", FOCUS)
        print("root:", root)
        print("files found:", len(items))
        print("top candidates:")
        for item in sorted(items, key=lambda x: (x.age_days, x.size), reverse=True)[:20]:
            print(f"- {item.path} | {item.size} bytes | {item.age_days:.1f} days | {categorize(item.path)}")
        print("\nThis tool is dry-run only. It does not delete anything.")

    if __name__ == "__main__":
        main()
    """).replace("__NAME__", name).replace("__DESC__", desc).replace("__FOCUS__", focus)

    readme = f"# {name}\n\n{desc}\n\n## Focus\n{focus}\n\n## Inspired by\n" + ("\n".join(f"- {s}" for s in snippets) if snippets else "- local knowledge") + "\n\n## Quick start\n- python main.py\n- review the dry-run output\n"
    return {"main.py": main, "README.md": readme, "project_manifest.json": json.dumps({"type": "file_tool", "name": name, "description": desc, "focus": focus, "snippets": snippets, "features": ["scan", "dry-run", "categorize"]}, indent=2)}


def template_notes_app(name, desc, focus, snippets):
    main = dedent("""
    from __future__ import annotations

    import json
    from datetime import datetime
    from pathlib import Path

    APP_NAME = "__NAME__"
    DESCRIPTION = "__DESC__"
    FOCUS = "__FOCUS__"
    DATA = Path(__file__).resolve().parent / "notes.json"

    def load():
        if DATA.exists():
            try:
                return json.loads(DATA.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"notes": []}

    def save(state):
        DATA.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_note(text):
        state = load()
        state.setdefault("notes", []).append({"text": text, "time": datetime.now().isoformat(timespec="seconds")})
        state["notes"] = state["notes"][-200:]
        save(state)

    def search(term):
        state = load()
        term = term.lower().strip()
        if not term:
            return []
        return [n for n in state.get("notes", []) if term in str(n.get("text", "")).lower()]

    def main():
        state = load()
        state.setdefault("notes", []).append({"text": "hello from SOAR", "time": datetime.now().isoformat(timespec="seconds")})
        state["notes"] = state["notes"][-200:]
        save(state)
        print(APP_NAME)
        print(DESCRIPTION)
        print("focus:", FOCUS)
        print("notes:", len(state["notes"]))
        print("searchable:", "yes")

    if __name__ == "__main__":
        main()
    """).replace("__NAME__", name).replace("__DESC__", desc).replace("__FOCUS__", focus)

    readme = f"# {name}\n\n{desc}\n\n## Focus\n{focus}\n\n## Inspired by\n" + ("\n".join(f"- {s}" for s in snippets) if snippets else "- local knowledge") + "\n\n## Quick start\n- python main.py\n"
    return {"main.py": main, "README.md": readme, "project_manifest.json": json.dumps({"type": "notes_app", "name": name, "description": desc, "focus": focus, "snippets": snippets, "features": ["search", "notes", "timestamps"]}, indent=2)}


def template_data_tool(name, desc, focus, snippets):
    main = dedent("""
    from __future__ import annotations

    import csv
    import json
    from collections import Counter
    from pathlib import Path

    APP_NAME = "__NAME__"
    DESCRIPTION = "__DESC__"
    FOCUS = "__FOCUS__"

    def summarize_json(path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            print("keys:", len(data))
            for key, value in list(data.items())[:20]:
                print(f"- {key}: {type(value).__name__}")
        elif isinstance(data, list):
            print("items:", len(data))
            counts = Counter(type(x).__name__ for x in data)
            for k, v in counts.items():
                print(f"- {k}: {v}")

    def summarize_csv(path: Path):
        with path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        print("rows:", len(rows))
        if rows:
            print("columns:", len(rows[0]))
            print("header:", rows[0])

    def main():
        print(APP_NAME)
        print(DESCRIPTION)
        print("focus:", FOCUS)
        print("ready for csv/json summary reports")

    if __name__ == "__main__":
        main()
    """).replace("__NAME__", name).replace("__DESC__", desc).replace("__FOCUS__", focus)

    readme = f"# {name}\n\n{desc}\n\n## Focus\n{focus}\n\n## Inspired by\n" + ("\n".join(f"- {s}" for s in snippets) if snippets else "- local knowledge") + "\n\n## Quick start\n- import the module and call summarize_json / summarize_csv\n"
    return {"main.py": main, "README.md": readme, "project_manifest.json": json.dumps({"type": "data_tool", "name": name, "description": desc, "focus": focus, "snippets": snippets, "features": ["csv", "json", "summary"]}, indent=2)}


def template_launcher(name, desc, focus, snippets):
    main = dedent("""
    from __future__ import annotations

    import json
    from pathlib import Path

    APP_NAME = "__NAME__"
    DESCRIPTION = "__DESC__"
    FOCUS = "__FOCUS__"
    HISTORY = Path(__file__).resolve().parent / "launcher_history.json"

    def load():
        if HISTORY.exists():
            try:
                return json.loads(HISTORY.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"opens": []}

    def save(state):
        HISTORY.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    def main():
        state = load()
        state.setdefault("opens", []).append({"app": APP_NAME, "focus": FOCUS})
        state["opens"] = state["opens"][-100:]
        save(state)
        print(APP_NAME)
        print(DESCRIPTION)
        print("focus:", FOCUS)
        print("launcher ready")

    if __name__ == "__main__":
        main()
    """).replace("__NAME__", name).replace("__DESC__", desc).replace("__FOCUS__", focus)

    readme = f"# {name}\n\n{desc}\n\n## Focus\n{focus}\n\n## Inspired by\n" + ("\n".join(f"- {s}" for s in snippets) if snippets else "- local knowledge") + "\n"
    return {"main.py": main, "README.md": readme, "project_manifest.json": json.dumps({"type": "launcher", "name": name, "description": desc, "focus": focus, "snippets": snippets}, indent=2)}


def template_mini_game(name, desc, focus, snippets):
    main = dedent("""
    from __future__ import annotations

    import random

    APP_NAME = "__NAME__"
    DESCRIPTION = "__DESC__"
    FOCUS = "__FOCUS__"

    def main():
        target = random.randint(1, 20)
        tries = 0
        print(APP_NAME)
        print(DESCRIPTION)
        print("guess a number 1 to 20")
        while True:
            tries += 1
            guess = input("> ").strip()
            if guess.lower() in ("quit", "exit"):
                print("bye")
                break
            if not guess.isdigit():
                print("enter a number")
                continue
            value = int(guess)
            if value == target:
                print("you won in", tries, "tries")
                print("focus:", FOCUS)
                break
            print("too", "low" if value < target else "high")

    if __name__ == "__main__":
        main()
    """).replace("__NAME__", name).replace("__DESC__", desc).replace("__FOCUS__", focus)

    readme = f"# {name}\n\n{desc}\n\n## Focus\n{focus}\n\n## Inspired by\n" + ("\n".join(f"- {s}" for s in snippets) if snippets else "- local knowledge") + "\n"
    return {"main.py": main, "README.md": readme, "project_manifest.json": json.dumps({"type": "mini_game", "name": name, "description": desc, "focus": focus, "snippets": snippets}, indent=2)}


def render_template(template, name, desc, focus, snippets):
    templates = {
        "python_cli": template_python_cli,
        "web_app": template_web_app,
        "api_service": template_api_service,
        "mini_game": template_mini_game,
        "file_tool": template_file_tool,
        "notes_app": template_notes_app,
        "data_tool": template_data_tool,
        "launcher": template_launcher,
    }
    return templates.get(template, template_python_cli)(name, desc, focus, snippets)


def validate_python_files(files):
    for rel_path, content in files.items():
        if str(rel_path).lower().endswith(".py"):
            ast.parse(str(content))


def build_spec(state, reason="manual trigger"):
    goal = goal_text(state)
    goal_words = set(goal_keywords(goal))
    best = None
    recent = list(state.get("project_history", []))[-DEDUP_RECENT_WINDOW:]

    for attempt in range(6):
        avoid_template = recent[-1]["template"] if recent and isinstance(recent[-1], dict) else None
        template = choose_template(
            state,
            project_importance_score(state, {"template": "", "focus": reason, "description": reason, "goal": goal}),
            goal=goal,
            avoid_template=avoid_template,
        )

        if attempt and recent:
            last_templates = [x.get("template") for x in recent[-3:] if isinstance(x, dict)]
            if last_templates and template == last_templates[-1]:
                template = choose_template(state, 30, goal=goal, avoid_template=template)

        avoid_words = set()
        for item in recent[-5:]:
            if not isinstance(item, dict):
                continue
            avoid_words.update(goal_keywords(item.get("name", "")))
            avoid_words.update(goal_keywords(item.get("focus", "")))

        focus = derive_focus(state, template, goal=goal, avoid_words=avoid_words)
        if goal_words and random.random() < 0.5:
            focus = random.choice(sorted(goal_words))
        name = readable_project_name(template, focus, goal=goal)
        desc = build_description(template, focus, goal=goal)

        similarity, hit = dedupe_similarity(state, name, focus, template=template, goal=goal)
        raw_score = project_importance_score(state, {"template": template, "focus": focus, "description": desc, "goal": goal})

        penalty = 0
        if similarity >= DEDUP_HARD:
            penalty = 45
        elif similarity >= DEDUP_HIGH:
            penalty = 20
        elif similarity >= 0.75:
            penalty = 8

        final_score = max(0, raw_score - penalty)

        library = state.get("web_library", []) or []
        sampled = random.sample(library, k=min(len(library), random.randint(1, 4))) if library else []
        snippets = [str(item.get("title") or item.get("source") or "web code")[:120] for item in sampled]

        candidate = {
            "template": template,
            "project_name": name,
            "description": desc,
            "focus": focus,
            "goal": goal,
            "files": render_template(template, name, desc, focus, snippets),
            "commands": [
                {"name": "status", "trigger": "status", "purpose": "show current state"},
                {"name": "new file", "trigger": "new file", "purpose": "generate a batch of projects"},
                {"name": "sync", "trigger": "sync", "purpose": "refresh web cache"},
                {"name": "open", "trigger": "open", "purpose": "open projects folder"},
            ],
            "snippet_refs": snippets,
            "reason": reason,
            "dedupe_similarity": similarity,
            "dedupe_hit": hit.get("name") if isinstance(hit, dict) else None,
            "raw_score": raw_score,
            "score": final_score,
            "tier": importance_label(final_score),
        }

        if template in ("python_cli", "notes_app", "launcher"):
            candidate["commands"].append({"name": "learn", "trigger": "learn", "purpose": "store a memory note"})

        if best is None or candidate["score"] > best["score"]:
            best = candidate

        if similarity < DEDUP_HIGH and final_score >= 0:
            break

    return best


def write_project(spec):
    folder = unique_folder_name(spec["project_name"], AUTOCODE_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    validate_python_files(spec.get("files", {}))

    for rel_path, content in spec.get("files", {}).items():
        path = folder / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content), encoding="utf-8")

    manifest = {
        "project_name": spec.get("project_name"),
        "template": spec.get("template"),
        "description": spec.get("description"),
        "focus": spec.get("focus"),
        "goal": spec.get("goal", ""),
        "reason": spec.get("reason"),
        "snippet_refs": spec.get("snippet_refs", []),
        "tier": spec.get("tier"),
        "score": spec.get("score"),
        "dedupe_similarity": spec.get("dedupe_similarity"),
        "created_at": datetime.now().isoformat(),
    }
    (folder / "soar_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    GENERATED_COMMANDS_JSON.write_text(json.dumps({"generated_at": datetime.now().isoformat(), "commands": spec.get("commands", [])}, indent=2, ensure_ascii=False), encoding="utf-8")
    return folder


def tier_marker(folder, tier):
    if tier == "keep":
        (folder / ".keep").write_text("protected from deletion\n", encoding="utf-8")
    elif tier == "promote":
        (folder / ".promote").write_text("expand later\n", encoding="utf-8")
    elif tier == "trash":
        (folder / ".trash").write_text("low quality\n", encoding="utf-8")


def move_to_trash(folder):
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    target = unique_folder_name(folder.name, TRASH_DIR)
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    shutil.move(str(folder), str(target))
    return target


def evolve_project(folder, spec):
    tier = spec.get("tier")
    score = int(spec.get("score", 0))
    if tier != "promote" and score < PROMOTE_CUTOFF:
        return folder

    template = spec.get("template")
    focus = spec.get("focus", "")
    name = spec.get("project_name", "Project")

    expansions = {
        "python_cli": {
            "modules/plugin_system.py": dedent(f"""
            from __future__ import annotations

            PLUGIN_NAME = {json.dumps(name)}
            FOCUS = {json.dumps(focus)}

            def describe():
                return {{
                    "name": PLUGIN_NAME,
                    "focus": FOCUS,
                    "capabilities": ["load", "extend", "inspect"]
                }}
            """),
            "modules/health.py": dedent("""
            from __future__ import annotations

            def health():
                return {"ok": True, "status": "ready"}
            """),
        },
        "web_app": {
            "modules/state_store.js": dedent(f"""
            export function loadState() {{
              try {{
                return JSON.parse(localStorage.getItem("soar_state") || "{{}}");
              }} catch {{
                return {{}};
              }}
            }}

            export function saveState(state) {{
              localStorage.setItem("soar_state", JSON.stringify(state));
            }}
            """),
            "docs/ux_notes.md": f"# UX Notes\n\n- Focus: {focus}\n- Improve layout, search, and local persistence.\n",
        },
        "api_service": {
            "modules/client.py": dedent("""
            from __future__ import annotations
            import json
            import urllib.request

            def get_json(url: str):
                with urllib.request.urlopen(url) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            """),
            "tests/test_smoke.py": dedent("""
            def test_smoke():
                assert True
            """),
        },
        "file_tool": {
            "modules/rules.py": dedent("""
            from __future__ import annotations

            def should_keep(path: str) -> bool:
                return True
            """),
            "notes/expansion.md": f"Expansion target: {focus}\n",
        },
        "notes_app": {
            "modules/search_index.py": dedent("""
            from __future__ import annotations

            def index_notes(notes):
                return [str(n.get("text", "")).lower() for n in notes]
            """),
            "notes/expansion.md": f"Expansion target: {focus}\n",
        },
        "data_tool": {
            "modules/pipeline.py": dedent("""
            from __future__ import annotations

            def pipeline(data):
                return data
            """),
            "docs/analysis.md": f"Focus: {focus}\n",
        },
        "launcher": {
            "modules/registry.py": dedent("""
            from __future__ import annotations

            def registry():
                return {}
            """),
            "docs/expansion.md": f"Focus: {focus}\n",
        },
    }

    extra = expansions.get(template, {
        "modules/extension.py": f"# Expansion for {name}\n# Focus: {focus}\n",
        "docs/expansion.md": f"Focus: {focus}\n",
    })

    for rel_path, content in extra.items():
        path = folder / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    manifest_path = folder / "soar_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        manifest = {}
    manifest["evolved"] = True
    manifest["evolved_at"] = datetime.now().isoformat()
    manifest["evolution_modules"] = list(extra.keys())
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    readme = folder / "README.md"
    try:
        old = readme.read_text(encoding="utf-8")
    except Exception:
        old = ""
    enhancement = "\n## Expansion\n\nThis project was automatically promoted and expanded with extra modules.\n"
    if enhancement.strip() not in old:
        readme.write_text(old + enhancement, encoding="utf-8")

    return folder


def learn_from_project(state, spec, folder, importance_score=None):
    state["run_count"] = int(state.get("run_count", 0)) + 1
    state["last_run"] = datetime.now().isoformat()
    state["last_project"] = str(folder)

    recent = state.get("recent_projects", [])
    recent.append(folder.name)
    state["recent_projects"] = recent[-MAX_RECENT:]

    history = state.get("project_history", [])
    history.append({
        "time": datetime.now().isoformat(),
        "name": spec.get("project_name"),
        "template": spec.get("template"),
        "focus": spec.get("focus"),
        "goal": spec.get("goal", ""),
        "folder": str(folder),
        "importance_score": importance_score,
        "tier": spec.get("tier"),
        "dedupe_similarity": spec.get("dedupe_similarity"),
    })
    state["project_history"] = history[-200:]

    template = spec.get("template")
    if template:
        weights = state.get("template_weights", {})
        weights[template] = int(weights.get(template, 1)) + 1

        if importance_score is not None:
            if importance_score >= PROMOTE_CUTOFF:
                for key, bump in SERIOUS_TEMPLATE_BIAS.items():
                    weights[key] = int(weights.get(key, 1)) + bump
            elif importance_score <= 25:
                for key, bump in TOY_TEMPLATE_BIAS.items():
                    weights[key] = int(weights.get(key, 1)) + bump

        state["template_weights"] = weights

        stats = state.get("template_stats", {})
        stats[template] = int(stats.get(template, 0)) + 1
        state["template_stats"] = stats

    hits = state.get("command_hits", {})
    for cmd in spec.get("commands", []):
        trigger = str(cmd.get("trigger", "")).strip().lower()
        if trigger:
            hits[trigger] = int(hits.get(trigger, 0)) + 1
    state["command_hits"] = hits

    memory = state.get("memory", [])
    memory.append(f"created {spec.get('project_name')} using {spec.get('template')} in {folder.name}")
    if spec.get("focus"):
        memory.append(f"focus: {spec.get('focus')}")
    if spec.get("goal"):
        memory.append(f"goal: {spec.get('goal')}")
    if importance_score is not None:
        memory.append(f"importance score: {importance_score}/100")
    if spec.get("tier"):
        memory.append(f"tier: {spec.get('tier')}")
    state["memory"] = memory[-MAX_MEMORY:]
    return state


def trim_state(state):
    state["recent_projects"] = state.get("recent_projects", [])[-MAX_RECENT:]
    state["memory"] = state.get("memory", [])[-MAX_MEMORY:]
    state["web_library"] = state.get("web_library", [])[-MAX_SNIPPETS:]
    state["project_history"] = state.get("project_history", [])[-200:]
    return state


def load_optional_extension():
    global SOAR_AUTOCODE_TWO
    path = SOAR_AUTOCODE_TWO_PATH
    if not path.exists():
        SOAR_AUTOCODE_TWO = None
        return None
    try:
        spec = importlib.util.spec_from_file_location("soar_autocodetwo", str(path))
        if spec is None or spec.loader is None:
            SOAR_AUTOCODE_TWO = None
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        SOAR_AUTOCODE_TWO = module
        log(f"loaded extension: {path.name}")
        return module
    except Exception as e:
        SOAR_AUTOCODE_TWO = None
        log(f"extension load failed: {e}")
        return None


def extension_has(name):
    return SOAR_AUTOCODE_TWO is not None and hasattr(SOAR_AUTOCODE_TWO, name)


def call_extension(name, *args, **kwargs):
    if not extension_has(name):
        return None
    try:
        return getattr(SOAR_AUTOCODE_TWO, name)(*args, **kwargs)
    except Exception as e:
        log(f"extension hook {name} failed: {e}")
        return None


def think_before_build(spec, score):
    delay = think_delay_for_importance(score)
    label = importance_label(score)
    focus = spec.get("focus", "project")
    log(f"thinking about {focus} ({label}) for {delay:.2f}s")
    time.sleep(delay)


def finalize_project(folder, spec):
    tier = spec.get("tier", "normal")
    if tier == "trash":
        folder = move_to_trash(folder)
        tier_marker(folder, tier)
        return folder
    tier_marker(folder, tier)
    if tier == "keep":
        log(f"protected project: {folder.name}")
    elif tier == "promote":
        folder = evolve_project(folder, spec)
        log(f"promoted and expanded: {folder.name}")
    return folder


def run_python_script(script_path: Path, cwd: Path, timeout: int = AUTO_RUN_TIMEOUT):
    try:
        proc = subprocess.Popen(
            [sys.executable, str(script_path)],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            out, _ = proc.communicate(timeout=timeout)
            rc = proc.returncode
            if out and out.strip():
                log(f"run output ({script_path.name}):\n{out.rstrip()}")
            log(f"finished run: {script_path} (exit {rc})")
            return rc
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                out, _ = proc.communicate(timeout=3)
            except Exception:
                out = ""
            if out and out.strip():
                log(f"partial output ({script_path.name}):\n{out.rstrip()}")
            log(f"timed out after {timeout}s: {script_path}")
            return -1
    except Exception as e:
        log(f"run failed for {script_path}: {e}")
        return -1


def open_folder(path: Path):
    if not AUTO_OPEN_FOLDERS:
        return
    try:
        if os.name == "nt":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as e:
        log(f"could not open folder: {e}")


def open_web_file(path: Path):
    if not AUTO_OPEN_WEB_APPS:
        return False
    try:
        import webbrowser
        webbrowser.open(path.resolve().as_uri())
        return True
    except Exception as e:
        log(f"could not open web file: {e}")
        return False


def run_generated_project(folder, spec):
    if not AUTO_RUN_GENERATED:
        return

    template = spec.get("template")

    # Only run code quietly in the background; do not open folders or windows.
    if template in {"python_cli", "notes_app", "data_tool", "file_tool", "launcher"}:
        main_py = folder / "main.py"
        if main_py.exists():
            run_python_script(main_py, cwd=folder, timeout=AUTO_RUN_TIMEOUT)
        return

    if template == "mini_game":
        if os.getenv("SOAR_RUN_MINI_GAME", "0") == "1":
            main_py = folder / "main.py"
            if main_py.exists():
                run_python_script(main_py, cwd=folder, timeout=AUTO_RUN_TIMEOUT)
        return

    if template == "web_app":
        index = folder / "index.html"
        if index.exists():
            # Headless mode: validate that the project exists, but do not open a browser.
            log(f"web app generated (headless): {index}")
            if AUTO_OPEN_WEB_APPS:
                open_web_file(index)
        return

    if template == "api_service":
        app_py = folder / "app.py"
        if app_py.exists():
            rc = subprocess.run([sys.executable, "-m", "py_compile", str(app_py)], cwd=str(folder), capture_output=True, text=True)
            if rc.stdout.strip():
                log(rc.stdout.rstrip())
            if rc.stderr.strip():
                log(rc.stderr.rstrip())
            log(f"validated api service: {app_py} (exit {rc.returncode})")
            if AUTO_START_API_SERVICES:
                subprocess.Popen([sys.executable, str(app_py)], cwd=str(folder))
        return


def run_cycle(reason="manual trigger"):
    state = load_state()
    try:
        call_extension("before_cycle", state, reason)
        if state.get("settings", {}).get("use_web_when_online", True) and online_available():
            state, new_items = sync_sources(state, force=False)
            if new_items:
                log(f"synced {len(new_items)} snippets")

        seed_spec = build_spec(state, reason=reason)
        batch_size, score = choose_batch_size(state, seed_spec)
        label = importance_label(score)
        log(f"batch plan: {batch_size} folders | importance {score}/100 | {label}")

        for index in range(batch_size):
            if stop_event.is_set():
                break

            spec = seed_spec if index == 0 else build_spec(state, reason=f"{reason} batch step {index + 1}/{batch_size}")
            project_score = int(spec.get("score", project_importance_score(state, spec)))
            spec["tier"] = importance_label(project_score)

            think_before_build(spec, project_score)

            folder = write_project(spec)
            folder = finalize_project(folder, spec)
            call_extension("after_project", state, spec, folder)
            state = learn_from_project(state, spec, folder, importance_score=project_score)
            state = trim_state(state)
            save_state(state)
            log(f"finished project {index + 1}/{batch_size}: {folder}")

            # Generate quietly in the background after creation.
            if AUTO_RUN_GENERATED:
                run_generated_project(folder, spec)

        call_extension("after_cycle", state, reason)
    except Exception as e:
        log(f"ERROR: {e}")
        traceback.print_exc()


def open_projects_folder():
    open_folder(AUTOCODE_DIR)


def show_status():
    state = load_state()
    print(f"app: {APP_NAME} {VERSION}")
    print(f"runs: {state.get('run_count', 0)}")
    print(f"projects dir: {PROJECTS_DIR}")
    print(f"autocode dir: {AUTOCODE_DIR}")
    print(f"trash dir: {TRASH_DIR}")
    print(f"last project: {state.get('last_project') or 'none'}")
    print(f"memory notes: {len(state.get('memory', []))}")
    print(f"cached snippets: {len(state.get('web_library', []))}")
    print(f"goal mode: {goal_text(state) or 'off'}")
    print(f"recent: {', '.join(state.get('recent_projects', [])[-5:]) or 'none'}")
    print(f"source message: {state.get('source_status', {}).get('message', 'idle')}")
    print(f"headless mode: yes")


def show_ideas():
    state = load_state()
    weights = state.get("template_weights", {}) or {}
    ranked = sorted(weights.items(), key=lambda item: item[1], reverse=True)
    print("top templates:")
    for name, weight in ranked[:6]:
        print(f"- {name}: {weight}")
    print("learned themes:")
    pattern = state.get("pattern_index", {}) or {}
    for item in (pattern.get("keywords", []) or [])[:10]:
        print(f"- {item}")


def set_goal(text):
    state = load_state()
    text = str(text or "").strip()
    state.setdefault("settings", {})["goal_mode"] = text
    save_state(state)
    log(f"goal mode set to: {text or 'off'}")


def add_source(url):
    url = str(url).strip()
    if not url:
        return
    state = load_state()
    sources = state.get("sources", [])
    if url not in sources:
        sources.append(url)
    state["sources"] = sources
    save_state(state)
    write_sources(state)
    log(f"added source: {url}")


def list_sources():
    state = load_state()
    urls = read_sources(state)
    if not urls:
        print("no sources configured")
        return
    for i, url in enumerate(urls, 1):
        print(f"{i}. {url}")


def show_help():
    print("commands: status | new file | sync | open | learn <note> | ideas | goal <text> | goal clear | addsource <url> | sources | exit")
    print("new file: creates a batch of 1-3 folders per cycle")
    print("generated projects run in the background quietly")


def input_loop():
    show_help()
    while not stop_event.is_set():
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            stop_event.set()
            break

        if not raw:
            continue

        lower = raw.lower()

        if lower == "exit":
            stop_event.set()
            break
        if lower == "status":
            show_status()
            continue
        if lower == "new file":
            manual_event.set()
            continue
        if lower == "sync":
            sync_event.set()
            continue
        if lower == "open":
            open_projects_folder()
            continue
        if lower == "ideas":
            show_ideas()
            continue
        if lower == "sources":
            list_sources()
            continue
        if lower.startswith("addsource "):
            add_source(raw.split(" ", 1)[1].strip())
            continue
        if lower.startswith("goal "):
            arg = raw.split(" ", 1)[1].strip()
            if arg.lower() in {"clear", "off", "none"}:
                set_goal("")
            else:
                set_goal(arg)
            continue
        if lower == "goal":
            print("current goal:", goal_text(load_state()) or "off")
            continue
        if lower.startswith("learn "):
            text = raw.split(" ", 1)[1].strip()
            if text:
                state = load_state()
                memory = state.get("memory", [])
                memory.append(text)
                state["memory"] = memory[-MAX_MEMORY:]
                save_state(state)
                log(f"saved note: {text}")
            continue

        print("unknown command")


def auto_loop():
    interval = max(10, int(os.getenv("SOAR_INTERVAL_SECONDS", str(AUTO_INTERVAL))))
    while not stop_event.is_set():
        if manual_event.is_set():
            manual_event.clear()
            run_cycle("manual new file request")
        else:
            run_cycle("scheduled autonomous upgrade")
        if stop_event.wait(interval):
            break


def sync_loop():
    interval = max(60, int(os.getenv("SOAR_SYNC_SECONDS", str(SYNC_INTERVAL))))
    while not stop_event.is_set():
        if sync_event.is_set():
            sync_event.clear()
            sync_sources(load_state(), force=True)
        else:
            state = load_state()
            if state.get("settings", {}).get("sync_on_start", True) or online_available():
                sync_sources(state, force=False)
        if stop_event.wait(interval):
            break


def runner_loop():
    # Background execution worker in case you later switch run_generated_project to queue jobs.
    while not stop_event.is_set():
        time.sleep(0.5)


def banner():
    print(f"{APP_NAME} {VERSION}")
    print(f"projects folder: {PROJECTS_DIR}")
    print(f"autocode folder: {AUTOCODE_DIR}")
    print(f"trash folder: {TRASH_DIR}")
    print(f"batch size: {MIN_BATCH_FOLDERS} to {MAX_BATCH_FOLDERS} folders per cycle")
    print(f"auto interval: {max(10, int(os.getenv('SOAR_INTERVAL_SECONDS', str(AUTO_INTERVAL))))} seconds")
    print(f"sync interval: {max(60, int(os.getenv('SOAR_SYNC_SECONDS', str(SYNC_INTERVAL))))} seconds")
    print(f"online: {'yes' if online_available() else 'no, using cache when possible'}")
    print(f"headless mode: yes")
    print()


def main():
    ensure_dirs()
    load_optional_extension()
    banner()

    state = load_state()
    if state.get("settings", {}).get("sync_on_start", True):
        sync_sources(state, force=False)

    threads = [
        threading.Thread(target=auto_loop, daemon=True),
        threading.Thread(target=sync_loop, daemon=True),
        threading.Thread(target=input_loop, daemon=True),
        threading.Thread(target=runner_loop, daemon=True),
    ]
    for thread in threads:
        thread.start()

    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        try:
            save_state(trim_state(load_state()))
        except Exception:
            pass
        log("shutting down")


if __name__ == "__main__":
    main()

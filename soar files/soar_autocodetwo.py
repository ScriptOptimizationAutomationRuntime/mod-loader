#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

APP_NAME = "SOAR AUTOCODE ADVANCED"
VERSION = "1.00.4"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "soar_data"
AUTOCODE_DIR = BASE_DIR / "Autocode"
STATE_FILE = DATA_DIR / "autocode_state.json"
CACHE_FILE = DATA_DIR / "autocode_cache.json"
LOG_FILE = DATA_DIR / "autocode_log.txt"
LEARNING_FILE = DATA_DIR / "autocode_learnings.txt"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
LOCK = threading.RLock()

MAX_MEMORY = 250
MAX_HINTS = 120
MAX_RECENT = 60
MAX_PROJECTS = 80
MAX_TOPICS = 250
MAX_LEARNINGS = 300
MAX_PATTERNS = 120
MAX_ACTIONS = 200
MAX_RUN_HISTORY = 120
MAX_DECISIONS = 120
MAX_EVENTS = 400

SMART_WORDS = {
    "smart",
    "smarter",
    "brain",
    "memory",
    "learn",
    "adaptive",
    "refactor",
    "optimize",
    "analyze",
    "inspect",
    "search",
    "index",
    "planner",
    "tracker",
    "dashboard",
    "workflow",
    "assistant",
    "builder",
    "automation",
    "system",
    "utility",
    "tool",
    "tools",
    "engine",
    "core",
    "pipeline",
    "sync",
    "report",
    "reporting",
    "monitor",
    "validator",
    "organizer",
    "launcher",
    "api",
    "service",
    "data",
    "web",
    "cli",
    "python",
    "notes",
    "file",
    "architecture",
    "project",
    "runtime",
    "scheduler",
    "orchestrator",
    "plugin",
    "plugins",
    "state",
    "cache",
    "indexer",
    "searcher",
    "scanner",
}

SERIOUS_TEMPLATES = {
    "python_cli",
    "file_tool",
    "data_tool",
    "api_service",
    "notes_app",
    "launcher",
    "web_app",
    "automation_core",
}

TEMPLATE_FAMILIES = {
    "python_cli": "core",
    "web_app": "ui",
    "api_service": "network",
    "file_tool": "files",
    "notes_app": "knowledge",
    "data_tool": "analytics",
    "launcher": "ui",
    "mini_game": "creative",
    "automation_core": "core",
    "plugin_host": "core",
}

TEMPLATE_ALIASES = {
    "cli": "python_cli",
    "script": "python_cli",
    "terminal": "python_cli",
    "dashboard": "web_app",
    "portal": "web_app",
    "panel": "web_app",
    "service": "api_service",
    "server": "api_service",
    "endpoint": "api_service",
    "organizer": "file_tool",
    "cleanup": "file_tool",
    "notes": "notes_app",
    "memory": "notes_app",
    "journal": "notes_app",
    "report": "data_tool",
    "analytics": "data_tool",
    "launcher": "launcher",
    "menu": "launcher",
    "hub": "launcher",
    "automation": "automation_core",
    "system": "automation_core",
    "plugin": "plugin_host",
    "plugins": "plugin_host",
}

GENERIC_FOCUS = [
    "project core",
    "workflow engine",
    "control center",
    "task runner",
    "smart automation",
    "data bridge",
    "memory layer",
    "insight board",
    "file organizer",
    "utility hub",
]

TEMPLATE_FOCUS = {
    "python_cli": ["automation runner", "task orchestrator", "project core", "workflow engine", "command tool"],
    "web_app": ["dashboard", "control panel", "workspace", "status board", "portal"],
    "api_service": ["json api", "local service", "endpoint kit", "sync service", "bridge"],
    "file_tool": ["file organizer", "batch helper", "sorter", "archive manager", "cleanup tool"],
    "notes_app": ["memory vault", "note search", "journal", "recall engine", "capture tool"],
    "data_tool": ["report engine", "csv helper", "analysis tool", "insight view", "data pipeline"],
    "launcher": ["command hub", "starter board", "app launcher", "quick menu", "workspace hub"],
    "mini_game": ["arcade loop", "micro challenge", "quick game", "test arena", "playground"],
    "automation_core": ["system orchestrator", "automation brain", "task core", "decision engine", "runtime core"],
    "plugin_host": ["plugin hub", "extension host", "module bridge", "addin manager", "integration center"],
}

NAME_PREFIXES = {
    "python_cli": ["Core", "Prime", "Nova", "Signal", "Pulse", "Atlas"],
    "web_app": ["Studio", "Panel", "Vista", "Orbit", "Atlas", "Canvas"],
    "api_service": ["Gateway", "Bridge", "Relay", "Nexus", "Link", "Transit"],
    "file_tool": ["File", "Folder", "Clean", "Sort", "Sweep", "Stack"],
    "notes_app": ["Memory", "Notes", "Journal", "Recall", "Vault", "Archive"],
    "data_tool": ["Data", "Report", "Chart", "Grid", "Insight", "Metric"],
    "launcher": ["Launch", "Hub", "Dock", "Board", "Menu", "Beam"],
    "mini_game": ["Arcade", "Quest", "Dash", "Loop", "Sprint", "Play"],
    "automation_core": ["Orch", "Astra", "Vector", "Engine", "Pulse", "Helix"],
    "plugin_host": ["Plugin", "Addon", "Module", "Bridge", "Hub", "Dock"],
}

NAME_NOUNS = {
    "python_cli": ["Engine", "System", "Builder", "Assistant", "Tool", "Core"],
    "web_app": ["Dashboard", "Studio", "Center", "Space", "Board", "View"],
    "api_service": ["API", "Service", "Link", "Node", "Engine", "Relay"],
    "mini_game": ["Game", "Run", "Quest", "Match", "Play", "Loop"],
    "file_tool": ["Manager", "Helper", "Organizer", "Tool", "Cleaner", "Sorter"],
    "notes_app": ["Vault", "Keeper", "Hub", "Pad", "Book", "Index"],
    "data_tool": ["Analyzer", "Reporter", "Tool", "Lab", "View", "Board"],
    "launcher": ["Hub", "Board", "Dock", "Panel", "Starter", "Menu"],
    "automation_core": ["Orchestrator", "Runtime", "Engine", "Core", "Director", "Brain"],
    "plugin_host": ["Host", "Hub", "Manager", "Bridge", "Shell", "Center"],
}

EVENT_KIND = {
    "memory": "memory",
    "hint": "hint",
    "decision": "decision",
    "project": "project",
    "learning": "learning",
    "analysis": "analysis",
    "cache": "cache",
    "cycle": "cycle",
    "error": "error",
    "status": "status",
}


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


@dataclass
class MemoryItem:
    time: str
    kind: str
    text: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectSpec:
    template: str = "python_cli"
    focus: str = "project core"
    goal: str = ""
    description: str = ""
    project_name: str = ""
    tags: list[str] = field(default_factory=list)
    priority: int = 50
    source: str = "manual"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectDecision:
    template: str
    focus: str
    project_name: str
    score: int
    reasons: list[str] = field(default_factory=list)
    family: str = "core"
    priority: int = 50
    created_at: str = field(default_factory=lambda: now())


@dataclass
class LearningItem:
    id: str
    title: str
    source: str
    keywords: list[str]
    reason: str
    time: str
    digest: str = ""
    importance: int = 1
    kind: str = "web"
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeStatus:
    app: str
    version: str
    runs: int
    last_cycle: Optional[str]
    last_project: Optional[str]
    recent_projects: list[str]
    top_templates: list[tuple[str, int]]
    top_web_topics: list[tuple[str, int]]
    hints: list[dict[str, Any]]
    memory_count: int
    learning_count: int
    event_count: int
    state_file: str
    learning_file: str
    cache_file: str



def now() -> str:
    return datetime.now().isoformat(timespec="seconds")



def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)



def _safe_json_load(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return default
        return json.loads(raw)
    except Exception:
        return default



def _safe_json_dump(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)



def _safe_append(path: Path, lines: Iterable[str]) -> None:
    text_lines = [str(line).rstrip() for line in lines if str(line).rstrip()]
    if not text_lines:
        return
    with path.open("a", encoding="utf-8") as f:
        for line in text_lines:
            f.write(line + "\n")



def stamp_message(message: str) -> str:
    return f"[{now()}] {message}"



def log(message: str, severity: Severity = Severity.low) -> None:
    ensure_dirs()
    line = stamp_message(f"{severity.value.upper()}: {message}")
    try:
        _safe_append(LOG_FILE, [line])
    except Exception:
        pass
    print(line)



def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()



def default_state() -> dict[str, Any]:
    return {
        "run_count": 0,
        "recent_reasons": [],
        "recent_projects": [],
        "memory": [],
        "hints": [],
        "web_topics": {},
        "learned_snippet_ids": [],
        "web_learnings": [],
        "template_bias": {
            "python_cli": 4,
            "web_app": 3,
            "api_service": 4,
            "file_tool": 4,
            "notes_app": 3,
            "data_tool": 4,
            "launcher": 3,
            "mini_game": 1,
            "automation_core": 5,
            "plugin_host": 3,
        },
        "focus_history": [],
        "project_scores": [],
        "decision_history": [],
        "run_history": [],
        "event_log": [],
        "pattern_hits": {},
        "action_history": [],
        "last_cycle": None,
        "last_project": None,
        "settings": {
            "prefer_serious": True,
            "quiet_mode": True,
            "auto_hint": True,
            "memory_limit": MAX_MEMORY,
            "deterministic_seed": None,
            "avoid_repeat_focus": True,
            "learn_from_web": True,
            "prefer_core_templates": True,
            "bias_memory": True,
        },
    }



def load_state() -> dict[str, Any]:
    ensure_dirs()
    with LOCK:
        data = _safe_json_load(STATE_FILE, default_state())
        if not isinstance(data, dict):
            return default_state()
        state = default_state()
        state.update(data)
        for key, value in default_state().items():
            state.setdefault(key, value)
        if not isinstance(state.get("settings"), dict):
            state["settings"] = default_state()["settings"]
        return trim_state(state)



def save_state(state: dict[str, Any]) -> None:
    ensure_dirs()
    with LOCK:
        _safe_json_dump(STATE_FILE, trim_state(state))



def trim_state(state: dict[str, Any]) -> dict[str, Any]:
    state["memory"] = list(state.get("memory", []) or [])[-MAX_MEMORY:]
    state["hints"] = list(state.get("hints", []) or [])[-MAX_HINTS:]
    state["recent_reasons"] = list(state.get("recent_reasons", []) or [])[-MAX_RECENT:]
    state["recent_projects"] = list(state.get("recent_projects", []) or [])[-MAX_RECENT:]
    state["focus_history"] = list(state.get("focus_history", []) or [])[-MAX_RECENT:]
    state["project_scores"] = list(state.get("project_scores", []) or [])[-MAX_PROJECTS:]
    state["decision_history"] = list(state.get("decision_history", []) or [])[-MAX_DECISIONS:]
    state["run_history"] = list(state.get("run_history", []) or [])[-MAX_RUN_HISTORY:]
    state["event_log"] = list(state.get("event_log", []) or [])[-MAX_EVENTS:]
    state["action_history"] = list(state.get("action_history", []) or [])[-MAX_ACTIONS:]
    state["web_learnings"] = list(state.get("web_learnings", []) or [])[-MAX_LEARNINGS:]
    state["learned_snippet_ids"] = list(state.get("learned_snippet_ids", []) or [])[-1000:]
    topics = state.get("web_topics", {}) or {}
    if isinstance(topics, dict):
        state["web_topics"] = dict(sorted(topics.items(), key=lambda x: x[1], reverse=True)[:MAX_TOPICS])
    patterns = state.get("pattern_hits", {}) or {}
    if isinstance(patterns, dict):
        state["pattern_hits"] = dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:MAX_PATTERNS])
    return state



def save_cache(payload: dict[str, Any]) -> None:
    ensure_dirs()
    try:
        _safe_json_dump(CACHE_FILE, payload)
    except Exception:
        pass



def append_learning_text(lines: Iterable[str]) -> None:
    ensure_dirs()
    try:
        _safe_append(LEARNING_FILE, lines)
    except Exception:
        pass



def normalize_text(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"[^A-Za-z0-9\s._/-]+", " ", text)
    text = re.sub(r"[\s_/-]+", " ", text).strip()
    return text



def keywords(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-z0-9_]{3,}", str(text).lower())}



def split_words(text: str) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    return [w for w in text.split() if w]



def canonical_template(value: str) -> str:
    value = str(value or "").strip().lower()
    if not value:
        return "python_cli"
    if value in TEMPLATE_ALIASES:
        return TEMPLATE_ALIASES[value]
    if value in TEMPLATE_FAMILIES:
        return value
    for key in TEMPLATE_FAMILIES:
        if key in value:
            return key
    return "python_cli"



def _contains_any(text: str, terms: Iterable[str]) -> bool:
    low = text.lower()
    return any(term in low for term in terms)



def score_text_for_seriousness(text: str) -> int:
    words = keywords(text)
    score = 0
    for w in words:
        if w in SMART_WORDS:
            score += 3
    if words.intersection({"automation", "assistant", "builder", "pipeline", "workflow", "analyze", "validator", "monitor", "orchestrator", "runtime"}):
        score += 7
    if words.intersection({"game", "pong", "snake", "quiz", "clicker", "arcade", "toy"}):
        score -= 8
    if words.intersection({"security", "defense", "audit", "backup", "sync", "index", "search"}):
        score += 4
    return score



def severity_from_score(score: int) -> Severity:
    if score >= 85:
        return Severity.critical
    if score >= 65:
        return Severity.high
    if score >= 40:
        return Severity.medium
    return Severity.low



def weighted_pick(weights: dict[str, int], seed: Optional[str] = None) -> str:
    items = [(k, max(1, int(v))) for k, v in (weights or {}).items() if str(k).strip()]
    if not items:
        return "python_cli"
    if seed is not None:
        rng = random.Random(seed)
        total = sum(v for _, v in items)
        roll = rng.uniform(0, total)
        upto = 0.0
        for key, value in items:
            upto += value
            if upto >= roll:
                return key
        return items[0][0]
    total = sum(v for _, v in items)
    roll = random.uniform(0, total)
    upto = 0.0
    for key, value in items:
        upto += value
        if upto >= roll:
            return key
    return items[0][0]



def merge_dict_counter(target: dict[str, int], source: dict[str, int], multiplier: int = 1) -> dict[str, int]:
    out = dict(target or {})
    for key, value in (source or {}).items():
        out[key] = int(out.get(key, 0)) + int(value) * multiplier
    return out



def make_note(kind: str, text: str, **meta: Any) -> dict[str, Any]:
    item = MemoryItem(time=now(), kind=kind, text=str(text), meta=dict(meta))
    return asdict(item)



def add_event(kind: str, message: str, **meta: Any) -> dict[str, Any]:
    state = load_state()
    event = {
        "time": now(),
        "kind": kind,
        "message": str(message),
        "meta": dict(meta),
    }
    state.setdefault("event_log", []).append(event)
    save_state(state)
    return event



def remember(text: str, kind: str = "memory", **meta: Any) -> dict[str, Any]:
    state = load_state()
    item = make_note(kind, text, **meta)
    state.setdefault("memory", []).append(item)
    state.setdefault("event_log", []).append({"time": now(), "kind": "memory", "message": str(text), "meta": dict(meta)})
    save_state(state)
    return item



def log_hint(text: str, **meta: Any) -> dict[str, Any]:
    state = load_state()
    item = make_note("hint", text, **meta)
    state.setdefault("hints", []).append(item)
    state.setdefault("event_log", []).append({"time": now(), "kind": "hint", "message": str(text), "meta": dict(meta)})
    save_state(state)
    save_cache({"last_hint": item, "hint_count": len(state.get("hints", []))})
    return item



def _item_digest(item: dict[str, Any]) -> str:
    raw = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
    return sha1_text(raw)



def summarize_web_item(item: dict[str, Any]) -> str:
    title = str(item.get("title") or item.get("source") or "web item").strip()
    source = str(item.get("source") or item.get("domain") or "").strip()
    text = str(item.get("text") or item.get("summary") or "").strip()
    profile = item.get("profile") or {}
    kws = list(profile.get("keywords", []) or [])[:10]
    snippet = re.sub(r"\s+", " ", text[:220]).strip()
    if len(text) > 220:
        snippet += "..."
    head = f"{title} [{source}]" if source else title
    if kws:
        return f"- {head} | topics: {', '.join(kws)} | {snippet}"
    return f"- {head} | {snippet}"



def build_short_learning_line(item: dict[str, Any]) -> str:
    title = str(item.get("title") or item.get("source") or "web item").strip()
    keywords_part = ", ".join(list((item.get("profile") or {}).get("keywords", []) or [])[:6])
    return f"{title} | {keywords_part or 'no keywords'}"



def update_topic_counts(topic_state: dict[str, int], kws: Iterable[str], weight: int = 1) -> dict[str, int]:
    out = dict(topic_state or {})
    for kw in kws:
        kw = str(kw).strip().lower()
        if not kw:
            continue
        out[kw] = int(out.get(kw, 0)) + max(1, int(weight))
    return out



def ingest_web_library(state: dict[str, Any], reason: str = "") -> dict[str, Any]:
    library = list(state.get("web_library", []) or [])
    seen_ids = set(state.get("learned_snippet_ids", []) or [])
    web_topics: dict[str, int] = dict(state.get("web_topics", {}) or {})
    learned_records: list[dict[str, Any]] = []
    log_lines: list[str] = []

    for item in library:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or "").strip()
        if not sid:
            sid = _item_digest(item)
        if sid in seen_ids:
            continue
        seen_ids.add(sid)

        profile = item.get("profile") or {}
        kws = [str(k).lower() for k in (profile.get("keywords", []) or []) if str(k).strip()]
        weight = int(profile.get("weight", 1) or 1)
        importance = max(1, min(10, int(profile.get("importance", 1) or 1)))
        web_topics = update_topic_counts(web_topics, kws, weight)

        learned = LearningItem(
            id=sid,
            title=str(item.get("title") or item.get("source") or "web item"),
            source=str(item.get("source") or item.get("domain") or ""),
            keywords=kws[:20],
            reason=reason,
            time=now(),
            digest=_item_digest(item),
            importance=importance,
            kind="web",
            meta={k: v for k, v in item.items() if k not in {"title", "source", "profile", "text"}},
        )
        learned_records.append(asdict(learned))
        log_lines.append(f"[{learned.time}] {learned.title} | {learned.source} | {', '.join(learned.keywords) or 'no keywords'}")
        log_lines.append(summarize_web_item(item))

    if learned_records:
        state.setdefault("web_learnings", []).extend(learned_records)
        state["web_learnings"] = state.get("web_learnings", [])[-MAX_LEARNINGS:]
        append_learning_text([f"[{now()}] learned from web sync ({reason or 'cycle'})"] + log_lines + [""])
        state["event_log"] = state.get("event_log", []) + [{"time": now(), "kind": "learning", "message": f"ingested {len(learned_records)} web items", "meta": {"reason": reason}}]

    state["learned_snippet_ids"] = list(seen_ids)[-1000:]
    state["web_topics"] = dict(sorted(web_topics.items(), key=lambda x: x[1], reverse=True)[:MAX_TOPICS])
    return state



def ingest_external_web_items(items: list[dict[str, Any]], reason: str = "external") -> None:
    state = load_state()
    state["web_library"] = list(items or [])
    state = ingest_web_library(state, reason=reason)
    save_state(state)
    save_cache({
        "updated_at": now(),
        "web_topics": state.get("web_topics", {}),
        "web_learnings": state.get("web_learnings", [])[-40:],
    })



def detect_patterns(text: str) -> list[str]:
    text = str(text or "")
    low = text.lower()
    patterns: list[str] = []
    checks = {
        "path": [r"[A-Za-z]:\\", r"/[^\s]+/[^\s]+", r"\\\\"],
        "python": [r"\bdef\b", r"\bclass\b", r"\bimport\b", r"\bfrom\b"],
        "json": [r"\{.*:\s*.*\}", r"\[[^\]]+\]"],
        "codeblock": [r"```", r"\bfunction\b", r"\breturn\b"],
        "automation": [r"\bworkflow\b", r"\borchestrator\b", r"\bautocode\b", r"\bruntime\b"],
        "notes": [r"\bremember\b", r"\bmemory\b", r"\bnote\b", r"\bjournal\b"],
        "analysis": [r"\banalyze\b", r"\binspect\b", r"\bmetric\b", r"\breport\b"],
    }
    for name, regs in checks.items():
        if any(re.search(rx, low, flags=re.IGNORECASE | re.DOTALL) for rx in regs):
            patterns.append(name)
    return patterns



def update_pattern_hits(state: dict[str, Any], patterns: Iterable[str]) -> dict[str, Any]:
    counts = dict(state.get("pattern_hits", {}) or {})
    for pat in patterns:
        counts[pat] = int(counts.get(pat, 0)) + 1
    state["pattern_hits"] = counts
    return state



def infer_project_priority(spec: ProjectSpec | dict[str, Any]) -> int:
    if isinstance(spec, dict):
        spec = ProjectSpec(**{**asdict(ProjectSpec()), **spec})
    template = canonical_template(spec.template)
    focus = str(spec.focus).strip().lower()
    desc = str(spec.description).strip().lower()
    goal = str(spec.goal).strip().lower()
    tags = [str(x).lower() for x in spec.tags]
    text = f"{template} {focus} {desc} {goal} {' '.join(tags)}"

    score = 40
    reasons: list[str] = []

    if template in SERIOUS_TEMPLATES:
        score += 8
        reasons.append("serious template")

    score += max(-10, min(15, score_text_for_seriousness(text)))
    if _contains_any(goal, ("build", "make", "create", "tool", "system", "workflow", "automation", "dashboard", "engine", "core")):
        score += 8
        reasons.append("goal suggests utility")
    if _contains_any(goal, ("game", "toy", "demo", "practice", "sandbox")):
        score -= 10
        reasons.append("goal suggests lighter work")
    if _contains_any(desc, ("robust", "secure", "fast", "reliable", "scalable", "pipeline", "production")):
        score += 5
        reasons.append("production language")
    if tags:
        if any(t in {"automation", "utility", "data", "analysis", "tool"} for t in tags):
            score += 5
            reasons.append("useful tags")
        if any(t in {"game", "fun", "toy"} for t in tags):
            score -= 6
            reasons.append("playful tags")

    memory_count = len(load_state().get("memory", []))
    score += min(10, memory_count // 20)
    score += min(5, len(spec.metadata or {}) // 2)
    score += min(5, len(spec.focus.split()))
    return max(0, min(100, score))



def _apply_bias_rules(bias: dict[str, int], text: str, weight: int = 1) -> dict[str, int]:
    low = text.lower()
    if _contains_any(low, ("automation", "workflow", "system", "engine", "assistant", "runtime", "orchestrator")):
        for key in ("python_cli", "api_service", "file_tool", "data_tool", "launcher", "automation_core"):
            bias[key] = int(bias.get(key, 1)) + 2 * weight
    if _contains_any(low, ("notes", "memory", "journal", "remember", "vault", "recall")):
        bias["notes_app"] = int(bias.get("notes_app", 1)) + 4 * weight
    if _contains_any(low, ("dashboard", "web", "ui", "panel", "portal", "view")):
        bias["web_app"] = int(bias.get("web_app", 1)) + 3 * weight
    if _contains_any(low, ("game", "snake", "pong", "quiz", "toy", "play")):
        bias["mini_game"] = int(bias.get("mini_game", 1)) + 3 * weight
    if _contains_any(low, ("file", "folder", "organize", "cleanup", "archive", "sort")):
        bias["file_tool"] = int(bias.get("file_tool", 1)) + 3 * weight
    if _contains_any(low, ("data", "csv", "sqlite", "report", "analysis", "chart", "metric")):
        bias["data_tool"] = int(bias.get("data_tool", 1)) + 3 * weight
    if _contains_any(low, ("api", "endpoint", "json", "server", "request", "response")):
        bias["api_service"] = int(bias.get("api_service", 1)) + 3 * weight
    if _contains_any(low, ("launch", "launcher", "menu", "dock", "hub", "starter")):
        bias["launcher"] = int(bias.get("launcher", 1)) + 3 * weight
    return bias



def choose_better_template(state: dict[str, Any], current_template: str, spec: ProjectSpec | dict[str, Any]) -> str:
    if isinstance(spec, dict):
        spec = ProjectSpec(**{**asdict(ProjectSpec()), **spec})
    template = canonical_template(spec.template or current_template)
    bias = dict(state.get("template_bias", {}) or {})
    seed = state.get("settings", {}).get("deterministic_seed")
    combined_text = f"{template} {spec.focus} {spec.description} {spec.goal} {' '.join(spec.tags)}"
    bias = _apply_bias_rules(bias, combined_text, 1)

    for topic, count in list((state.get("web_topics", {}) or {}).items())[:30]:
        topic = str(topic).lower()
        bump = max(1, int(count) // 2)
        if topic in {"python", "cli", "script", "def", "import", "module"}:
            bias["python_cli"] = int(bias.get("python_cli", 1)) + bump
        elif topic in {"api", "endpoint", "json", "server", "request", "response"}:
            bias["api_service"] = int(bias.get("api_service", 1)) + bump
        elif topic in {"data", "csv", "sqlite", "table", "report", "analysis", "chart", "metric"}:
            bias["data_tool"] = int(bias.get("data_tool", 1)) + bump
        elif topic in {"web", "html", "css", "javascript", "ui", "dom", "browser"}:
            bias["web_app"] = int(bias.get("web_app", 1)) + bump
        elif topic in {"note", "notes", "memory", "journal", "search", "vault", "recall"}:
            bias["notes_app"] = int(bias.get("notes_app", 1)) + bump
        elif topic in {"file", "folder", "organize", "cleanup", "path", "archive"}:
            bias["file_tool"] = int(bias.get("file_tool", 1)) + bump
        elif topic in {"launch", "launcher", "menu", "dock", "hub"}:
            bias["launcher"] = int(bias.get("launcher", 1)) + bump
        elif topic in {"automation", "workflow", "engine", "orchestrator", "runtime"}:
            bias["automation_core"] = int(bias.get("automation_core", 1)) + bump

    if template in bias:
        bias[template] = max(1, int(bias[template]) - 1)
    if state.get("settings", {}).get("prefer_serious", True):
        for key in SERIOUS_TEMPLATES:
            bias[key] = int(bias.get(key, 1)) + 1
    if state.get("settings", {}).get("prefer_core_templates", True):
        for key in ("python_cli", "api_service", "file_tool", "data_tool", "automation_core", "launcher"):
            bias[key] = int(bias.get(key, 1)) + 1

    choice = weighted_pick(bias, seed=seed if isinstance(seed, str) else None)
    return canonical_template(choice)



def suggest_focus(state: dict[str, Any], spec: ProjectSpec | dict[str, Any]) -> str:
    if isinstance(spec, dict):
        spec = ProjectSpec(**{**asdict(ProjectSpec()), **spec})
    template = canonical_template(spec.template)
    goal = normalize_text(spec.goal).lower()
    focus = normalize_text(spec.focus).lower()
    recent = [normalize_text(x).lower() for x in (state.get("focus_history", []) or [])[-12:]]
    avoid = set(recent) if state.get("settings", {}).get("avoid_repeat_focus", True) else set()

    candidates: list[str] = []
    if goal:
        candidates.append(goal)
    if focus:
        candidates.append(focus)

    candidates.extend(TEMPLATE_FOCUS.get(template, GENERIC_FOCUS))

    learned_topics = state.get("web_topics", {}) or {}
    if learned_topics:
        top_topic = sorted(learned_topics.items(), key=lambda x: x[1], reverse=True)[0][0]
        candidates.insert(0, top_topic)

    cleaned: list[str] = []
    for item in candidates:
        item = normalize_text(item).lower()
        if not item:
            continue
        if item in avoid:
            continue
        cleaned.append(item)

    if not cleaned:
        cleaned = ["project core", "utility", "system"]

    seed = state.get("settings", {}).get("deterministic_seed")
    if isinstance(seed, str) and seed:
        rng = random.Random(seed + template + goal + focus)
        return rng.choice(cleaned)
    return random.choice(cleaned)



def suggest_project_name(template: str, focus: str, goal: str = "") -> str:
    template = canonical_template(template)
    focus_words = split_words(focus)[:2] or ["Project"]
    goal_words = split_words(goal)[:2]
    prefix = random.choice(NAME_PREFIXES.get(template, ["Core"]))
    noun = random.choice(NAME_NOUNS.get(template, ["Project"]))
    middle_words = goal_words or focus_words
    middle = " ".join(word.capitalize() for word in middle_words)
    name = f"{prefix} {middle} {noun}".strip()
    name = re.sub(r"\s+", " ", name)
    return name[:48]



def unique_name(base: str, existing: Iterable[str]) -> str:
    base = normalize_text(base) or "Project"
    existing_set = {normalize_text(x).lower() for x in existing}
    candidate = base
    idx = 2
    while candidate.lower() in existing_set:
        candidate = f"{base} {idx}"
        idx += 1
    return candidate



def maybe_prefix(text: str, prefix: str, chance: float = 0.25) -> str:
    text = str(text or "").strip()
    if not text:
        return text
    if random.random() < chance:
        return f"{prefix} {text}"
    return text



def build_project_spec(
    template: str = "python_cli",
    focus: str = "",
    goal: str = "",
    description: str = "",
    project_name: str = "",
    tags: Optional[list[str]] = None,
    source: str = "manual",
    metadata: Optional[dict[str, Any]] = None,
) -> ProjectSpec:
    spec = ProjectSpec(
        template=canonical_template(template),
        focus=normalize_text(focus) or "project core",
        goal=normalize_text(goal),
        description=normalize_text(description),
        project_name=normalize_text(project_name),
        tags=[normalize_text(t).lower() for t in (tags or []) if normalize_text(t)],
        source=source,
        metadata=dict(metadata or {}),
    )
    if not spec.project_name:
        spec.project_name = suggest_project_name(spec.template, spec.focus, spec.goal)
    spec.priority = infer_project_priority(spec)
    return spec



def plan_template_switch(state: dict[str, Any], spec: ProjectSpec) -> ProjectDecision:
    template = choose_better_template(state, spec.template, spec)
    focus = suggest_focus(state, ProjectSpec(template=template, focus=spec.focus, goal=spec.goal, description=spec.description, tags=spec.tags))
    name = spec.project_name or suggest_project_name(template, focus, spec.goal)
    score = infer_project_priority(ProjectSpec(template=template, focus=focus, goal=spec.goal, description=spec.description, project_name=name, tags=spec.tags, source=spec.source, metadata=spec.metadata))
    family = TEMPLATE_FAMILIES.get(template, "core")
    reasons = []
    if template != spec.template:
        reasons.append(f"template moved from {spec.template} to {template}")
    if state.get("web_topics"):
        top_topic = sorted(state.get("web_topics", {}).items(), key=lambda x: x[1], reverse=True)[0][0]
        reasons.append(f"topic pressure from {top_topic}")
    if score >= 75:
        reasons.append("strong utility fit")
    elif score <= 25:
        reasons.append("low priority exploratory fit")
    return ProjectDecision(template=template, focus=focus, project_name=name, score=score, reasons=reasons, family=family, priority=score)



def append_project_score(state: dict[str, Any], spec: ProjectSpec, score: int, folder: Optional[Path] = None) -> None:
    state.setdefault("project_scores", []).append({
        "time": now(),
        "project": spec.project_name,
        "folder": str(folder) if folder else None,
        "template": spec.template,
        "focus": spec.focus,
        "goal": spec.goal,
        "priority": score,
        "tags": spec.tags,
        "source": spec.source,
    })
    state["project_scores"] = state.get("project_scores", [])[-MAX_PROJECTS:]



def tune_bias_from_project(state: dict[str, Any], spec: ProjectSpec, score: int) -> dict[str, Any]:
    bias = dict(state.get("template_bias", {}) or {})
    template = canonical_template(spec.template)
    bias[template] = int(bias.get(template, 1)) + 1
    if score >= 80:
        for key in ("python_cli", "api_service", "data_tool", "file_tool", "notes_app", "automation_core"):
            bias[key] = int(bias.get(key, 1)) + 1
    elif score <= 25:
        bias["mini_game"] = int(bias.get("mini_game", 1)) + 1
    if spec.tags:
        bias = _apply_bias_rules(bias, " ".join(spec.tags), 1)
    return bias



def after_project(state: dict[str, Any] | None, spec: ProjectSpec | dict[str, Any], folder: Path | str) -> dict[str, Any]:
    try:
        current = load_state()
        if isinstance(spec, dict):
            spec = build_project_spec(**spec)
        if isinstance(folder, str):
            folder = Path(folder)
        score = infer_project_priority(spec)
        current.setdefault("recent_projects", []).append(folder.name)
        current["recent_projects"] = current.get("recent_projects", [])[-MAX_RECENT:]
        current.setdefault("focus_history", []).append(spec.focus)
        current["focus_history"] = current.get("focus_history", [])[-MAX_RECENT:]
        current["last_project"] = str(folder)
        append_project_score(current, spec, score, folder)
        current["template_bias"] = tune_bias_from_project(current, spec, score)

        if score >= 80:
            hint = f"Promoted project: {spec.project_name} ({spec.template}) focusing on {spec.focus}"
        elif score <= 25:
            hint = f"Low-priority project: {spec.project_name} ({spec.template}) focusing on {spec.focus}"
        else:
            hint = f"Project complete: {spec.project_name} ({spec.template}) focusing on {spec.focus}"

        current.setdefault("hints", []).append(make_note("project_hint", hint, folder=str(folder), score=score, template=spec.template))
        current.setdefault("decision_history", []).append({
            "time": now(),
            "kind": "after_project",
            "project": spec.project_name,
            "template": spec.template,
            "focus": spec.focus,
            "goal": spec.goal,
            "score": score,
            "folder": str(folder),
        })
        current["decision_history"] = current.get("decision_history", [])[-MAX_DECISIONS:]
        current["event_log"] = current.get("event_log", []) + [{"time": now(), "kind": "project", "message": f"completed {spec.project_name}", "meta": {"template": spec.template, "score": score}}]
        save_state(current)
        save_cache({
            "updated_at": now(),
            "last_project": str(folder),
            "template_bias": current.get("template_bias", {}),
            "project_scores": current.get("project_scores", [])[-20:],
        })
        if current.get("settings", {}).get("auto_hint", True):
            if spec.goal:
                log_hint(f"Goal influence detected: {spec.goal}", template=spec.template, project=spec.project_name)
            if score >= 80:
                log_hint("Next cycle should stay serious and utility-focused.", project=spec.project_name, score=score)
            elif score <= 25:
                log_hint("Next cycle can reduce repetition by shifting templates.", project=spec.project_name, score=score)
        log(f"after_project: {spec.project_name} | template={spec.template} | score={score}")
        return current
    except Exception as e:
        log(f"after_project error: {e}", Severity.high)
        return load_state()



def before_cycle(state: dict[str, Any] | None, reason: str) -> dict[str, Any]:
    try:
        current = load_state()
        current.setdefault("recent_reasons", []).append(str(reason))
        current["recent_reasons"] = current.get("recent_reasons", [])[-MAX_RECENT:]
        current["last_cycle"] = now()
        current.setdefault("run_history", []).append({"time": now(), "reason": str(reason)})
        current["run_history"] = current.get("run_history", [])[-MAX_RUN_HISTORY:]
        current.setdefault("event_log", []).append({"time": now(), "kind": "cycle", "message": f"before {reason}", "meta": {}})
        save_state(current)
        log(f"before_cycle: {reason}")
        return current
    except Exception as e:
        log(f"before_cycle error: {e}", Severity.high)
        return load_state()



def _compress_memory_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in entries[-MAX_MEMORY:]:
        if isinstance(item, dict):
            out.append(item)
        else:
            out.append(make_note("memory", str(item)))
    return out[-MAX_MEMORY:]



def after_cycle(state: dict[str, Any] | None, reason: str) -> dict[str, Any]:
    try:
        current = load_state()
        current["run_count"] = int(current.get("run_count", 0)) + 1
        current["last_cycle"] = now()
        current["memory"] = _compress_memory_entries(list(current.get("memory", []) or []))
        current["hints"] = list(current.get("hints", []) or [])[-MAX_HINTS:]
        current["event_log"] = current.get("event_log", []) + [{"time": now(), "kind": "cycle", "message": f"after {reason}", "meta": {"run_count": current["run_count"]}}]
        save_state(current)
        save_cache({
            "updated_at": now(),
            "recent_projects": current.get("recent_projects", []),
            "template_bias": current.get("template_bias", {}),
            "project_scores": current.get("project_scores", [])[-20:],
            "hints": current.get("hints", [])[-20:],
            "web_topics": current.get("web_topics", {}),
            "pattern_hits": current.get("pattern_hits", {}),
        })
        if current.get("web_topics"):
            top = sorted(current.get("web_topics", {}).items(), key=lambda x: x[1], reverse=True)[:5]
            top_str = ", ".join(f"{k}:{v}" for k, v in top)
            log_hint(f"Latest learned web topics: {top_str}")
        log(f"after_cycle: {reason}")
        return current
    except Exception as e:
        log(f"after_cycle error: {e}", Severity.high)
        return load_state()



def _recommend_from_topics(topics: dict[str, int]) -> Optional[str]:
    if not topics:
        return None
    top = sorted(topics.items(), key=lambda x: x[1], reverse=True)[0][0].lower()
    if top in {"python", "cli", "script", "def", "import", "module"}:
        return "python_cli"
    if top in {"api", "endpoint", "json", "server", "request", "response"}:
        return "api_service"
    if top in {"data", "csv", "sqlite", "report", "analysis", "chart", "metric"}:
        return "data_tool"
    if top in {"web", "html", "css", "javascript", "ui", "dom", "browser"}:
        return "web_app"
    if top in {"note", "notes", "memory", "journal", "search", "vault", "recall"}:
        return "notes_app"
    if top in {"file", "folder", "organize", "cleanup", "path", "archive"}:
        return "file_tool"
    if top in {"launch", "launcher", "menu", "dock", "hub"}:
        return "launcher"
    if top in {"automation", "workflow", "runtime", "engine", "orchestrator"}:
        return "automation_core"
    if top in {"plugin", "plugins", "extension", "addon"}:
        return "plugin_host"
    return None



def suggest_next_step(goal: str = "") -> str:
    state = load_state()
    biases = dict(state.get("template_bias", {}) or {})
    seed = state.get("settings", {}).get("deterministic_seed")
    goal = normalize_text(goal).lower()

    recommended: Optional[str] = None
    serious = sorted([(k, v) for k, v in biases.items() if k in SERIOUS_TEMPLATES], key=lambda x: x[1], reverse=True)
    if serious:
        recommended = serious[0][0]
    else:
        recommended = weighted_pick(biases or {"python_cli": 1}, seed=seed if isinstance(seed, str) else None)

    if goal:
        if _contains_any(goal, ("dashboard", "panel", "portal", "ui", "visual")):
            recommended = "web_app"
        elif _contains_any(goal, ("memory", "notes", "journal", "remember", "recall")):
            recommended = "notes_app"
        elif _contains_any(goal, ("api", "server", "endpoint", "json", "network")):
            recommended = "api_service"
        elif _contains_any(goal, ("data", "csv", "report", "analysis", "chart")):
            recommended = "data_tool"
        elif _contains_any(goal, ("file", "folder", "organize", "cleanup", "archive")):
            recommended = "file_tool"
        elif _contains_any(goal, ("launcher", "hub", "menu", "dock", "starter")):
            recommended = "launcher"
        elif _contains_any(goal, ("automation", "system", "runtime", "orchestrator")):
            recommended = "automation_core"
        elif _contains_any(goal, ("plugin", "addon", "extension", "module")):
            recommended = "plugin_host"

    topic_recommendation = _recommend_from_topics(state.get("web_topics", {}) or {})
    if topic_recommendation:
        recommended = topic_recommendation

    focus = suggest_focus(state, ProjectSpec(template=recommended, goal=goal, focus=goal or ""))
    name = suggest_project_name(recommended, focus, goal)
    score = infer_project_priority(ProjectSpec(template=recommended, focus=focus, goal=goal, project_name=name))
    vibe = severity_from_score(score)
    return f"Try a {recommended} focused on {focus}. Project name: {name}. Priority: {score}/100 ({vibe.value})."



def analyze_text(text: str) -> dict[str, Any]:
    text = str(text or "")
    words = keywords(text)
    patterns = detect_patterns(text)
    serious = score_text_for_seriousness(text)
    return {
        "words": sorted(words)[:40],
        "seriousness": serious,
        "severity": severity_from_score(max(0, serious + 40)).value,
        "length": len(text),
        "word_count": len(split_words(text)),
        "has_code_signals": any(k in words for k in {"def", "class", "import", "function", "module", "state", "return"}),
        "patterns": patterns,
        "digest": sha1_text(text),
    }



def feed_memory(text: str, kind: str = "memory", **meta: Any) -> dict[str, Any]:
    return remember(text, kind=kind, **meta)



def make_hint(text: str, **meta: Any) -> dict[str, Any]:
    return log_hint(text, **meta)



def record_action(action: str, **meta: Any) -> dict[str, Any]:
    state = load_state()
    item = {
        "time": now(),
        "action": str(action),
        "meta": dict(meta),
    }
    state.setdefault("action_history", []).append(item)
    state["action_history"] = state.get("action_history", [])[-MAX_ACTIONS:]
    state.setdefault("event_log", []).append({"time": now(), "kind": "analysis", "message": action, "meta": dict(meta)})
    save_state(state)
    return item



def note_decision(decision: ProjectDecision, extra: Optional[dict[str, Any]] = None) -> None:
    state = load_state()
    payload = asdict(decision)
    if extra:
        payload["extra"] = dict(extra)
    state.setdefault("decision_history", []).append(payload)
    state["decision_history"] = state.get("decision_history", [])[-MAX_DECISIONS:]
    state.setdefault("event_log", []).append({"time": now(), "kind": "decision", "message": decision.project_name, "meta": payload})
    save_state(state)



def plan_project(
    template: str = "python_cli",
    focus: str = "",
    goal: str = "",
    description: str = "",
    project_name: str = "",
    tags: Optional[list[str]] = None,
    source: str = "manual",
    metadata: Optional[dict[str, Any]] = None,
) -> ProjectDecision:
    state = load_state()
    spec = build_project_spec(template=template, focus=focus, goal=goal, description=description, project_name=project_name, tags=tags, source=source, metadata=metadata)
    decided_template = choose_better_template(state, spec.template, spec)
    decided_focus = suggest_focus(state, ProjectSpec(template=decided_template, goal=spec.goal, focus=spec.focus, description=spec.description, tags=spec.tags, source=spec.source, metadata=spec.metadata))
    decided_name = spec.project_name or suggest_project_name(decided_template, decided_focus, spec.goal)
    score = infer_project_priority(ProjectSpec(template=decided_template, focus=decided_focus, goal=spec.goal, description=spec.description, project_name=decided_name, tags=spec.tags, source=spec.source, metadata=spec.metadata))
    family = TEMPLATE_FAMILIES.get(decided_template, "core")
    reasons = []
    if decided_template != spec.template:
        reasons.append(f"template adjusted to {decided_template}")
    if decided_focus != spec.focus:
        reasons.append(f"focus refined to {decided_focus}")
    if score >= 70:
        reasons.append("high utility priority")
    if state.get("web_topics"):
        top = sorted(state.get("web_topics", {}).items(), key=lambda x: x[1], reverse=True)[0][0]
        reasons.append(f"learned topic: {top}")
    decision = ProjectDecision(template=decided_template, focus=decided_focus, project_name=decided_name, score=score, reasons=reasons, family=family, priority=score)
    note_decision(decision, extra={"source": source, "goal": spec.goal, "description": spec.description, "tags": spec.tags})
    append_project_score(state, ProjectSpec(template=decided_template, focus=decided_focus, goal=spec.goal, description=spec.description, project_name=decided_name, tags=spec.tags, source=source, metadata=spec.metadata), score)
    state["template_bias"] = tune_bias_from_project(state, ProjectSpec(template=decided_template, focus=decided_focus, goal=spec.goal, description=spec.description, project_name=decided_name, tags=spec.tags, source=source, metadata=spec.metadata), score)
    save_state(state)
    return decision



def export_snapshot() -> dict[str, Any]:
    state = load_state()
    snapshot = {
        "exported_at": now(),
        "state": trim_state(state),
        "status": asdict(get_extension_status()),
    }
    return snapshot



def save_snapshot() -> Path:
    ensure_dirs()
    path = SNAPSHOT_DIR / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    _safe_json_dump(path, export_snapshot())
    return path



def clear_memory(keep_hints: bool = False) -> None:
    state = load_state()
    state["memory"] = []
    state["web_learnings"] = []
    state["web_topics"] = {}
    state["learned_snippet_ids"] = []
    if not keep_hints:
        state["hints"] = []
    save_state(state)
    log("memory cleared", Severity.medium)



def reset_all() -> None:
    save_state(default_state())
    save_cache({"reset_at": now()})
    log("state reset", Severity.medium)



def get_extension_status() -> RuntimeStatus:
    state = load_state()
    return RuntimeStatus(
        app=APP_NAME,
        version=VERSION,
        runs=int(state.get("run_count", 0)),
        last_cycle=state.get("last_cycle"),
        last_project=state.get("last_project"),
        recent_projects=list(state.get("recent_projects", [])[-10:]),
        top_templates=sorted((state.get("template_bias", {}) or {}).items(), key=lambda x: x[1], reverse=True)[:6],
        top_web_topics=sorted((state.get("web_topics", {}) or {}).items(), key=lambda x: x[1], reverse=True)[:10],
        hints=list(state.get("hints", [])[-10:]),
        memory_count=len(state.get("memory", [])),
        learning_count=len(state.get("web_learnings", [])),
        event_count=len(state.get("event_log", [])),
        state_file=str(STATE_FILE),
        learning_file=str(LEARNING_FILE),
        cache_file=str(CACHE_FILE),
    )



def status_dict() -> dict[str, Any]:
    return asdict(get_extension_status())



def summarize_state() -> dict[str, Any]:
    state = load_state()
    top_templates = sorted((state.get("template_bias", {}) or {}).items(), key=lambda x: x[1], reverse=True)
    top_topics = sorted((state.get("web_topics", {}) or {}).items(), key=lambda x: x[1], reverse=True)
    return {
        "app": APP_NAME,
        "version": VERSION,
        "runs": state.get("run_count", 0),
        "recent_projects": state.get("recent_projects", [])[-10:],
        "top_templates": top_templates[:10],
        "top_topics": top_topics[:10],
        "last_cycle": state.get("last_cycle"),
        "last_project": state.get("last_project"),
        "memory_count": len(state.get("memory", [])),
        "hint_count": len(state.get("hints", [])),
        "learning_count": len(state.get("web_learnings", [])),
        "events": len(state.get("event_log", [])),
    }



def export_summary_text() -> str:
    s = summarize_state()
    lines = [
        f"{s['app']} {s['version']}",
        f"runs: {s['runs']}",
        f"last_cycle: {s['last_cycle']}",
        f"last_project: {s['last_project']}",
        f"memory_count: {s['memory_count']}",
        f"hint_count: {s['hint_count']}",
        f"learning_count: {s['learning_count']}",
        "top_templates:",
    ]
    for k, v in s["top_templates"][:5]:
        lines.append(f"  - {k}: {v}")
    lines.append("top_topics:")
    for k, v in s["top_topics"][:8]:
        lines.append(f"  - {k}: {v}")
    return "\n".join(lines)



def scan_input_for_learning(text: str, source: str = "input") -> dict[str, Any]:
    state = load_state()
    patterns = detect_patterns(text)
    state = update_pattern_hits(state, patterns)
    analysis = analyze_text(text)
    note = {
        "time": now(),
        "source": source,
        "text": text,
        "analysis": analysis,
        "patterns": patterns,
    }
    state.setdefault("event_log", []).append({"time": now(), "kind": "analysis", "message": f"scanned {source}", "meta": {"patterns": patterns, "length": len(text)}})
    state.setdefault("memory", []).append(make_note("analysis", text[:2000], source=source, patterns=patterns, digest=analysis["digest"]))
    save_state(state)
    return note



def learn_from_text_block(text: str, source: str = "text_block", importance: int = 1) -> None:
    info = scan_input_for_learning(text, source=source)
    if info["patterns"]:
        record_action("pattern_detected", source=source, patterns=info["patterns"])
    if importance > 1:
        log_hint(f"High importance input from {source}", source=source, importance=importance)



def build_learning_item_from_web(item: dict[str, Any], reason: str = "web") -> LearningItem:
    profile = item.get("profile") or {}
    kws = [str(k).lower() for k in (profile.get("keywords", []) or []) if str(k).strip()]
    sid = str(item.get("id") or _item_digest(item))
    return LearningItem(
        id=sid,
        title=str(item.get("title") or item.get("source") or "web item"),
        source=str(item.get("source") or item.get("domain") or ""),
        keywords=kws[:20],
        reason=reason,
        time=now(),
        digest=_item_digest(item),
        importance=max(1, min(10, int(profile.get("importance", 1) or 1))),
        kind="web",
        meta={"raw": {k: v for k, v in item.items() if k not in {"profile", "text"}}},
    )



def ingest_web_items(items: list[dict[str, Any]], reason: str = "external") -> dict[str, Any]:
    state = load_state()
    seen_ids = set(state.get("learned_snippet_ids", []) or [])
    web_topics: dict[str, int] = dict(state.get("web_topics", {}) or {})
    new_records: list[dict[str, Any]] = []
    log_lines: list[str] = []

    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        learned = build_learning_item_from_web(raw, reason=reason)
        if learned.id in seen_ids:
            continue
        seen_ids.add(learned.id)
        web_topics = update_topic_counts(web_topics, learned.keywords, learned.importance)
        record = asdict(learned)
        new_records.append(record)
        log_lines.append(f"[{learned.time}] {learned.title} | {learned.source} | {', '.join(learned.keywords) or 'no keywords'}")
        log_lines.append(summarize_web_item(raw))

    if new_records:
        state.setdefault("web_learnings", []).extend(new_records)
        state["web_learnings"] = state.get("web_learnings", [])[-MAX_LEARNINGS:]
        state["event_log"] = state.get("event_log", []) + [{"time": now(), "kind": "learning", "message": f"ingested {len(new_records)} items", "meta": {"reason": reason}}]
        append_learning_text([f"[{now()}] external web learning ({reason})"] + log_lines + [""])

    state["learned_snippet_ids"] = list(seen_ids)[-1000:]
    state["web_topics"] = dict(sorted(web_topics.items(), key=lambda x: x[1], reverse=True)[:MAX_TOPICS])
    save_state(state)
    save_cache({
        "updated_at": now(),
        "web_topics": state.get("web_topics", {}),
        "web_learnings": state.get("web_learnings", [])[-20:],
    })
    return state



def record_web_topic(topic: str, amount: int = 1) -> None:
    state = load_state()
    topic = normalize_text(topic).lower()
    if not topic:
        return
    state["web_topics"] = update_topic_counts(dict(state.get("web_topics", {}) or {}), [topic], amount)
    save_state(state)



def record_web_topics(topics: Iterable[str], amount: int = 1) -> None:
    state = load_state()
    state["web_topics"] = update_topic_counts(dict(state.get("web_topics", {}) or {}), topics, amount)
    save_state(state)



def get_top_topics(limit: int = 10) -> list[tuple[str, int]]:
    state = load_state()
    return sorted((state.get("web_topics", {}) or {}).items(), key=lambda x: x[1], reverse=True)[:limit]



def get_top_templates(limit: int = 10) -> list[tuple[str, int]]:
    state = load_state()
    return sorted((state.get("template_bias", {}) or {}).items(), key=lambda x: x[1], reverse=True)[:limit]



def get_recent_hints(limit: int = 10) -> list[dict[str, Any]]:
    state = load_state()
    return list(state.get("hints", [])[-limit:])



def get_recent_memory(limit: int = 10) -> list[dict[str, Any]]:
    state = load_state()
    return list(state.get("memory", [])[-limit:])



def get_recent_projects(limit: int = 10) -> list[str]:
    state = load_state()
    return list(state.get("recent_projects", [])[-limit:])



def get_recent_events(limit: int = 20) -> list[dict[str, Any]]:
    state = load_state()
    return list(state.get("event_log", [])[-limit:])



def get_decision_history(limit: int = 10) -> list[dict[str, Any]]:
    state = load_state()
    return list(state.get("decision_history", [])[-limit:])



def list_learnings(limit: int = 20) -> list[dict[str, Any]]:
    state = load_state()
    return list(state.get("web_learnings", [])[-limit:])



def register_template(name: str, bias: int = 1) -> None:
    state = load_state()
    name = canonical_template(name)
    bias_map = dict(state.get("template_bias", {}) or {})
    bias_map[name] = int(bias_map.get(name, 1)) + max(1, int(bias))
    state["template_bias"] = bias_map
    save_state(state)
    add_event("status", f"template registered: {name}", bias=bias)



def degrade_template(name: str, amount: int = 1) -> None:
    state = load_state()
    name = canonical_template(name)
    bias_map = dict(state.get("template_bias", {}) or {})
    bias_map[name] = max(1, int(bias_map.get(name, 1)) - max(1, int(amount)))
    state["template_bias"] = bias_map
    save_state(state)
    add_event("status", f"template degraded: {name}", amount=amount)



def recommend_template(goal: str = "", focus: str = "", description: str = "") -> ProjectDecision:
    spec = build_project_spec(goal=goal, focus=focus, description=description)
    state = load_state()
    template = choose_better_template(state, spec.template, spec)
    focus_choice = suggest_focus(state, ProjectSpec(template=template, goal=goal, focus=focus, description=description))
    project_name = suggest_project_name(template, focus_choice, goal)
    score = infer_project_priority(ProjectSpec(template=template, focus=focus_choice, goal=goal, description=description, project_name=project_name))
    decision = ProjectDecision(template=template, focus=focus_choice, project_name=project_name, score=score, reasons=["recommendation"], family=TEMPLATE_FAMILIES.get(template, "core"), priority=score)
    note_decision(decision, extra={"kind": "recommendation"})
    return decision



def build_recommendation_text(goal: str = "", focus: str = "", description: str = "") -> str:
    decision = recommend_template(goal=goal, focus=focus, description=description)
    return f"Try a {decision.template} focused on {decision.focus}. Project name: {decision.project_name}. Priority: {decision.score}/100."



def iterate_learning_from_project(spec: ProjectSpec, notes: Optional[list[str]] = None) -> None:
    state = load_state()
    state.setdefault("focus_history", []).append(spec.focus)
    state["focus_history"] = state.get("focus_history", [])[-MAX_RECENT:]
    if notes:
        for note in notes:
            state.setdefault("memory", []).append(make_note("project_note", note, project=spec.project_name, template=spec.template))
    state["template_bias"] = tune_bias_from_project(state, spec, infer_project_priority(spec))
    save_state(state)



def summarize_project_spec(spec: ProjectSpec) -> dict[str, Any]:
    return {
        "template": canonical_template(spec.template),
        "focus": spec.focus,
        "goal": spec.goal,
        "description": spec.description,
        "project_name": spec.project_name,
        "priority": spec.priority,
        "tags": spec.tags,
        "source": spec.source,
        "metadata": spec.metadata,
    }



def run_cycle(reason: str = "manual") -> dict[str, Any]:
    state = before_cycle(None, reason)
    state = after_cycle(state, reason)
    return state



def cycle_and_plan(
    reason: str = "manual",
    template: str = "python_cli",
    focus: str = "",
    goal: str = "",
    description: str = "",
    project_name: str = "",
    tags: Optional[list[str]] = None,
) -> dict[str, Any]:
    state = before_cycle(None, reason)
    decision = recommend_template(goal=goal, focus=focus, description=description)
    spec = build_project_spec(template=decision.template if template == "python_cli" else template, focus=decision.focus, goal=goal, description=description, project_name=project_name or decision.project_name, tags=tags, source="cycle")
    after_cycle(state, reason)
    return {
        "state": status_dict(),
        "decision": asdict(decision),
        "project": summarize_project_spec(spec),
        "next_step": suggest_next_step(goal=goal),
    }



def maintenance_tick() -> dict[str, Any]:
    state = load_state()
    state = trim_state(state)
    if state.get("settings", {}).get("learn_from_web", True):
        state = ingest_web_library(state, reason="maintenance")
    state["event_log"] = state.get("event_log", []) + [{"time": now(), "kind": "cache", "message": "maintenance tick", "meta": {"runs": state.get("run_count", 0)}}]
    save_state(state)
    save_cache({
        "updated_at": now(),
        "runs": state.get("run_count", 0),
        "top_templates": get_top_templates(10),
        "top_topics": get_top_topics(10),
        "last_cycle": state.get("last_cycle"),
    })
    return summarize_state()



def describe_template(name: str) -> dict[str, Any]:
    name = canonical_template(name)
    return {
        "template": name,
        "family": TEMPLATE_FAMILIES.get(name, "core"),
        "bias": load_state().get("template_bias", {}).get(name, 1),
        "focus_options": TEMPLATE_FOCUS.get(name, GENERIC_FOCUS),
        "name_prefixes": NAME_PREFIXES.get(name, ["Core"]),
        "name_nouns": NAME_NOUNS.get(name, ["Project"]),
    }



def format_status(status: RuntimeStatus | dict[str, Any]) -> str:
    data = asdict(status) if isinstance(status, RuntimeStatus) else dict(status)
    top_templates = data.get("top_templates", [])
    top_topics = data.get("top_web_topics", [])
    lines = [
        f"{data.get('app')} {data.get('version')}",
        f"runs: {data.get('runs')}",
        f"last_cycle: {data.get('last_cycle')}",
        f"last_project: {data.get('last_project')}",
        f"memory_count: {data.get('memory_count')}",
        f"learning_count: {data.get('learning_count')}",
        f"event_count: {data.get('event_count')}",
        "top_templates:",
    ]
    for k, v in top_templates[:5]:
        lines.append(f"  - {k}: {v}")
    lines.append("top_topics:")
    for k, v in top_topics[:8]:
        lines.append(f"  - {k}: {v}")
    return "\n".join(lines)



def format_decision(decision: ProjectDecision) -> str:
    lines = [
        f"template: {decision.template}",
        f"focus: {decision.focus}",
        f"project_name: {decision.project_name}",
        f"score: {decision.score}",
        f"family: {decision.family}",
        f"priority: {decision.priority}",
    ]
    if decision.reasons:
        lines.append("reasons:")
        for reason in decision.reasons[:10]:
            lines.append(f"  - {reason}")
    return "\n".join(lines)



def report_activity(limit: int = 10) -> str:
    state = load_state()
    lines = [
        f"activity report @ {now()}",
        f"runs: {state.get('run_count', 0)}",
        f"memory: {len(state.get('memory', []))}",
        f"hints: {len(state.get('hints', []))}",
        f"projects: {len(state.get('project_scores', []))}",
        f"learnings: {len(state.get('web_learnings', []))}",
        "recent projects:",
    ]
    for p in state.get("recent_projects", [])[-limit:]:
        lines.append(f"  - {p}")
    lines.append("top templates:")
    for k, v in get_top_templates(limit)[:limit]:
        lines.append(f"  - {k}: {v}")
    lines.append("top topics:")
    for k, v in get_top_topics(limit)[:limit]:
        lines.append(f"  - {k}: {v}")
    return "\n".join(lines)



def search_memory(query: str, limit: int = 10) -> list[dict[str, Any]]:
    state = load_state()
    q = normalize_text(query).lower()
    results: list[dict[str, Any]] = []
    for item in reversed(state.get("memory", []) or []):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).lower()
        kind = str(item.get("kind", "")).lower()
        if q in text or q in kind:
            results.append(item)
        if len(results) >= limit:
            break
    return results



def search_hints(query: str, limit: int = 10) -> list[dict[str, Any]]:
    state = load_state()
    q = normalize_text(query).lower()
    results: list[dict[str, Any]] = []
    for item in reversed(state.get("hints", []) or []):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).lower()
        kind = str(item.get("kind", "")).lower()
        if q in text or q in kind:
            results.append(item)
        if len(results) >= limit:
            break
    return results



def search_learnings(query: str, limit: int = 10) -> list[dict[str, Any]]:
    state = load_state()
    q = normalize_text(query).lower()
    results: list[dict[str, Any]] = []
    for item in reversed(state.get("web_learnings", []) or []):
        if not isinstance(item, dict):
            continue
        text = " ".join([str(item.get("title", "")), str(item.get("source", "")), " ".join(item.get("keywords", []) or [])]).lower()
        if q in text:
            results.append(item)
        if len(results) >= limit:
            break
    return results



def smart_hint_for_goal(goal: str) -> str:
    goal = normalize_text(goal).lower()
    if not goal:
        return suggest_next_step()
    if _contains_any(goal, ("dashboard", "panel", "portal", "ui")):
        return "Build a web_app with clear status cards and quick actions."
    if _contains_any(goal, ("memory", "notes", "journal", "remember")):
        return "Build a notes_app with search, tags, and quick capture."
    if _contains_any(goal, ("api", "server", "endpoint", "json")):
        return "Build an api_service with routes, validation, and clean JSON output."
    if _contains_any(goal, ("data", "csv", "report", "analysis")):
        return "Build a data_tool with import, summarize, and export features."
    if _contains_any(goal, ("file", "folder", "organize", "cleanup")):
        return "Build a file_tool for sorting, deduping, and batch renaming."
    if _contains_any(goal, ("automation", "workflow", "system", "orchestrator")):
        return "Build an automation_core that tracks tasks and routes actions."
    if _contains_any(goal, ("plugin", "addon", "extension", "module")):
        return "Build a plugin_host that can register and manage modules."
    return suggest_next_step(goal)



def build_status_payload() -> dict[str, Any]:
    state = load_state()
    return {
        "status": status_dict(),
        "summary": summarize_state(),
        "top_templates": get_top_templates(10),
        "top_topics": get_top_topics(10),
        "recent_hints": get_recent_hints(10),
        "recent_memory": get_recent_memory(10),
        "recent_projects": get_recent_projects(10),
        "recent_events": get_recent_events(10),
        "decision_history": get_decision_history(10),
        "learnings": list_learnings(10),
        "settings": state.get("settings", {}),
    }



def cycle_summary(reason: str = "manual") -> dict[str, Any]:
    state = run_cycle(reason)
    return {
        "reason": reason,
        "status": status_dict(),
        "next_step": suggest_next_step(),
        "report": report_activity(5),
        "top_templates": get_top_templates(8),
        "top_topics": get_top_topics(8),
        "hints": get_recent_hints(5),
    }



def apply_setting(key: str, value: Any) -> None:
    state = load_state()
    settings = dict(state.get("settings", {}) or {})
    settings[key] = value
    state["settings"] = settings
    save_state(state)
    add_event("status", f"setting updated: {key}", value=value)



def set_deterministic_seed(seed: Optional[str]) -> None:
    apply_setting("deterministic_seed", seed)



def set_prefer_serious(value: bool) -> None:
    apply_setting("prefer_serious", bool(value))



def set_quiet_mode(value: bool) -> None:
    apply_setting("quiet_mode", bool(value))



def set_auto_hint(value: bool) -> None:
    apply_setting("auto_hint", bool(value))



def set_learning_enabled(value: bool) -> None:
    apply_setting("learn_from_web", bool(value))



def set_prefer_core_templates(value: bool) -> None:
    apply_setting("prefer_core_templates", bool(value))



def set_avoid_repeat_focus(value: bool) -> None:
    apply_setting("avoid_repeat_focus", bool(value))



def get_setting(name: str, default: Any = None) -> Any:
    state = load_state()
    return dict(state.get("settings", {}) or {}).get(name, default)



def batch_remember(lines: Iterable[str], kind: str = "memory", **meta: Any) -> list[dict[str, Any]]:
    out = []
    for line in lines:
        if str(line).strip():
            out.append(remember(str(line), kind=kind, **meta))
    return out



def batch_hints(lines: Iterable[str], **meta: Any) -> list[dict[str, Any]]:
    out = []
    for line in lines:
        if str(line).strip():
            out.append(log_hint(str(line), **meta))
    return out



def compact_state_for_export() -> dict[str, Any]:
    state = load_state()
    compact = trim_state(dict(state))
    compact.pop("web_library", None)
    return compact



def export_state_file(path: Optional[Path] = None) -> Path:
    ensure_dirs()
    path = path or (SNAPSHOT_DIR / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    _safe_json_dump(path, compact_state_for_export())
    return path



def import_state_file(path: Path | str) -> None:
    path = Path(path)
    data = _safe_json_load(path, None)
    if not isinstance(data, dict):
        raise ValueError("invalid state file")
    state = default_state()
    state.update(data)
    save_state(trim_state(state))
    add_event("status", f"imported state from {path}")



def summarize_memory(limit: int = 10) -> str:
    items = get_recent_memory(limit)
    lines = [f"memory summary @ {now()}"]
    for item in items:
        lines.append(f"- {item.get('kind')}: {item.get('text')}")
    return "\n".join(lines)



def summarize_hints(limit: int = 10) -> str:
    items = get_recent_hints(limit)
    lines = [f"hints summary @ {now()}"]
    for item in items:
        lines.append(f"- {item.get('kind')}: {item.get('text')}")
    return "\n".join(lines)



def summarize_learnings(limit: int = 10) -> str:
    items = list_learnings(limit)
    lines = [f"learning summary @ {now()}"]
    for item in items:
        lines.append(f"- {item.get('title')} | {item.get('source')} | {', '.join(item.get('keywords', []) or [])}")
    return "\n".join(lines)



def summarize_events(limit: int = 20) -> str:
    items = get_recent_events(limit)
    lines = [f"event summary @ {now()}"]
    for item in items:
        lines.append(f"- {item.get('kind')}: {item.get('message')}")
    return "\n".join(lines)



def set_memory_limit(limit: int) -> None:
    limit = max(10, min(2000, int(limit)))
    apply_setting("memory_limit", limit)



def prune_state() -> dict[str, Any]:
    state = trim_state(load_state())
    save_state(state)
    save_cache({"pruned_at": now(), "status": summarize_state()})
    return state



def health_check() -> dict[str, Any]:
    state = load_state()
    problems: list[str] = []
    if not isinstance(state.get("settings"), dict):
        problems.append("settings missing")
    if len(state.get("memory", [])) > MAX_MEMORY:
        problems.append("memory overflow")
    if len(state.get("hints", [])) > MAX_HINTS:
        problems.append("hint overflow")
    if len(state.get("web_learnings", [])) > MAX_LEARNINGS:
        problems.append("learning overflow")
    return {
        "healthy": not problems,
        "problems": problems,
        "runs": state.get("run_count", 0),
        "state_file_exists": STATE_FILE.exists(),
        "learning_file_exists": LEARNING_FILE.exists(),
        "cache_file_exists": CACHE_FILE.exists(),
    }



def _cli_print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))



def main() -> None:
    ensure_dirs()
    state = load_state()
    state["run_count"] = int(state.get("run_count", 0))
    save_state(state)
    status = get_extension_status()
    print(format_status(status))
    print()
    print(suggest_next_step())
    print(f"learning file: {LEARNING_FILE}")


if __name__ == "__main__":
    main()

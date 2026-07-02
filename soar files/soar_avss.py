# ======================================
# SOAR AVSS (Anti Virus SOAR Software)
# V 1.0 
# Made by Philip Kluz 2026 Jun 25 Late
# SOAR Help Module #002
# "ay ve es es"
# ======================================

import os
import time
import threading
from pathlib import Path
from copy import deepcopy

import psutil

MALWARE_BLOCKLIST = [
    "malware.exe",
    "miner.exe",
    "bad_process",
    "reverse_shell.sh",
]

SUSPICIOUS_KEYWORDS = [
    "trojan",
    "keylogger",
    "stealer",
    "backdoor",
    "injector",
    "payload",
    "njrat",
    "quasarrat",
    "async_rat",
]

MONITOR_INTERVAL = 5
DEDUP_TTL = 60
MAX_REPORT_ITEMS = 200

TTS_LOCK = threading.Lock()

DESKTOP = Path.home() / "Desktop"
if not DESKTOP.exists():
    DESKTOP = None

_report_lock = threading.Lock()
_report = {
    "running": False,
    "last_scan": None,
    "scan_count": 0,
    "blocked_count": 0,
    "suspicious_count": 0,
    "terminated_count": 0,
    "failed_terminations": 0,
    "file_hits": 0,
    "process_hits": 0,
    "errors": 0,
    "items": [],
}

_recent_hits = {}
_recent_lock = threading.Lock()


def _now():
    return time.time()


def _prune_recent():
    cutoff = _now() - DEDUP_TTL
    stale = [key for key, ts in _recent_hits.items() if ts < cutoff]
    for key in stale:
        _recent_hits.pop(key, None)


def _should_emit(key):
    with _recent_lock:
        _prune_recent()
        if key in _recent_hits:
            return False
        _recent_hits[key] = _now()
        return True


def _append_report(item):
    with _report_lock:
        _report["items"].append(item)
        if len(_report["items"]) > MAX_REPORT_ITEMS:
            _report["items"] = _report["items"][-MAX_REPORT_ITEMS:]


def _record_item(kind, severity, title, details, action=None, status=None):
    item = {
        "time": _now(),
        "kind": kind,
        "severity": severity,
        "title": title,
        "details": details,
        "action": action,
        "status": status,
    }
    _append_report(item)
    return item


def _is_suspicious_text(text):
    lower_text = (text or "").lower()
    return any(keyword in lower_text for keyword in SUSPICIOUS_KEYWORDS)


def _is_blocklisted_text(text):
    lower_text = (text or "").lower()
    return any(bad_name in lower_text for bad_name in MALWARE_BLOCKLIST)


def terminate_process(proc_pid):
    try:
        proc = psutil.Process(proc_pid)

        children = []
        try:
            children = proc.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            proc.terminate()
        except Exception:
            pass

        targets = [proc, *children]
        gone, alive = psutil.wait_procs(targets, timeout=3)

        for alive_proc in alive:
            try:
                alive_proc.kill()
            except Exception:
                pass

        psutil.wait_procs(alive, timeout=3)

        return not psutil.pid_exists(proc_pid)
    except Exception:
        return False


def _scan_processes_once():
    blocked_count = 0
    suspicious_count = 0
    terminated_count = 0
    failed_terminations = 0
    process_hits = 0

    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            proc_name = proc.info.get("name") or ""
            proc_pid = proc.info.get("pid")
            proc_exe = proc.info.get("exe") or ""
            proc_cmdline = " ".join(proc.info.get("cmdline") or [])

            blob = f"{proc_name} {proc_exe} {proc_cmdline}".lower()

            if _is_blocklisted_text(blob):
                key = f"block::{proc_pid}::{proc_name.lower()}::{proc_exe.lower()}"
                if _should_emit(key):
                    blocked_count += 1
                    title = "Blocklisted process detected"
                    details = {
                        "pid": proc_pid,
                        "name": proc_name,
                        "exe": proc_exe,
                        "cmdline": proc_cmdline,
                    }
                    terminated = terminate_process(proc_pid)
                    if terminated:
                        terminated_count += 1
                        status = "terminated"
                    else:
                        failed_terminations += 1
                        status = "failed"

                    _record_item(
                        kind="process",
                        severity="extreme",
                        title=title,
                        details=details,
                        action="terminate",
                        status=status,
                    )
                continue

            if _is_suspicious_text(blob):
                key = f"suspicious-proc::{proc_pid}::{proc_name.lower()}::{proc_exe.lower()}"
                if _should_emit(key):
                    suspicious_count += 1
                    process_hits += 1
                    _record_item(
                        kind="process",
                        severity="warning",
                        title="Suspicious process detected",
                        details={
                            "pid": proc_pid,
                            "name": proc_name,
                            "exe": proc_exe,
                            "cmdline": proc_cmdline,
                        },
                        action="queued_for_review",
                        status="pending",
                    )

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as e:
            with _report_lock:
                _report["errors"] += 1
            _record_item(
                kind="error",
                severity="low",
                title="Process scan error",
                details={"error": str(e)},
                action="scan",
                status="failed",
            )

    return {
        "blocked_count": blocked_count,
        "suspicious_count": suspicious_count,
        "terminated_count": terminated_count,
        "failed_terminations": failed_terminations,
        "process_hits": process_hits,
    }


def _scan_files_once():
    file_hits = 0

    if DESKTOP is None:
        return {"file_hits": 0}

    try:
        for path in DESKTOP.rglob("*"):
            try:
                if not path.is_file():
                    continue

                file_blob = f"{path.name} {str(path)}".lower()

                if _is_suspicious_text(file_blob):
                    key = f"suspicious-file::{str(path).lower()}"
                    if _should_emit(key):
                        file_hits += 1
                        _record_item(
                            kind="file",
                            severity="warning",
                            title="Suspicious file detected",
                            details={
                                "name": path.name,
                                "path": str(path),
                            },
                            action="queued_for_review",
                            status="pending",
                        )

            except Exception as e:
                with _report_lock:
                    _report["errors"] += 1
                _record_item(
                    kind="error",
                    severity="low",
                    title="File scan error",
                    details={"path": str(path), "error": str(e)},
                    action="scan",
                    status="failed",
                )
    except Exception as e:
        with _report_lock:
            _report["errors"] += 1
        _record_item(
            kind="error",
            severity="low",
            title="Desktop scan error",
            details={"error": str(e)},
            action="scan",
            status="failed",
        )

    return {"file_hits": file_hits}


def scan_once():
    process_result = _scan_processes_once()
    file_result = _scan_files_once()

    with _report_lock:
        _report["scan_count"] += 1
        _report["blocked_count"] += process_result["blocked_count"]
        _report["suspicious_count"] += process_result["suspicious_count"] + file_result["file_hits"]
        _report["terminated_count"] += process_result["terminated_count"]
        _report["failed_terminations"] += process_result["failed_terminations"]
        _report["file_hits"] += file_result["file_hits"]
        _report["process_hits"] += process_result["process_hits"]
        _report["last_scan"] = _now()

    return get_report(clear=False)


def run_avss_loop(stop_event, interval=MONITOR_INTERVAL):
    with _report_lock:
        _report["running"] = True

    try:
        while not stop_event.is_set():
            try:
                scan_once()
            except Exception as e:
                with _report_lock:
                    _report["errors"] += 1
                _record_item(
                    kind="error",
                    severity="low",
                    title="Scan loop error",
                    details={"error": str(e)},
                    action="scan_loop",
                    status="failed",
                )

            for _ in range(int(interval * 10)):
                if stop_event.is_set():
                    break
                time.sleep(0.1)
    finally:
        with _report_lock:
            _report["running"] = False


def get_report(clear=False):
    with _report_lock:
        snapshot = deepcopy(_report)
        if clear:
            _report["items"].clear()
            _report["scan_count"] = 0
            _report["blocked_count"] = 0
            _report["suspicious_count"] = 0
            _report["terminated_count"] = 0
            _report["failed_terminations"] = 0
            _report["file_hits"] = 0
            _report["process_hits"] = 0
            _report["errors"] = 0
            _report["last_scan"] = None
    return snapshot


def clear_report():
    return get_report(clear=True)


def start_background_monitor(stop_event=None, interval=MONITOR_INTERVAL):
    if stop_event is None:
        stop_event = threading.Event()

    thread = threading.Thread(
        target=run_avss_loop,
        args=(stop_event, interval),
        daemon=True,
    )
    thread.start()
    return stop_event, thread


def has_pending_items():
    with _report_lock:
        return len(_report["items"]) > 0


def get_pending_items():
    with _report_lock:
        return deepcopy(_report["items"])


def pop_pending_items():
    with _report_lock:
        items = deepcopy(_report["items"])
        _report["items"].clear()
    return items
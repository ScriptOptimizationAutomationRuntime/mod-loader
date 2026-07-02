# ======================================================
# CSRS (Connection Server Request System) V 1.0
# SOAR Help Module #003
# Made by Philip Kluz 2026 Jun 29 Late
# "sE es aRe es"
# ======================================================

import os
import platform
import socket
import subprocess
import sys
import threading
import time
from statistics import mean

GREEN = "\033[38;5;22m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"

DEFAULT_TARGETS = [
    "8.8.8.8",
    "1.1.1.1",
    "google.com",
    "cloudflare.com",
]

RECOVERY_TARGETS = [
    "1.0.0.1",
    "9.9.9.9",
    "github.com",
    "microsoft.com",
    "apple.com",
]

HIGH_LATENCY_MS = 250
TIMEOUT_SECONDS = 2.5
GOOD_SCORE_THRESHOLD = 65

MAX_RECOVERY_ATTEMPTS = None
RECOVERY_SLEEP_SECONDS = 1.25

SWITCH_MARGIN = 10
LOW_SIGNAL = 55


def colorize(text, color=GREEN):
    return f"{color}{text}{RESET}"


def slow_print(text, delay=0.005, color=GREEN):
    for c in text:
        sys.stdout.write(colorize(c, color))
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()


def section(title):
    print()
    slow_print(title, delay=0.005, color=GREEN)
    slow_print("-" * len(title), delay=0.001, color=GREEN)


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def normalize_targets(raw_tokens):
    cleaned = []
    for token in raw_tokens:
        token = token.strip()
        if not token or token == "-":
            continue
        if token.lower() in {"test", "request", "mode"}:
            continue
        cleaned.append(token)

    seen = set()
    unique = []
    duplicates = []
    for t in cleaned:
        key = t.lower()
        if key in seen:
            duplicates.append(t)
        else:
            seen.add(key)
            unique.append(t)
    return unique, duplicates


def parse_request(arg):
    raw = (arg or "").strip()
    if not raw:
        return "run", [], ""

    tokens = raw.split()
    head = tokens[0].lower()

    if head in {"run", "fix", "devtest", "devtest0151", "status", "auto"}:
        mode = head
        targets, _dupes = normalize_targets(tokens[1:])
        return mode, targets, raw

    targets, _dupes = normalize_targets(tokens)
    return "run", targets, raw


def inspect_target(host, results, index, timeout=TIMEOUT_SECONDS):
    entry = {
        "target": host,
        "resolved": False,
        "resolved_ip": None,
        "dns_error": None,
        "tcp_ok": False,
        "latency_ms": None,
        "tcp_error": None,
        "port": 443,
    }

    try:
        info = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if info:
            entry["resolved"] = True
            entry["resolved_ip"] = info[0][4][0]
    except Exception as e:
        entry["dns_error"] = str(e)
        results[index] = entry
        return

    try:
        start = time.time()
        with socket.create_connection((host, 443), timeout=timeout):
            pass
        entry["tcp_ok"] = True
        entry["latency_ms"] = round((time.time() - start) * 1000, 2)
    except Exception as e:
        entry["tcp_error"] = str(e)

    results[index] = entry


def run_diagnostics(targets, timeout=TIMEOUT_SECONDS):
    results = [None] * len(targets)
    threads = []

    for i, target in enumerate(targets):
        th = threading.Thread(target=inspect_target, args=(target, results, i, timeout), daemon=True)
        th.start()
        threads.append(th)

    for th in threads:
        th.join()

    return results


def build_problems(results, duplicates=None):
    problems = []

    if duplicates:
        problems.append(("warning", f"Duplicate targets detected: {', '.join(duplicates)}"))

    if not results:
        problems.append(("error", "No targets were provided for diagnostics."))
        return problems

    for item in results:
        host = item["target"]

        if item["dns_error"]:
            problems.append(("error", f"{host}: DNS resolution failed"))
            continue

        if not item["tcp_ok"]:
            err = item["tcp_error"] or "TCP connection failed"
            if "timed out" in err.lower():
                problems.append(("error", f"{host}: connection timed out"))
            else:
                problems.append(("error", f"{host}: {err}"))
            continue

        if item["latency_ms"] is not None and item["latency_ms"] > HIGH_LATENCY_MS:
            problems.append(("warning", f"{host}: high latency ({item['latency_ms']} ms)"))

    return problems


def health_score(results, duplicates=None):
    score = 100

    if duplicates:
        score -= min(10, len(duplicates) * 3)

    for item in results:
        if item["dns_error"]:
            score -= 30
        elif not item["tcp_ok"]:
            score -= 25
        elif item["latency_ms"] is not None:
            if item["latency_ms"] > HIGH_LATENCY_MS:
                score -= 10
            elif item["latency_ms"] > 120:
                score -= 3

    return max(0, score)


def score_label(score):
    if score >= 90:
        return "EXCELLENT"
    if score >= 75:
        return "GOOD"
    if score >= 55:
        return "FAIR"
    if score >= 35:
        return "WEAK"
    if score >= 15:
        return "EXTREME"
    return "CRITICAL"


def render_overview(arg, mode, targets, timeout, duplicates):
    slow_print("SOAR CSRS NETWORK DIAGNOSTIC ENGINE ACTIVE")
    slow_print(f"REQUEST: {arg or 'run'}")
    slow_print(f"MODE: {mode.upper()}")
    slow_print(f"TIMEOUT: {timeout:.1f}s")
    slow_print(f"TARGET COUNT: {len(targets)}")
    if duplicates:
        slow_print(f"DUPLICATES: {', '.join(duplicates)}", color=YELLOW)


def render_results(results):
    section("RESULTS")

    latency_values = [r["latency_ms"] for r in results if r["tcp_ok"] and r["latency_ms"] is not None]
    if latency_values:
        slow_print(f"AVERAGE LATENCY: {round(mean(latency_values), 2)} ms")
        slow_print(f"BEST LATENCY: {min(latency_values)} ms")
        slow_print(f"WORST LATENCY: {max(latency_values)} ms")
    else:
        slow_print("NO SUCCESSFUL TCP LATENCY MEASUREMENTS.", color=YELLOW)

    print()
    for item in results:
        host = item["target"]

        if item["dns_error"]:
            slow_print(f"{host} -> DNS FAIL", color=RED)
            continue

        if item["tcp_ok"]:
            resolved = item["resolved_ip"] or "unknown"
            slow_print(f"{host} -> OK | IP {resolved} | {item['latency_ms']} ms")
        else:
            err = item["tcp_error"] or "connection failed"
            if "timed out" in err.lower():
                slow_print(f"{host} -> TIMEOUT", color=RED)
            else:
                slow_print(f"{host} -> FAIL", color=RED)


def render_problems(results, duplicates=None):
    section("PROBLEMS")

    problems = build_problems(results, duplicates)
    if not problems:
        slow_print("NO ACTIVE PROBLEMS DETECTED.")
        return problems

    for level, message in problems:
        if level == "error":
            slow_print(f"[ERROR] {message}", color=RED)
        else:
            slow_print(f"[WARN] {message}", color=YELLOW)

    return problems


def render_summary(results, problems, duplicates=None):
    section("SUMMARY")

    total = len(results)
    ok = sum(1 for r in results if r["tcp_ok"])
    failed_dns = sum(1 for r in results if r["dns_error"])
    failed_tcp = sum(1 for r in results if (not r["tcp_ok"]) and not r["dns_error"])
    score = health_score(results, duplicates)

    slow_print(f"TARGETS TESTED: {total}")
    slow_print(f"REACHABLE: {ok}")
    slow_print(f"DNS FAILURES: {failed_dns}")
    slow_print(f"TCP FAILURES: {failed_tcp}")
    slow_print(f"HEALTH SCORE: {score}/100")
    slow_print(f"HEALTH STATUS: {score_label(score)}")

    if problems:
        slow_print("PROBLEMS WERE FOUND IN THE CURRENT SESSION.", color=YELLOW)
    else:
        slow_print("NO PROBLEMS FOUND. CONNECTION PATH LOOKS STABLE.")

    return score


def expand_targets(targets):
    merged = []
    seen = set()

    for t in list(targets) + RECOVERY_TARGETS:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            merged.append(t)

    return merged


def try_run_command(cmd, timeout=20):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "cmd": cmd,
            "ok": result.returncode == 0,
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
            "returncode": result.returncode,
        }
    except FileNotFoundError:
        return {
            "cmd": cmd,
            "ok": False,
            "stdout": "",
            "stderr": "command not available",
            "returncode": None,
        }
    except Exception as e:
        return {
            "cmd": cmd,
            "ok": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": None,
        }


def is_windows():
    return platform.system().lower() == "windows"


def is_macos():
    return platform.system().lower() == "darwin"


def is_linux():
    return platform.system().lower() == "linux"


def parse_percent(text):
    if not text:
        return None
    digits = "".join(ch for ch in str(text) if ch.isdigit())
    return int(digits) if digits else None


def get_wifi_context():
    context = {
        "system": platform.system().lower(),
        "iface": None,
        "current_ssid": None,
        "current_signal": None,
        "known_ssids": set(),
        "available": [],
    }

    if is_windows():
        interfaces = try_run_command(["netsh", "wlan", "show", "interfaces"], timeout=12)
        for line in (interfaces["stdout"] + "\n" + interfaces["stderr"]).splitlines():
            low = line.lower().strip()
            if low.startswith("name") and ":" in line and context["iface"] is None:
                context["iface"] = line.split(":", 1)[1].strip()
            elif low.startswith("ssid") and ":" in line and "bssid" not in low and context["current_ssid"] is None:
                ssid = line.split(":", 1)[1].strip()
                if ssid and ssid.lower() != "not connected":
                    context["current_ssid"] = ssid
            elif low.startswith("signal") and ":" in line and context["current_signal"] is None:
                context["current_signal"] = parse_percent(line.split(":", 1)[1])

        profiles = try_run_command(["netsh", "wlan", "show", "profiles"], timeout=12)
        for line in (profiles["stdout"] + "\n" + profiles["stderr"]).splitlines():
            low = line.lower().strip()
            if "all user profile" in low or "user profile" in low:
                if ":" in line:
                    context["known_ssids"].add(line.split(":", 1)[1].strip())

        scan = try_run_command(["netsh", "wlan", "show", "networks", "mode=bssid"], timeout=20)
        context["available"] = parse_windows_wifi_scan(scan["stdout"])
        return context

    if is_macos():
        hw = try_run_command(["networksetup", "-listallhardwareports"], timeout=15)
        lines = (hw["stdout"] + "\n" + hw["stderr"]).splitlines()
        for i, line in enumerate(lines):
            if "Wi-Fi" in line or "AirPort" in line:
                for j in range(i, min(i + 5, len(lines))):
                    if lines[j].startswith("Device:"):
                        context["iface"] = lines[j].split(":", 1)[1].strip()
                        break
                if context["iface"]:
                    break
        if context["iface"] is None:
            context["iface"] = "en0"

        current = try_run_command(["networksetup", "-getairportnetwork", context["iface"]], timeout=10)
        text = (current["stdout"] + "\n" + current["stderr"]).strip()
        if "Current Wi-Fi Network:" in text:
            context["current_ssid"] = text.split("Current Wi-Fi Network:", 1)[1].strip()

        pref = try_run_command(["networksetup", "-listpreferredwirelessnetworks", context["iface"]], timeout=20)
        for line in (pref["stdout"] + "\n" + pref["stderr"]).splitlines():
            line = line.strip()
            if line and not line.lower().startswith("preferred wireless networks"):
                context["known_ssids"].add(line)

        airport = airport_scan_command()
        if airport:
            scan = try_run_command(airport, timeout=20)
            context["available"] = parse_macos_wifi_scan(scan["stdout"])
        return context

    nmcli = try_run_command(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,SECURITY,DEVICE", "dev", "wifi", "list"], timeout=20)
    context["available"] = parse_linux_wifi_scan(nmcli["stdout"])

    active = [x for x in context["available"] if x.get("active")]
    if active:
        best = active[0]
        context["current_ssid"] = best.get("ssid") or None
        context["current_signal"] = best.get("signal")

    conns = try_run_command(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"], timeout=20)
    for line in (conns["stdout"] + "\n" + conns["stderr"]).splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[1] == "wifi":
            context["known_ssids"].add(parts[0])

    if context["iface"] is None:
        dev = try_run_command(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"], timeout=15)
        for line in (dev["stdout"] + "\n" + dev["stderr"]).splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[1] == "wifi":
                context["iface"] = parts[0]
                break

    return context


def parse_windows_wifi_scan(text):
    networks = []
    ssid = None
    signal = None
    security = None

    for raw in text.splitlines():
        line = raw.strip()
        low = line.lower()

        if low.startswith("ssid ") and ":" in line:
            if ssid:
                networks.append({
                    "ssid": ssid,
                    "signal": signal or 0,
                    "security": security or "",
                })
            ssid = line.split(":", 1)[1].strip()
            signal = None
            security = None
        elif low.startswith("signal") and ":" in line:
            signal = parse_percent(line.split(":", 1)[1]) or 0
        elif low.startswith("authentication") and ":" in line:
            security = line.split(":", 1)[1].strip()

    if ssid:
        networks.append({
            "ssid": ssid,
            "signal": signal or 0,
            "security": security or "",
        })

    deduped = []
    seen = set()
    for n in networks:
        key = n["ssid"].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(n)
        elif n["signal"] > next((x["signal"] for x in deduped if x["ssid"].lower() == key), -1):
            for x in deduped:
                if x["ssid"].lower() == key:
                    x.update(n)
                    break
    return sorted(deduped, key=lambda x: x["signal"], reverse=True)


def parse_linux_wifi_scan(text):
    networks = []
    for line in text.splitlines():
        parts = line.split(":")
        if len(parts) < 5:
            continue
        active, ssid, signal, security, device = parts[:5]
        ssid = ssid.strip()
        if not ssid:
            continue
        try:
            sig = int(signal)
        except Exception:
            sig = 0
        networks.append({
            "ssid": ssid,
            "signal": sig,
            "security": security.strip(),
            "active": active.strip() == "*",
            "device": device.strip(),
        })
    deduped = []
    seen = set()
    for n in networks:
        key = n["ssid"].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(n)
        elif n["signal"] > next((x["signal"] for x in deduped if x["ssid"].lower() == key), -1):
            for x in deduped:
                if x["ssid"].lower() == key:
                    x.update(n)
                    break
    return sorted(deduped, key=lambda x: x["signal"], reverse=True)


def parse_macos_wifi_scan(text):
    networks = []
    for line in text.splitlines():
        line = line.rstrip()
        if not line or line.startswith("SSID"):
            continue
        pieces = line.split()
        if len(pieces) < 2:
            continue
        signal = None
        ssid = None
        for i in range(min(5, len(pieces))):
            if pieces[i].isdigit():
                signal = int(pieces[i])
                ssid = " ".join(pieces[0:i] + pieces[i+1:]) if i + 1 < len(pieces) else " ".join(pieces[0:i])
                break
        if signal is None:
            continue
        ssid = ssid.strip() if ssid else ""
        if not ssid:
            continue
        networks.append({
            "ssid": ssid,
            "signal": signal,
            "security": "",
        })
    return sorted(networks, key=lambda x: x["signal"], reverse=True)


def airport_scan_command():
    candidates = [
        ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-s"],
        ["airport", "-s"],
    ]
    for cmd in candidates:
        if shutil_which(cmd[0]):
            return cmd
    return None


def shutil_which(name):
    try:
        from shutil import which
        return which(name)
    except Exception:
        return None


def strongest_saved_candidate(context):
    current_ssid = context.get("current_ssid")
    current_signal = context.get("current_signal") or 0
    known = {s.lower(): s for s in context.get("known_ssids", set())}
    available = context.get("available", [])

    candidates = []
    for net in available:
        ssid = net.get("ssid")
        signal = net.get("signal", 0)
        if not ssid:
            continue
        if ssid.lower() not in known:
            continue
        if current_ssid and ssid.lower() == current_ssid.lower():
            continue
        candidates.append((ssid, signal))

    candidates.sort(key=lambda x: x[1], reverse=True)
    if not candidates:
        return None

    best_ssid, best_signal = candidates[0]
    if best_signal >= current_signal + SWITCH_MARGIN or current_signal <= LOW_SIGNAL:
        return {
            "ssid": best_ssid,
            "signal": best_signal,
        }
    return None


def switch_to_wifi(context):
    system = context["system"]
    target = strongest_saved_candidate(context)

    if target:
        ssid = target["ssid"]
        slow_print(f"FOUND STRONGER SAVED NETWORK: {ssid} ({target['signal']}%)", color=CYAN)
        return connect_to_saved_wifi(context, ssid)

    return bounce_wifi_and_retry(context)


def connect_to_saved_wifi(context, ssid):
    system = context["system"]
    iface = context.get("iface")

    if system == "windows":
        cmds = []
        if iface:
            cmds.append(["netsh", "wlan", "disconnect"])
        cmds.append(["netsh", "wlan", "connect", f'name="{ssid}"'])
        return run_command_sequence(cmds, pause=1.2)

    if system == "darwin":
        iface = iface or "en0"
        return run_command_sequence([
            ["networksetup", "-setairportpower", iface, "off"],
            ["networksetup", "-setairportpower", iface, "on"],
            ["networksetup", "-setairportnetwork", iface, ssid],
        ], pause=1.0)

    if iface:
        return run_command_sequence([
            ["nmcli", "dev", "disconnect", iface],
            ["nmcli", "connection", "up", ssid],
            ["nmcli", "dev", "connect", iface],
        ], pause=1.0)

    return {"ok": False, "stderr": "no interface found", "stdout": ""}


def bounce_wifi_and_retry(context):
    system = context["system"]
    iface = context.get("iface")

    if system == "windows":
        cmds = [
            ["ipconfig", "/flushdns"],
            ["ipconfig", "/release"],
            ["ipconfig", "/renew"],
        ]
        if iface:
            cmds = [
                ["netsh", "wlan", "disconnect"],
                ["netsh", "interface", "set", "interface", f'name="{iface}"', "admin=disabled"],
                ["netsh", "interface", "set", "interface", f'name="{iface}"', "admin=enabled"],
            ] + cmds
        return run_command_sequence(cmds, pause=1.1)

    if system == "darwin":
        iface = iface or "en0"
        return run_command_sequence([
            ["networksetup", "-setairportpower", iface, "off"],
            ["networksetup", "-setairportpower", iface, "on"],
            ["ipconfig", "set", iface, "DHCP"],
            ["dscacheutil", "-flushcache"],
            ["killall", "-HUP", "mDNSResponder"],
        ], pause=1.0)

    if iface:
        return run_command_sequence([
            ["nmcli", "dev", "disconnect", iface],
            ["nmcli", "radio", "wifi", "off"],
            ["nmcli", "radio", "wifi", "on"],
            ["nmcli", "dev", "connect", iface],
        ], pause=1.0)

    return run_command_sequence([
        ["nmcli", "networking", "off"],
        ["nmcli", "networking", "on"],
    ], pause=1.0)


def run_command_sequence(cmds, pause=0.8):
    last = {"ok": False, "stdout": "", "stderr": ""}
    for cmd in cmds:
        pretty = " ".join(cmd)
        slow_print(f"[RECOVERY] {pretty}", color=CYAN)
        out = try_run_command(cmd, timeout=25)
        last = out
        if out["ok"]:
            slow_print(f"[OK] {pretty}", color=GREEN)
        else:
            reason = out["stderr"] or "failed"
            slow_print(f"[FAIL] {pretty} -> {reason}", color=YELLOW)
        time.sleep(pause)
    return last


def attempt_recovery_step(attempt_number, score):
    section(f"RECOVERY ATTEMPT {attempt_number}")
    slow_print(f"CURRENT SCORE: {score}/100", color=YELLOW)
    slow_print("Scanning remembered Wi-Fi and trying the stronger option first...")

    context = get_wifi_context()

    if context.get("current_ssid"):
        slow_print(f"CURRENT NETWORK: {context['current_ssid']}", color=CYAN)
    if context.get("current_signal") is not None:
        slow_print(f"CURRENT SIGNAL: {context['current_signal']}%", color=CYAN)

    available = context.get("available", [])
    if available:
        best = available[0]
        slow_print(f"BEST SCAN RESULT: {best.get('ssid', 'unknown')} ({best.get('signal', 0)}%)", color=CYAN)

    changed = switch_to_wifi(context)
    if changed is None:
        slow_print("NO SWITCH ATTEMPT WAS POSSIBLE.", color=YELLOW)


def auto_recover_until_good(targets, duplicates=None):
    clear_screen()
    render_overview("run", "run", targets, TIMEOUT_SECONDS, duplicates)

    if not targets:
        targets = DEFAULT_TARGETS[:]

    working_targets = targets[:]
    best_score = -1
    best_results = None
    best_problems = None

    attempt = 0
    while True:
        attempt += 1
        section("DNS + TCP CHECK")
        timeout = TIMEOUT_SECONDS + min(2.0, attempt * 0.25)
        results = run_diagnostics(working_targets, timeout=timeout)
        render_results(results)
        problems = render_problems(results, duplicates)
        score = render_summary(results, problems, duplicates)

        if score > best_score:
            best_score = score
            best_results = results
            best_problems = problems

        if score >= GOOD_SCORE_THRESHOLD:
            section("RECOVERY COMPLETE")
            slow_print(f"GOOD CONNECTION ACHIEVED: {score}/100", color=GREEN)
            slow_print(f"THRESHOLD MET: {GOOD_SCORE_THRESHOLD}+", color=GREEN)
            return

        if MAX_RECOVERY_ATTEMPTS is not None and attempt >= MAX_RECOVERY_ATTEMPTS:
            break

        attempt_recovery_step(attempt, score)
        working_targets = expand_targets(working_targets)
        slow_print(f"Retrying in {RECOVERY_SLEEP_SECONDS:.1f}s...", color=YELLOW)
        time.sleep(RECOVERY_SLEEP_SECONDS)

    section("RECOVERY STOPPED")
    slow_print(f"BEST SCORE REACHED: {best_score}/100", color=YELLOW)
    slow_print(f"TARGET THRESHOLD WAS: {GOOD_SCORE_THRESHOLD}+", color=YELLOW)
    if best_results is not None:
        render_results(best_results)
        render_problems(best_results, duplicates)
        render_summary(best_results, best_problems, duplicates)


def mode_run(arg, targets, duplicates):
    auto_recover_until_good(targets, duplicates)


def mode_fix(arg, targets, duplicates):
    clear_screen()
    render_overview(arg, "fix", targets, TIMEOUT_SECONDS, duplicates)

    if not targets:
        targets = DEFAULT_TARGETS

    section("RECOVERY ACTIONS")
    steps = [
        "Rechecking local resolver path",
        "Retrying host lookup",
        "Rebuilding TCP test path",
        "Running stronger Wi-Fi recovery",
    ]

    for step in steps:
        slow_print(f"[FIX] {step}")
        time.sleep(0.35)

    attempt_recovery_step(1, 0)

    section("SECOND PASS")
    retry_results = run_diagnostics(targets, timeout=max(TIMEOUT_SECONDS, 4.0))
    render_results(retry_results)
    problems = render_problems(retry_results, duplicates)
    render_summary(retry_results, problems, duplicates)


def mode_devtest(arg, targets, duplicates):
    clear_screen()
    render_overview(arg, "devtest", targets, TIMEOUT_SECONDS, duplicates)

    section("DEVTEST OUTPUT")
    fake = [
        ("127.0.0.1", "SIMULATED", 0.2),
        ("localhost", "SIMULATED", 0.1),
        ("dev-node", "SIMULATED", 0.3),
        ("soar-internal", "SIMULATED", 0.4),
    ]

    for host, state, ms in fake:
        slow_print(f"{host} -> {state} | {ms} ms")

    section("PROBLEMS")
    slow_print("NO LIVE NETWORK PROBLEMS IN DEVTEST MODE.", color=YELLOW)


def mode_status(arg, targets, duplicates):
    clear_screen()
    render_overview(arg, "status", targets, TIMEOUT_SECONDS, duplicates)

    section("SYSTEM STATUS")
    ctx = get_wifi_context()
    slow_print(f"HOSTNAME: {socket.gethostname()}")
    slow_print(f"PLATFORM: {platform.system()} {platform.release()}")
    slow_print(f"PYTHON: {sys.version.split()[0]}")
    slow_print("DEFAULT PORT: 443")
    slow_print(f"DEFAULT TARGETS: {', '.join(DEFAULT_TARGETS)}")
    slow_print(f"GOOD SCORE THRESHOLD: {GOOD_SCORE_THRESHOLD}")
    slow_print(f"MAX RECOVERY ATTEMPTS: {'UNLIMITED' if MAX_RECOVERY_ATTEMPTS is None else MAX_RECOVERY_ATTEMPTS}")
    if ctx.get("current_ssid"):
        slow_print(f"CURRENT SSID: {ctx['current_ssid']}")
    if ctx.get("current_signal") is not None:
        slow_print(f"CURRENT SIGNAL: {ctx['current_signal']}%")
    if ctx.get("available"):
        best = ctx["available"][0]
        slow_print(f"BEST AVAILABLE: {best.get('ssid', 'unknown')} ({best.get('signal', 0)}%)")


def run_matrix_ui(arg):
    mode, targets, raw = parse_request(arg)
    _targets = targets[:] if targets else []
    _targets, duplicates = normalize_targets(_targets)
    if not _targets and mode not in {"devtest", "devtest0151", "status"}:
        _targets = DEFAULT_TARGETS

    if mode == "fix":
        mode_fix(raw, _targets, duplicates)
    elif mode in {"devtest", "devtest0151"}:
        mode_devtest(raw, _targets, duplicates)
    elif mode == "status":
        mode_status(raw, _targets, duplicates)
    else:
        mode_run(raw, _targets, duplicates)


if __name__ == "__main__":
    arg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "run"
    run_matrix_ui(arg)

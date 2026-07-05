# ======================================================
# SOAR RSMS (Resource & System Monitor Software) V 1.0
# SOAR Help Module #004
# Made by Philip Kluz 2026 Jul 04 Late
# "aR es es em es"
# ======================================================

import os
import sys
import time
import subprocess
import platform
import psutil

GREEN = "\033[38;5;22m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

CPU_THRESHOLD_PCT = 85.0
RAM_THRESHOLD_PCT = 90.0
DISK_THRESHOLD_PCT = 92.0

def colorize(text, color=GREEN):
    return f"{color}{text}{RESET}"

def slow_print(text, delay=0.005, color=GREEN):
    for c in text:
        sys.stdout.write(colorize(c, color))
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()

def launch():
    """Handles self-spawning architecture cleanly when invoked by soar_main."""
    current_script = os.path.abspath(__file__)
    os_type = platform.system()
    
    if os_type == "Windows":
        subprocess.Popen(["start", "cmd", "/c", sys.executable, current_script, "--detached"], shell=True)
        return True
        
    elif os_type == "Darwin":

        script_line = f'tell application "Terminal" to do script "\\"{sys.executable}\\" \\"{current_script}\\" --detached"'
        subprocess.Popen(["osascript", "-e", script_line, "-e", 'tell application "Terminal" to activate'])
        return True
        
    elif os_type == "Linux":
        for term in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]:
            if subprocess.run(["which", term], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                if term == "gnome-terminal":
                    subprocess.Popen([term, "--", sys.executable, current_script, "--detached"])
                else:
                    subprocess.Popen([term, "-e", f"{sys.executable} {current_script} --detached"])
                return True
    return False

def run_isolated_matrix():
    """The metric diagnostic matrix that prints inside the standalone window context."""
    slow_print("Initializing SOAR Resource Diagnostics...", color=GREEN)
    time.sleep(0.5)
    
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    
    print(f"  PLATFORM: {platform.system()} {platform.release()}")
    print(f"  CPU USAGE: {cpu}%")
    print(f"  RAM USAGE: {ram}%")
    print(f"  DISK SPACE: {disk}%")
    print("-" * 40)
    
    alerts = []
    if cpu > CPU_THRESHOLD_PCT: alerts.append(f"CRITICAL: High CPU Usage ({cpu}%!)")
    if ram > RAM_THRESHOLD_PCT: alerts.append(f"CRITICAL: High RAM Usage ({ram}%!)")
    if disk > DISK_THRESHOLD_PCT: alerts.append(f"WARNING: Disk capacity limit ({disk}%!)")
    
    if alerts:
        for alert in alerts:
            slow_print(alert, color=RED if "CRITICAL" in alert else YELLOW)
    else:
        slow_print("ALL RESOURCE METRICS WITHIN NOMINAL BOUNDS.", color=GREEN)
        
    print("-" * 40)
    slow_print("Task complete. This window will close in 4 seconds...", color=YELLOW)
    time.sleep(4)

if __name__ == "__main__":
    if "--detached" in sys.argv:
        run_isolated_matrix()

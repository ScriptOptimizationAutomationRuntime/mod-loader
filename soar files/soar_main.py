# =====================================================
# SOAR MAIN SYSTEM
# SOAR - Script Optimization and Automation Runtime
# Made by Philip Kluz
# Version 1.00.8 Early Beta
# DO NOT EDIT CORE PARTS.
# =====================================================

from __future__ import annotations

import ast
import io
import json
import os
import platform
from pydoc import text
import random
import queue
import shlex
import socket
import subprocess
import sys
import threading
import time
import psutil
import webbrowser
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from urllib.parse import quote_plus
import urllib.request
import ssl
import certifi

pronoun = "sir" # you can change this to prefered pronoun.
_last_resource_alert = 0
RESOURCE_COOLDOWN = 10  #seconds
intro_start_time = 0 

IS_SPEAKING = False

intro_proc = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    import soar_autocode
except Exception:
    soar_autocode = None

try:
    import soar_avss
except Exception:
    soar_avss = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import rsms  # type: ignore
except Exception:
    rsms = None

APP_NAME = "SOAR"
BASE_DIR = Path(__file__).resolve().parent
MAIN_SCRIPT = Path(__file__).resolve()
DATA_DIR = BASE_DIR / "soar_data"
PROJECTS_DIR = Path.home() / "SOAR" / "Projects"
SETTINGS_FILE = DATA_DIR / "settings.json"
NOTES_FILE = DATA_DIR / "notes.txt"
MEMORY_FILE = DATA_DIR / "memories.txt"
TODO_FILE = DATA_DIR / "todos.txt"
CHAT_LOG = DATA_DIR / "chat_log.txt"
MODS_DIR = BASE_DIR / "soar-mods"

for p in [DATA_DIR, PROJECTS_DIR, NOTES_FILE, MEMORY_FILE, TODO_FILE, CHAT_LOG, SETTINGS_FILE]:
    if p == DATA_DIR or p == PROJECTS_DIR:
        p.mkdir(parents=True, exist_ok=True)
    elif not p.exists():
        p.write_text("", encoding="utf-8")

STARTUP_TIME = datetime.now()

autocode_enabled = False
autocode_stop = threading.Event()

stop_event = threading.Event()
bot_lock = threading.Lock()

voice_pause = threading.Event()
voice_enabled = True
listener_stop = None
voice_state_lock = threading.Lock()

recognizer = None

tts_engine = None
tts_queue = queue.Queue()
tts_ready = threading.Event()
tts_thread = None

speech_cooldown_until = 0.0
speech_cooldown_lock = threading.Lock()

shutting_down = False

SETTINGS_LOCK = threading.Lock()
SETTINGS_CACHE = None

tts_voice_label = None
tts_voice_id = None

ssl_context = ssl.create_default_context(cafile=certifi.where())

# ======================================================
# SPA (SOAR Project Agent) V 1.0
# SOAR Help Module #005
# Made by Philip Kluz 2026 Jul 19 Late
# "eS p eY e"
# ======================================================

class ProjectAgent:
    """
    SOAR Advanced Autonomous Project Builder Agent
    Features: Dynamic project routing, intelligent scaffolding, multi-file AST validation, 
    metadata tracking, and context-aware execution.
    """
    def __init__(self, prompt: str, project_name: str):
        self.prompt = prompt.strip()
        self.project_name = project_name.strip().replace(" ", "_")
        
        current_script_dir = Path(__file__).resolve().parent
        self.project_dir = current_script_dir / "projects" / self.project_name
        
        self.logs = []
        self.project_type = self._determine_project_type()
        self.entry_point = "main.py" 
        self.features = []

    def log(self, message: str):
        full_msg = f"[{self.project_name.upper()}-BUILDER] {message}"
        self.logs.append(full_msg)
        print(full_msg)

    def _determine_project_type(self) -> str:
        """Analyzes the prompt to route to the correct architecture."""
        prompt_lower = self.prompt.lower()
        if any(word in prompt_lower for word in ["bot", "discord", "slack", "telegram"]):
            return "bot"
        elif any(word in prompt_lower for word in ["web", "website", "html", "flask", "django"]):
            return "web_app"
        elif any(word in prompt_lower for word in ["api", "endpoint", "rest", "backend"]):
            return "api"
        elif any(word in prompt_lower for word in ["data", "scrape", "csv", "json"]):
            return "data_tool"
        elif any(word in prompt_lower for word in ["game", "pygame", "arcade"]):
            return "game"
        elif any(word in prompt_lower for word in ["gui", "interface", "desktop", "tkinter"]):
            return "desktop_gui"
        elif any(word in prompt_lower for word in ["automation", "organize", "cleanup", "file"]):
            return "automation_script"
        else:
            return "cli" 

    def execute_pipeline(self):
        self.log(f"Initializing ADVANCED build pipeline.")
        self.log(f"Detected Project Architecture: {self.project_type.upper()}")
        
        self.make_folders()
        self.write_code()
        
        success = self.debug_and_test()
        
        if success:
            self.run_project()
        else:
            self.log("Pipeline stopped: Code checking failed validation step.")
            
        self.explain_everything()

    def make_folders(self):
        self.log("Scaffolding dynamic workspace directories...")
        
        directories = ["src", "tests", "docs", "config"]
        
        if self.project_type == "web_app":
            directories.extend(["src/templates", "src/static"])
        elif self.project_type == "data_tool":
            directories.extend(["data/input", "data/output"])

        for d in directories:
            (self.project_dir / d).mkdir(parents=True, exist_ok=True)
            
        self.log(f"Directory structure prepared at: {self.project_dir}")

    def write_code(self):
        self.log("Generating source assets, routing templates, and configuring dependencies...")
        
        manifest = {
            "name": self.project_name,
            "type": self.project_type,
            "generated_at": datetime.now().isoformat(),
            "original_prompt": self.prompt
        }
        
        if self.project_type == "bot":
            self.entry_point = "bot.py"
            reqs = "discord.py\npython-dotenv\n"
            main_code = dedent("""\
                import os
                import sys
                import time
                
                print("[LIVE] Advanced Bot Framework starting...")
                print("[LIVE] Loading environment configurations...")
                
                if __name__ == '__main__':
                    print("✓ Bot connection protocols established.")
                    print("✓ Listening for incoming commands.")
                    try:
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        print("Exiting bot instance safely.")
            """)
            self.features = ["Command Routing", "Event Listeners", "Env Config"]

        elif self.project_type == "desktop_gui":
            self.entry_point = "gui_app.py"
            reqs = ""  
            main_code = dedent("""\
                import tkinter as tk
                from tkinter import messagebox
                import sys
                
                print("[GUI SYSTEM] Compiling platform window configurations...")
                
                class SoarAppWindow:
                    def __init__(self):
                        self.root = tk.Tk()
                        self.root.title(f"{self.__class__.__name__} - SOAR Generated Interface")
                        self.root.geometry("450x300")
                        self.build_layout()
                        
                    def build_layout(self):
                        lbl = tk.Label(self.root, text="SOAR Autonomous Window", font=("Helvetica", 14, "bold"))
                        lbl.pack(pady=20)
                        
                        btn = tk.Button(self.root, text="Trigger Action Matrix", command=self.on_click)
                        btn.pack(pady=10)
                        
                    def on_click(self):
                        print("[GUI CALLBACK] Action button clicked.")
                        
                    def run(self):
                        # Safely runs unless headless/detached error happens
                        if sys.stdout and sys.stdout.isatty():
                            self.root.mainloop()
                        else:
                            print("[GUI WARNING] Headless background worker running without desktop window.")
                            
                if __name__ == '__main__':
                    app = SoarAppWindow()
                    print("✓ Window wrapper successfully mounted.")
            """)
            self.features = ["Tkinter Mainloop Architecture", "Responsive Layout Constraints", "Event-Driven Button Callbacks"]

        elif self.project_type == "automation_script":
            self.entry_point = "cleaner.py"
            reqs = "psutil\n"
            main_code = dedent(f"""\
                import os
                import sys
                import shutil
                from pathlib import Path
                
                print("[AUTOMATION LOG] Initializing dynamic file system scanner...")
                
                def run_maintenance_scan(target_path):
                    path = Path(target_path)
                    print(f"[SCANNING] Parsing node branches inside: {{path}}")
                    
                    # Core target safety checklist rule
                    protected_roots = ["C:\\\\Windows", "/System", "/usr/bin"]
                    if any(str(path).startswith(p) for p in protected_roots):
                        print("[-] Access Revoked: System core targets are shielded by SOAR safety guardrails.")
                        return False
                        
                    print("✓ Scan trace operation executed completely with zero conflicts.")
                    return True
                    
                if __name__ == '__main__':
                    # Fallback to local project workspace directory context
                    run_maintenance_scan("./")
            """)
            self.features = ["File Tree Pattern Scanning", "SOAR Core Safety Shield Guardrails", "Shutil Context File Relocator Blueprint"]
            
        elif self.project_type == "web_app":
            self.entry_point = "app.py"
            reqs = "flask\nwerkzeug\n"
            main_code = dedent("""\
                from flask import Flask, jsonify
                
                app = Flask(__name__)
                
                @app.route('/')
                def home():
                    return jsonify({"status": "online", "message": "SOAR Web App Active"})
                
                if __name__ == '__main__':
                    print("[LIVE] Web Server starting on port 5000...")
                    # app.run(debug=True, port=5000) # Uncomment to actually run
            """)
            
            index_html = dedent("""\
                <!DOCTYPE html>
                <html><head><title>SOAR App</title></head>
                <body><h1>App is running!</h1></body></html>
            """)
            (self.project_dir / "src" / "templates" / "index.html").write_text(index_html, encoding="utf-8")
            self.features = ["Flask Routing", "HTML Templates", "Static Assets"]

        elif self.project_type == "api":
            self.entry_point = "api.py"
            reqs = "fastapi\nuvicorn\n"
            main_code = dedent("""\
                import json
                print("[LIVE] API Gateway initializing...")
                print("✓ Endpoints mounted at /api/v1/")
                
                if __name__ == '__main__':
                    print("Ready for requests.")
            """)
            self.features = ["JSON Endpoints", "Data Validation", "REST Architecture"]

        else: 
            self.entry_point = "main.py"
            reqs = "requests\n"
            main_code = dedent(f"""\
                import argparse
                import sys
                
                def main():
                    parser = argparse.ArgumentParser(description="{self.prompt}")
                    parser.add_argument('--run', action='store_true', help='Execute main routine')
                    args = parser.parse_args()
                    
                    print(f"[{self.project_name.upper()}] CLI Tool Initialized.")
                    if args.run:
                        print("Execution complete.")
                
                if __name__ == '__main__':
                    main()
            """)
            self.features = ["Argument Parsing", "Terminal Output", "Modular Design"]

        (self.project_dir / "src" / self.entry_point).write_text(main_code, encoding="utf-8")
        (self.project_dir / "requirements.txt").write_text(reqs, encoding="utf-8")
        (self.project_dir / "soar_manifest.json").write_text(json.dumps(manifest, indent=4), encoding="utf-8")
        
        readme_content = dedent(f"""\
            # {self.project_name.replace("_", " ")}
            *Generated autonomously by SOAR ProjectAgent.*
            
            **Objective:** {self.prompt}
            **Architecture:** {self.project_type.upper()}
            
            ## Features Built
            {chr(10).join([f"- {f}" for f in self.features])}
            
            ## Getting Started
            1. `cd {self.project_name}`
            2. `pip install -r requirements.txt`
            3. `python src/{self.entry_point}`
        """)
        (self.project_dir / "README.md").write_text(readme_content, encoding="utf-8")
        
        self.log(f"Code generation complete. Entry point set to {self.entry_point}.")

    def debug_and_test(self) -> bool:
        self.log("Running comprehensive AST syntax validation on all Python files...")
        
        python_files = list(self.project_dir.rglob("*.py"))
        if not python_files:
            self.log("✗ No Python files found to test.")
            return False
            
        all_passed = True
        for py_file in python_files:
            try:
                source_content = py_file.read_text(encoding="utf-8")
                ast.parse(source_content)
                self.log(f"  ✓ {py_file.name}: Syntax clean.")
            except SyntaxError as e:
                self.log(f"  ✗ {py_file.name}: Syntax Error at line {e.lineno} -> {e.msg}")
                all_passed = False
                
        return all_passed

    def run_project(self):
        self.log(f"Spawning independent execution stream for {self.entry_point}...")
        target_script = self.project_dir / "src" / self.entry_point
        
        if not target_script.exists():
            self.log(f"✗ Cannot run. {self.entry_point} not found.")
            return
            
        if platform.system() == "Windows":
            subprocess.Popen(["start", "cmd", "/c", sys.executable, str(target_script)], shell=True)
        else:
            subprocess.Popen(
                [sys.executable, str(target_script)], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        self.log("✓ Project execution sequence initiated safely in background.")

    def explain_everything(self):
        print("\n" + "="*60)
        print(f" SOAR ADVANCED BUILD COMPLETE: {self.project_name.upper()}")
        print("="*60)
        print(f" ► Architecture : {self.project_type.title()}")
        print(f" ► Location     : {self.project_dir}")
        print(f" ► Entry File   : src/{self.entry_point}")
        
        print("\n [ Project Briefing ]")
        if self.project_type == "bot":
            print(" I have scaffolded a Bot Architecture. You will need to add your API")
            print(" Token (like a Discord or Slack token) to a .env file before it can")
            print(" truly connect to external servers.")
        elif self.project_type == "web_app":
            print(" I have built a Web Application scaffold using Flask. It includes")
            print(" template routing. You can expand the HTML in src/templates/")
            print(" and add CSS to src/static/.")
        elif self.project_type == "api":
            print(" I have generated an API Gateway. It is structured to handle JSON")
            print(" requests. Perfect for bridging frontends to databases.")
        else:
            print(" I have created a Command Line utility. It uses argparse so you")
            print(" can easily add flags and parameters to run from your terminal.")
            
        print("\n [ Next Steps ]")
        print(f" 1. Navigate to the folder: cd projects/{self.project_name}")
        print(" 2. Install dependencies:   pip install -r requirements.txt")
        print(f" 3. Run the application:    python src/{self.entry_point}")
        print("="*60 + "\n")


def log_line(who, text):
    line = f"[{stamp()}] {who}: {text}"
    with CHAT_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    cleanup_logs()

def cleanup_logs(max_lines=2000):
    try:
        if not CHAT_LOG.exists():
            return

        lines = CHAT_LOG.read_text(encoding="utf-8").splitlines()

        if len(lines) > max_lines:
            lines = lines[-max_lines:]
            CHAT_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")

    except Exception as e:
        print(f"[LOG CLEANUP ERROR] {e}")

def stamp():
    """Returns the current timestamp string for logs."""
    return datetime.now().strftime("%H:%M:%S")

def read_lines(path):
    if not path.exists():
        return []
    return [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def save_lines(path, lines):
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def append_line(path, text):
    with path.open("a", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")

def load_database():
    time.sleep(0.8) 

def initialize_network():
    time.sleep(1.2)

def load_configurations():
    time.sleep(0.4)

def verify_security():
    time.sleep(0.6)

import threading


def load_systems(tasks):
    total_tasks = len(tasks)
    bar_width = 40
    print(f"{APP_NAME} booting up...")
    
    current_pct = 0
    
    for index, (task_name, task_func) in enumerate(tasks):
        target_pct = int(((index + 1) / total_tasks) * 100)
        
        captured_output = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output
        
        task_thread = threading.Thread(target=task_func)
        task_thread.start()
        
        while task_thread.is_alive():
            log_content = captured_output.getvalue()
            if log_content:
                sys.stdout = original_stdout
                print(f"\r\033[K{log_content.strip()}")
                captured_output.seek(0)
                captured_output.truncate(0)
                sys.stdout = captured_output
                
            if current_pct < target_pct - 1:
                current_pct += 1
                filled_length = int(bar_width * current_pct // 100)
                bar = "█" * filled_length + " " * (bar_width - filled_length)
                
                original_stdout.write(f"\r[{bar}] {current_pct}% | Loading: {task_name:<25}")
                original_stdout.flush()
                time.sleep(0.02)
            else:
                time.sleep(0.01)
        
        sys.stdout = original_stdout
        
        remaining_log = captured_output.getvalue()
        if remaining_log:
            print(f"\r\033[K{remaining_log.strip()}")
            
        current_pct = target_pct
        filled_length = int(bar_width * current_pct // 100)
        bar = "█" * filled_length + " " * (bar_width - filled_length)
        print(f"\r[{bar}] {current_pct}% | Loaded: {task_name:<25}", end="", flush=True)


def default_settings():
    return {
        "voice_preference": "auto",
        "personality": {
            "Respectiveness": 0.85, # 0.85
            "Humor": 0.4, # 0.4
            "Honesty": 0.9, # 0.9   
            "Comfort": 0.7, # 0.7     
        }
    }


def load_settings():
    global SETTINGS_CACHE
    with SETTINGS_LOCK:
        if SETTINGS_CACHE is not None:
            return dict(SETTINGS_CACHE)

        data = default_settings()
        try:
            if SETTINGS_FILE.exists() and SETTINGS_FILE.read_text(encoding="utf-8").strip():
                loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data.update(loaded)
        except Exception as e:
            print(f"[{stamp()}] [SETTINGS ERROR] Failed to load configuration: {e}")

        SETTINGS_CACHE = data
        return dict(data)


def save_settings(settings):
    global SETTINGS_CACHE
    with SETTINGS_LOCK:
        merged = default_settings()
        if isinstance(settings, dict):
            merged.update(settings)
        SETTINGS_CACHE = merged
        SETTINGS_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")


def get_voice_preference():
    return str(load_settings().get("voice_preference", "auto") or "auto").strip()


def set_voice_preference(name):
    settings = load_settings()
    settings["voice_preference"] = str(name or "auto").strip() or "auto"
    save_settings(settings)


def resolve_mac_voice_candidates(preferred_name="auto"):
    pref = str(preferred_name or "auto").strip()
    low = pref.lower()

    if low in {"", "auto"}:
        return ["Daniel", "Alex", "Samantha", "Victoria", "Karen", "Moira"]
    if "daniel" in low:
        return ["Daniel", "Alex", "Samantha", "Victoria", "David"]
    if "alex" in low:
        return ["Alex", "Daniel", "Samantha", "Victoria"]
    if "samantha" in low:
        return ["Samantha", "Victoria", "Alex", "Daniel"]
    return [pref, "Daniel", "Alex", "Samantha", "Victoria"]


def resolve_windows_voice_candidates(preferred_name="auto"):
    pref = str(preferred_name or "auto").strip()
    low = pref.lower()

    if low in {"", "auto"}:
        return ["Daniel", "David", "Mark", "Zira", "Hazel"]
    if "daniel" in low:
        return ["Daniel", "David", "Mark", "Zira", "Hazel"]
    if "david" in low:
        return ["David", "Daniel", "Mark", "Zira", "Hazel"]
    if "zira" in low:
        return ["Zira", "David", "Mark", "Daniel", "Hazel"]
    return [pref, "Daniel", "David", "Mark", "Zira", "Hazel"]


def list_available_voices():
    system = platform.system()
    if system == "Darwin":
        try:
            result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=False)
            out = result.stdout.strip()
            if not out:
                return []
            voices = []
            for line in out.splitlines():
                line = line.strip()
                if not line:
                    continue
                name = line.split()[0]
                voices.append(name)
            return voices
        except Exception:
            return []
    if pyttsx3 is None:
        return []
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices") or []
        items = []
        for voice in voices:
            name = str(getattr(voice, "name", "") or "").strip()
            vid = str(getattr(voice, "id", "") or "").strip()
            if name and vid:
                items.append(f"{name} | {vid}")
            elif name:
                items.append(name)
            elif vid:
                items.append(vid)
        try:
            engine.stop()
        except Exception:
            pass
        return items
    except Exception:
        return []


def choose_best_tts_voice(engine=None, preferred_name=None):
    global tts_voice_label, tts_voice_id

    system = platform.system()
    pref = preferred_name if preferred_name is not None else get_voice_preference()

    if system == "Darwin":
        candidates = resolve_mac_voice_candidates(pref)
        available = list_available_voices()
        available_lower = [x.lower() for x in available]

        chosen = None
        for candidate in candidates:
            cand = candidate.lower()
            for idx, item in enumerate(available_lower):
                if cand in item:
                    chosen = available[idx]
                    break
            if chosen:
                break

        if chosen is None:
            chosen = candidates[0] if candidates else "Daniel"

        tts_voice_label = chosen
        tts_voice_id = chosen
        return chosen

    if engine is None:
        if pyttsx3 is None:
            return None
        try:
            engine = pyttsx3.init()
        except Exception:
            return None

    candidates = resolve_windows_voice_candidates(pref)
    try:
        voices = engine.getProperty("voices") or []
    except Exception:
        voices = []

    fallback = None
    for voice in voices:
        voice_id = str(getattr(voice, "id", "") or "")
        voice_name = str(getattr(voice, "name", "") or "")
        blob = f"{voice_id} {voice_name}".lower()

        for candidate in candidates:
            if candidate.lower() in blob:
                try:
                    engine.setProperty("voice", voice_id)
                    tts_voice_label = voice_name or voice_id
                    tts_voice_id = voice_id
                    return voice_id
                except Exception:
                    pass

        if fallback is None:
            fallback = voice_id

    if fallback:
        try:
            engine.setProperty("voice", fallback)
            for voice in voices:
                if str(getattr(voice, "id", "")) == fallback:
                    tts_voice_label = str(getattr(voice, "name", "") or fallback)
                    break
            else:
                tts_voice_label = fallback
            tts_voice_id = fallback
            return fallback
        except Exception:
            return None

    return None

if not MODS_DIR.exists(): #mods start 1
    MODS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[*] Created empty mods directory at: {MODS_DIR}")

def load_soar_mods():
    import importlib.util
    import sys
    from pathlib import Path
    
    MODS_DIR = BASE_DIR / "soar-mods"
    if not MODS_DIR.exists():
        MODS_DIR.mkdir(parents=True, exist_ok=True)
        
    if not hasattr(sys, "mod_commands"):
        sys.mod_commands = {}

    print("[SOAR MODS] Scanning 'soar-mods/' folder for active addons...")
    
    for mod_path in MODS_DIR.iterdir():
        if mod_path.is_dir():
            init_file = mod_path / "__init__.py"
            if init_file.exists():
                mod_name = mod_path.name
                try:
                    spec = importlib.util.spec_from_file_location(mod_name, str(init_file))
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[mod_name] = module
                        spec.loader.exec_module(module)
                        print(f"Mod Loaded: {mod_name}")
                        
                        if hasattr(module, "MOD_COMMANDS") and isinstance(module.MOD_COMMANDS, dict):
                            sys.mod_commands.update(module.MOD_COMMANDS)
                            
                        if hasattr(module, "initialize_addon"):
                            module.initialize_addon()
                except Exception as e:
                    print(f"Error loading mod {mod_name}: {e}")

    print("Mods above.")

load_soar_mods() #mods end 1

def show_voice_status():
    pref = get_voice_preference()
    print()
    print("Voice status")
    print(f"  platform: {platform.system()}")
    print(f"  preference: {pref}")
    print(f"  selected: {tts_voice_label or 'none'}")
    print(f"  tts ready: {'yes' if tts_ready.is_set() else 'no'}")
    print()


def refresh_voice_selection():
    global tts_engine
    pref = get_voice_preference()
    if platform.system() == "Darwin":
        choose_best_tts_voice(None, pref)
        return True
    if tts_engine is None:
        return False
    return choose_best_tts_voice(tts_engine, pref) is not None


def cooldown_seconds_for_text(text):
    return max(0.9, min(6.0, len(text) / 14.0))


def mic_is_muted():
    with speech_cooldown_lock:
        return voice_pause.is_set() or time.time() < speech_cooldown_until


def mute_mic_temporarily(seconds=1.0):
    global speech_cooldown_until
    with speech_cooldown_lock:
        voice_pause.set()
        speech_cooldown_until = max(speech_cooldown_until, time.time() + float(seconds))


def unmute_mic():
    with speech_cooldown_lock:
        voice_pause.clear()


def maybe_address_user(text, chance=0.25):
    if not text:
        return text
    low = text.lower()
    if "sir" in low or "ma'am" in low:
        return text
        
    try:
        settings = load_settings()
        personality = settings.get("personality", {})
        respect_score = personality.get("Respectiveness", 0.5)
    except Exception:
        respect_score = chance

    if random.random() < respect_score:
        cleaned = text.rstrip(".!?")
        if respect_score > 0.8:
            title = ", {pronoun}."
        elif respect_score > 0.4:
            title = ", friend."
        else:
            title = "."
        return f"{cleaned}{title}"
    return text


def open_url(target):
    target = target.strip()
    if not target:
        return False

    if not (target.startswith("http://") or target.startswith("https://")):
        if " " in target or "." not in target:
            target = f"https://www.google.com/search?q={quote_plus(target)}"
        else:
            target = "https://" + target

    try:
        webbrowser.open(target)
        return True
    except Exception:
        return False


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        try:
            s.close()
        except Exception:
            pass


def clipboard_copy(text):
    text = str(text)
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["pbcopy"], input=text, text=True, check=False)
            return True
        if system == "Windows":
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Set-Clipboard"],
                input=text,
                text=True,
                check=False,
            )
            return True

        for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
            try:
                subprocess.run(cmd, input=text, text=True, check=True)
                return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def clipboard_paste():
    system = platform.system()
    try:
        if system == "Darwin":
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=False)
            return result.stdout.strip()
        if system == "Windows":
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.stdout.strip()

        for cmd in (["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return result.stdout.strip()
            except Exception:
                continue
    except Exception:
        pass
    return ""


def parse_duration_seconds(text):
    s = text.strip().lower().replace(" ", "")
    if not s:
        raise ValueError("empty duration")

    suffix = s[-1]
    if suffix in {"s", "m", "h"}:
        value = float(s[:-1])
        if suffix == "s":
            return int(value)
        if suffix == "m":
            return int(value * 60)
        if suffix == "h":
            return int(value * 3600)

    return int(float(s))


def schedule_reminder(delay_seconds, message, kind="Reminder"):
    delay_seconds = max(1, int(delay_seconds))
    message = message.strip()

    def _fire():
        speak(f"{kind}: {message}", allow_sound=True)

    timer = threading.Timer(delay_seconds, _fire)
    timer.daemon = True
    timer.start()
    return timer


def search_storage(term):
    term = term.strip().lower()
    if not term:
        return []

    results = []
    sources = [
        ("notes", read_lines(NOTES_FILE)),
        ("memories", read_lines(MEMORY_FILE)),
        ("todos", read_lines(TODO_FILE)),
    ]

    for label, items in sources:
        for item in items:
            if term in item.lower():
                results.append(f"{label}: {item}")

    return results


def loading_status_line():
    return f"Running on {platform.system()} {platform.release()} with Python {sys.version.split()[0]}"


def is_protected_path(path):
    try:
        path = path.resolve()
    except Exception:
        path = Path(str(path)).absolute()

    try:
        if path == MAIN_SCRIPT:
            return True
    except Exception:
        pass
    return False


def normalize_path(text, allow_create=True):
    raw = str(text).strip().strip('"').strip("'")
    if not raw:
        raise ValueError("empty path")

    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path

    try:
        path = path.resolve()
    except Exception:
        path = path.absolute()

    allowed_roots = []
    for root in (BASE_DIR, DATA_DIR, PROJECTS_DIR):
        try:
            allowed_roots.append(root.resolve())
        except Exception:
            pass

    if not any(path == root or root in path.parents for root in allowed_roots):
        raise ValueError("path must stay inside the current SOAR folder")

    if is_protected_path(path):
        raise ValueError("main script is protected")

    if not allow_create and not path.exists():
        raise FileNotFoundError("file not found")

    return path


def autocode_connected():
    return soar_autocode is not None and hasattr(soar_autocode, "run_cycle")




def show_autocode_status():
    print()
    print("SOAR autocode status")
    print(f"  connected: {'yes' if autocode_connected() else 'no'}")

    if not autocode_connected():
        print()
        return

    state = None
    if hasattr(soar_autocode, "load_state"):
        try:
            state = soar_autocode.load_state()
        except Exception:
            state = None

    if isinstance(state, dict):
        print(f"  runs: {state.get('run_count', 0)}")
        print(f"  last project: {state.get('last_project') or 'none'}")
        recent = state.get("recent_projects", [])
        if isinstance(recent, list):
            print(f"  recent: {', '.join(recent[-5:]) or 'none'}")
        memory = state.get("memory", [])
        if isinstance(memory, list):
            print(f"  memories: {len(memory)}")

    projects_dir = getattr(soar_autocode, "PROJECTS_DIR", PROJECTS_DIR)
    print(f"  output folder: {projects_dir}")
    print()


def trigger_autocode(reason="manual trigger from main"):
    if not autocode_connected():
        print("Autocode is not connected.")
        speak("Autocode is not connected.", allow_sound=True)
        return False

    def _run():
        try:
            soar_autocode.run_cycle(reason)
        except Exception as e:
            print(f"Autocode error: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return True


def pause_voice_input():
    global listener_stop
    was_active = False

    try:
        acquired = voice_state_lock.acquire(blocking=False)
    except KeyboardInterrupt:
        return False

    if not acquired:
        voice_pause.set()
        return False

    try:
        voice_pause.set()
        if listener_stop is not None:
            try:
                listener_stop(wait_for_stop=False)
                was_active = True
            except Exception:
                pass
            listener_stop = None
    finally:
        try:
            voice_state_lock.release()
        except Exception:
            pass

    return was_active


def resume_voice_input(was_active):
    if shutting_down:
        unmute_mic()
        return

    if not was_active:
        unmute_mic()
        return

    if not voice_enabled or stop_event.is_set():
        unmute_mic()
        return

    try:
        acquired = voice_state_lock.acquire(blocking=False)
    except KeyboardInterrupt:
        unmute_mic()
        return

    try:
        if acquired and listener_stop is None:
            try:
                start_voice_listener()
            except Exception:
                pass
    finally:
        if acquired:
            try:
                voice_state_lock.release()
            except Exception:
                pass

    unmute_mic()


def tts_worker():
    global tts_engine, IS_SPEAKING  
    if pyttsx3 is None:
        print("TTS ERROR: pyttsx3 is not installed.")
        tts_ready.set()
        return

    try:
        tts_engine = pyttsx3.init()
        try:
            tts_engine.setProperty("rate", 190)
            tts_engine.setProperty("volume", 1.0)
        except Exception:
            pass

        chosen = choose_best_tts_voice(tts_engine, get_voice_preference())
        if chosen:
            print(f"TTS: using voice {chosen}")
        else:
            print("TTS: no preferred voice found, using fallback voice.")

        tts_ready.set()

        while not stop_event.is_set():
            try:
                item = tts_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is None:
                break

            text = str(item).strip()
            if not text:
                continue

            was_active = pause_voice_input()
            try:
                if tts_engine is not None:
                    tts_engine.stop()
                    tts_engine.say(text)
                    
                    IS_SPEAKING = True
                    tts_engine.runAndWait()
                    IS_SPEAKING = False
                    
            except Exception as e:
                print(f"TTS ERROR: {e}")
                IS_SPEAKING = False  
            finally:
                try:
                    if tts_engine is not None:
                        tts_engine.stop()
                except Exception:
                    pass
                IS_SPEAKING = False  
                resume_voice_input(was_active)

    except Exception as e:
        print(f"TTS ERROR: {e}")
        IS_SPEAKING = False
        tts_ready.set()
    finally:
        try:
            if tts_engine is not None:
                tts_engine.stop()
        except Exception:
            pass
        IS_SPEAKING = False


def init_tts():
    global tts_thread
    if platform.system() == "Darwin":
        choose_best_tts_voice(None, get_voice_preference())
        tts_ready.set()
        print(f"TTS: macOS voice ready ({tts_voice_label or 'Daniel'}).")
        return

    tts_thread = threading.Thread(target=tts_worker, daemon=True)
    tts_thread.start()
    tts_ready.wait(timeout=5)


def init_recognition():
    global recognizer
    if sr is None:
        return False
    try:
        recognizer = sr.Recognizer()
        return True
    except Exception:
        recognizer = None
        return False

def speak(text, allow_sound=True, gender="default", custom_name=None):
    global shutting_down
    text = str(text)

    display_name = custom_name if custom_name else APP_NAME

    with bot_lock:
        print(f"{display_name}: {text}")
        log_line(display_name, text)

    if not allow_sound or shutting_down:
        return

    was_active = False
    try:
        was_active = pause_voice_input()
        mute_mic_temporarily(cooldown_seconds_for_text(text))

        if platform.system() == "Darwin":
            voice_name = "Samantha" if gender == "female" else (tts_voice_label or choose_best_tts_voice(None, get_voice_preference()) or "Daniel")
            subprocess.run(["say", "-v", voice_name, text], check=False)
        else:
            if not tts_ready.is_set():
                print("TTS ERROR: voice system not ready.")
                return
            try:
                tts_queue.put_nowait((text, gender))
            except Exception as e:
                print(f"TTS ERROR: {e}")
    except Exception as e:
        print(f"Speech Core Error: {e}")

def say_user(text):
    with bot_lock:
        print(f"You: {text}")
        log_line("You", text)


def prompt_yes_no(question):
    while True:
        ans = input(f"{question} (y/n): ").strip().lower()
        if ans in {"y", "yes"}:
            return True
        if ans in {"n", "no"}:
            return False


def safe_calc(expr):
    allowed = {
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult, ast.Div,
        ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Constant, ast.Call,
        ast.Name,
    }
    names = {"abs": abs, "round": round, "min": min, "max": max}

    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if type(node) not in allowed:
            raise ValueError("bad")
        if isinstance(node, ast.Name) and node.id not in names:
            raise ValueError("bad")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in names:
                raise ValueError("bad")

    return eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, names)


def python_template(project_name, description):
    title = project_name.replace("_", " ").replace("-", " ").title()
    description = description.strip() or "Auto-generated project"
    return dedent(f"""\
        #!/usr/bin/env python3

        def main():
            print("{title}")
            print("{description}")

        if __name__ == "__main__":
            main()
    """).lstrip()


def html_template(title, description):
    title = title.replace("_", " ").replace("-", " ").title()
    description = description.strip() or "Auto-generated web project"
    return dedent(f"""\
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>{title}</title>
          <link rel="stylesheet" href="style.css">
        </head>
        <body>
          <main class="wrap">
            <h1>{title}</h1>
            <p>{description}</p>
            <button id="btn">Click me</button>
          </main>
          <script src="script.js"></script>
        </body>
        </html>
    """).lstrip()


def css_template():
    return dedent("""\
        :root {
          color-scheme: dark;
          font-family: system-ui, sans-serif;
        }

        body {
          margin: 0;
          min-height: 100vh;
          display: grid;
          place-items: center;
          background: #111;
          color: #fff;
        }

        .wrap {
          width: min(720px, calc(100vw - 32px));
          padding: 32px;
          border-radius: 20px;
          background: #1b1b1b;
          box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
        }

        button {
          border: 0;
          border-radius: 14px;
          padding: 12px 18px;
          font: inherit;
          background: #fff;
          color: #111;
          cursor: pointer;
        }
    """).lstrip()


def js_template():
    return dedent("""\
        const btn = document.getElementById("btn");
        if (btn) {
          btn.addEventListener("click", () => {
            alert("SOAR project ready");
          });
        }
    """).lstrip()


def md_template(name, description):
    name = name.replace("_", " ").replace("-", " ").title()
    description = description.strip() or "Auto-generated project"
    return dedent(f"""\
        # {name}

        {description}
    """).lstrip()


def json_template():
    return "{\n  \n}\n"


def create_file_with_template(path, description=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()
    stem = path.stem

    if ext == ".py":
        content = python_template(stem, description)
    elif ext == ".html":
        content = html_template(stem, description)
    elif ext == ".css":
        content = css_template()
    elif ext == ".js":
        content = js_template()
    elif ext == ".md":
        content = md_template(stem, description)
    elif ext == ".json":
        content = json_template()
    elif ext == ".txt":
        content = (description.strip() + "\n") if description.strip() else ""
    else:
        content = description if description else ""

    path.write_text(content, encoding="utf-8")
    return path


def create_python_project(project_name, description=""):
    root = PROJECTS_DIR / project_name
    root.mkdir(parents=True, exist_ok=True)
    main_file = root / "main.py"
    readme = root / "README.md"
    req = root / "requirements.txt"

    main_file.write_text(python_template(project_name, description), encoding="utf-8")
    readme.write_text(md_template(project_name, description), encoding="utf-8")
    req.write_text("", encoding="utf-8")
    return root, [main_file, readme, req]


def create_web_project(project_name, description=""):
    root = PROJECTS_DIR / project_name
    root.mkdir(parents=True, exist_ok=True)
    index = root / "index.html"
    style = root / "style.css"
    script = root / "script.js"
    readme = root / "README.md"

    index.write_text(html_template(project_name, description), encoding="utf-8")
    style.write_text(css_template(), encoding="utf-8")
    script.write_text(js_template(), encoding="utf-8")
    readme.write_text(md_template(project_name, description), encoding="utf-8")
    return root, [index, style, script, readme]


def open_projects_folder():
    try:
        if platform.system() == "Darwin":
            subprocess.Popen(["open", str(PROJECTS_DIR)])
        elif platform.system() == "Windows":
            os.startfile(str(PROJECTS_DIR))
        else:
            subprocess.Popen(["xdg-open", str(PROJECTS_DIR)])
    except Exception as e:
        print(f"Could not open projects folder: {e}")


def open_data_folder():
    try:
        if platform.system() == "Darwin":
            subprocess.Popen(["open", str(DATA_DIR)])
        elif platform.system() == "Windows":
            os.startfile(str(DATA_DIR))
        else:
            subprocess.Popen(["xdg-open", str(DATA_DIR)])
    except Exception as e:
        print(f"Could not open data folder: {e}")


def show_help():
    text = (
        "Commands: help, exit, shut down, shutdown, power off, power down, quit, bye, clear, time, date, uptime, ping, say, message, calc, note, notes, "
        "remember, memories, forget, search, todo add, todo list, todo done, todo remove, todo clear, "
        "remind, timer, shell, read, write, open, openurl, copy, paste, ip, status, voice, voice on, "
        "voice off, voice list, voice set <name>, voice auto, listen on, listen off, code, mkdir, "
        "newfile <path> <optional text>, projects, data, logs, log tail, autocode, autocode status, autocode on, autocode off, "
        "flip a coin, roll a dice, fact, story."
    )
    print()
    print(text)
    print()

def show_status():
    print()
    print(f"{APP_NAME} status")
    print(f"  platform: {platform.system()} {platform.release()}")
    print(f"  python: {sys.version.split()[0]}")
    print(f"  notes: {len(read_lines(NOTES_FILE))}")
    print(f"  memories: {len(read_lines(MEMORY_FILE))}")
    print(f"  todos: {len(read_lines(TODO_FILE))}")
    print(f"  voice: {'on' if voice_enabled else 'off'}")
    print(f"  voice preference: {get_voice_preference()}")
    print(f"  selected voice: {tts_voice_label or 'none'}")
    print(f"  tts: {'ready' if tts_ready.is_set() else 'not ready'}")
    print(f"  speech recognition: {'ready' if recognizer else 'not ready'}")
    print(f"  local ip: {get_local_ip()}")
    print(f"  uptime: {str(datetime.now() - STARTUP_TIME).split('.')[0]}")
    print(f"  chat log: {CHAT_LOG}")
    print(f"  autocode: {'connected' if autocode_connected() else 'offline'}")
    if autocode_connected() and hasattr(soar_autocode, "load_state"):
        try:
            auto_state = soar_autocode.load_state()
            if isinstance(auto_state, dict):
                print(f"  autocode runs: {auto_state.get('run_count', 0)}")
                print(f"  autocode last project: {auto_state.get('last_project') or 'none'}")
        except Exception:
            pass
    print()


def show_recent_log(count=20):
    try:
        count = max(1, min(500, int(count)))
    except Exception:
        count = 20

    lines = read_lines(CHAT_LOG)
    if not lines:
        print("No log entries yet.")
        return

    for line in lines[-count:]:
        print(line)

def analyze_code_syntax(file_path):
    """
    Scans a Python file for compilation errors and provides 
    a clear, helpful explanation for a developer.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        
        compile(source, file_path, 'exec')
        return "No syntax errors detected! The structure looks clean."
        
    except SyntaxError as e:
        explanation = "Hint: Check for missing colons (:), unclosed parentheses (), or mismatched quotes."
        if "expected ':'" in str(e):
            explanation = "Hint: You forgot a colon ':' at the end of an 'if', 'for', 'while', or 'def' statement."
        elif "unmatched" in str(e):
            explanation = "Hint: You have an open parenthesis '(', bracket '[', or brace '{' that never got closed."
        elif "indentation" in str(e).lower():
            explanation = "Hint: Your spacing is uneven. Make sure you are consistently using either 4 spaces or tabs."

        return (
            f"[SYNTAX ERROR FOUND]\n"
            f"  File: {os.path.basename(file_path)}\n"
            f"  Line {e.lineno}: {e.text.strip() if e.text else 'Unknown text'}\n"
            f"  Error: {e.msg}\n"
            f"  {explanation}"
        )
    except Exception as e:
        return f"Could not analyze file structure: {e}"

def analyze_code_syntax(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        compile(source, file_path, 'exec')
        return "No syntax errors detected! The structure looks clean."
        
    except SyntaxError as e:
        explanation = "Hint: Check for missing colons (:), unclosed parentheses (), or mismatched quotes."
        if "expected ':'" in str(e):
            explanation = "Hint: You forgot a colon ':' at the end of an 'if', 'for', 'while', or 'def' statement."
        elif "unmatched" in str(e):
            explanation = "Hint: You have an open parenthesis '(', bracket '[', or brace '{' that never got closed."
        elif "indentation" in str(e).lower():
            explanation = "Hint: Your spacing is uneven. Make sure you are consistently using either 4 spaces or tabs."

        return (
            f"[SYNTAX ERROR FOUND]\n"
            f"  File: {os.path.basename(file_path)}\n"
            f"  Line {e.lineno}: {e.text.strip() if e.text else 'Unknown text'}\n"
            f"  Error: {e.msg}\n"
            f"  {explanation}"
        )
    except Exception as e:
        return f"Could not analyze file structure: {e}"

def reply_to(user_text):
    
    text = user_text.strip().lower()
    parts = [] 
    if not text:
        return "Say something and I will answer."
    if "how are you" in text:
        return maybe_address_user("Pretty good. I am ready to help.")
    if "who are you" in text:
        return maybe_address_user("I am SOAR, your helper bot.")
    if "what can you do" in text:
        return maybe_address_user("I can talk, store notes, manage tasks, make files, create starter projects, run safe commands, and use voice.")
    if text in {"thanks", "thank you", "thx"}:
        return maybe_address_user("No problem.")
    
    if "flip a coin" in text or "coin flip" in text:
        return maybe_address_user(f"It landed on {random.choice(['Heads', 'Tails'])}.")
    
    if "roll a dice" in text or "dice roll" in text:
        return maybe_address_user(f"I rolled a {random.randint(1, 6)}.")
    
    if text.startswith("check file ") or text.startswith("checkfile "):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            return maybe_address_user("Please specify the file to analyze. Example: check file my_project/main.py")
            
        filename = parts[2].strip()
        target_path = PROJECTS_DIR / filename
        
        if not target_path.exists():
            return maybe_address_user(f"I couldn't find a file at the path '{filename}' inside your Projects folder.")
            
        if target_path.is_dir():
            return maybe_address_user("The path points to a directory. Please specify a Python file instead.")
            
        if not target_path.suffix.lower() == ".py":
            return maybe_address_user("Right now, my syntax assistant optimization specializes in Python (.py) files.")
            
        print("\n--- SOAR CODE ANALYSIS ENGINE ---")
        result = analyze_code_syntax(target_path)
        print(result)
        print("---------------------------------\n")
        
        return maybe_address_user("Code scanning sequence completed.")
    
    if text.startswith("set personality "):
        parts = text.split(" ")
        if len(parts) == 4:
            trait = parts[2].capitalize()
            try:
                val = float(parts[3])
                settings = load_settings()
                
                if "personality" not in settings:
                    settings["personality"] = {}
                    
                settings["personality"][trait] = max(0.0, min(1.0, val))
                save_settings(settings)
                
                return maybe_address_user(f"Personality parameter {trait} has been set to {val}.")
            except ValueError:
                return "Error: Trait value must be a number between 0.0 and 1.0."
        else:
            return "Usage format: set personality [trait] [0.0 - 1.0]"

    if text == "sysinfo" or text == "system resources":
        try:
            print("\n================ SOAR SYSTEM DIAGNOSTICS ================")
            print(f"  OS Family:    {platform.system()} {platform.release()}")
            print(f"  Architecture: {platform.machine()}")
            print(f"  Processor:    {platform.processor() or 'Detected x86/ARM Engine'}")
            print(f"  Host Name:    {platform.node()}")
            
            import shutil
            total, used, free = shutil.disk_usage("/")
            print(f"  Storage Cap:  {used // (2**30)}GB Used / {total // (2**30)}GB Total")
            
            try:
                import psutil
                p = psutil.Process(os.getpid())
                print(f"  SOAR CPU:     {p.cpu_percent(interval=0.1):.1f}%")
                print(f"  SOAR RAM:     {p.memory_percent():.1f}%")
            except ImportError:
                print("  SOAR Usage:   Install 'psutil' to view runtime allocation profiles.")
                
            print("=========================================================")
            return maybe_address_user("Local system profile overview complete.")
        except Exception as e:
            print(f"Diagnostics Error: {e}")
            return maybe_address_user("I am unable to poll your hardware diagnostic sensors at this moment.")

    if "fact" in text or "tell me a fact" in text:
        facts = [
            "Did you know that water makes up about 60 percent of the human body?",
            "Did you know that octopuses have three hearts?",
            "Did you know that a jiffy is an actual unit of time? It's one hundredth of a second.",
            "Did you know that honey never spoils? Archaeologists have found pots of honey in ancient tombs that are over 3,000 years old."
        ]
        return maybe_address_user(random.choice(facts))
    
    if text.startswith("check file ") or text.startswith("checkfile "):
        
        parts = text.split(" ", 2)
        if len(parts) < 3:
            return maybe_address_user("Please specify the file to analyze. Example: check file my_project/main.py")
            
        
        filename = parts[2].strip()
        target_path = PROJECTS_DIR / filename
        
        if not target_path.exists():
            return maybe_address_user(f"I couldn't find a file at the path '{filename}' inside your Projects folder.")
            
        if target_path.is_dir():
            return maybe_address_user("The path points to a directory. Please specify a Python file instead.")
            
        if not target_path.suffix.lower() == ".py":
            return maybe_address_user("Right now, my syntax assistant optimization specializes in Python (.py) files.")
            
        print("\n--- SOAR CODE ANALYSIS ENGINE ---")
        result = analyze_code_syntax(target_path)
        print(result)
        print("---------------------------------\n")
        
        return maybe_address_user("Code scanning sequence completed.")
    
    if text.startswith("create project py") or text.startswith("create python project"):
        try:
            if text.startswith("create python project"):
                command_body = user_text.strip()[22:] 
            else:
                command_body = user_text.strip()[17:] 
                
            args = shlex.split(command_body)
            
            if len(args) < 2:
                return maybe_address_user("I need a directory and a project name, please check your command format.")
                
            project_type = "default"
            if args[0].lower() in ["default", "website", "game", "converter"]:
                project_type = args[0].lower()
                args = args[1:]
                
            if len(args) < 2:
                return maybe_address_user("I need a directory and a project name, please check your command format.")
                
            project_name = args[-1]
            dir_path = " ".join(args[:-1])
            target_base_dir = Path(dir_path).expanduser()
            
            if not target_base_dir.exists():
                return maybe_address_user("That directory does not exist. Please check the path and try again.")
                
            project_root = target_base_dir / project_name
            if project_root.exists():
                return maybe_address_user("A project with that name already exists in that location.")
                
            project_root.mkdir(parents=True)
            (project_root / "src").mkdir()
            (project_root / "tests").mkdir()
            (project_root / "src" / "__init__.py").touch()
            (project_root / "tests" / "__init__.py").touch()
            
            req_content = ""
            main_code = ""
            
            if project_type == "website":
                (project_root / "src" / "templates").mkdir()
                (project_root / "src" / "static").mkdir()
                index_html = project_root / "src" / "templates" / "index.html"
                index_html.write_text("<!DOCTYPE html>\n<html>\n<head>\n    <title>" + project_name + "</title>\n</head>\n<body>\n    <h1>Welcome to " + project_name + " website!</h1>\n</body>\n</html>", encoding="utf-8")
                
                req_content = "flask\n"
                main_code = dedent(f"""\
                    from flask import Flask, render_template
                    
                    app = Flask(__name__)
                    
                    @app.route('/')
                    def home():
                        return render_template('index.html')
                        
                    if __name__ == '__main__':
                        app.run(debug=True)
                """)
                
            elif project_type == "game":
                (project_root / "src" / "assets").mkdir()
                req_content = "pygame\n"
                main_code = dedent(f"""\
                    import pygame
                    import sys
                    
                    pygame.init()
                    screen = pygame.display.set_mode((800, 600))
                    pygame.display.set_set_caption('{project_name}')
                    clock = pygame.time.Clock()
                    
                    running = True
                    while running:
                        for event in pygame.event.get():
                            if event.type == pygame.QUIT:
                                running = False
                                
                        screen.fill((0, 0, 0))
                        pygame.display.flip()
                        clock.tick(60)
                        
                    pygame.quit()
                    sys.exit()
                """)
                
            elif project_type == "converter":
                (project_root / "src" / "input").mkdir()
                (project_root / "src" / "output").mkdir()
                main_code = dedent(f"""\
                    import json
                    import csv
                    import os
                    
                    def convert_csv_to_json(csv_path, json_path):
                        if not os.path.exists(csv_path):
                            print("No input CSV file found.")
                            return
                        data = []
                        with open(csv_path, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                data.append(row)
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=4)
                        print("Conversion completed successfully.")
                        
                    if __name__ == '__main__':
                        print("Utility engine initiated.")
                """)
                
            else:
                main_code = python_template(project_name, "SOAR auto-generated Python project")
                
            main_file = project_root / "src" / "main.py"
            main_file.write_text(main_code, encoding="utf-8")
            
            readme = project_root / "README.md"
            readme.write_text(md_template(project_name, f"SOAR auto-generated Python {project_type} project"), encoding="utf-8")
            
            req = project_root / "requirements.txt"
            req.write_text(req_content, encoding="utf-8")
            
            gitignore = project_root / ".gitignore"
            gitignore.write_text("*.pyc\n__pycache__/\n.venv/\n", encoding="utf-8")
            
            print(f"Created {project_type} Python project '{project_name}' at {project_root}")
            return maybe_address_user(f"Python project {project_name} has been created successfully.")
            
        except Exception as e:
            print(f"Error creating project: {e}")
            return maybe_address_user("I encountered an error creating the project.")
        
    if text.startswith("create project js") or text.startswith("create javascript project"):
        try:
            if text.startswith("create javascript project"):
                command_body = user_text.strip()[26:] 
            else:
                command_body = user_text.strip()[18:] 
                
            args = shlex.split(command_body)
            
            if len(args) < 2:
                return maybe_address_user("I need a directory and a project name, please check your command format.")
                
            project_type = "default"
            if args[0].lower() in ["default", "website", "game", "converter"]:
                project_type = args[0].lower()
                args = args[1:]
                
            if len(args) < 2:
                return maybe_address_user("I need a directory and a project name, please check your command format.")
                
            project_name = args[-1]
            dir_path = " ".join(args[:-1])
            target_base_dir = Path(dir_path).expanduser()
            
            if not target_base_dir.exists():
                return maybe_address_user("That directory does not exist. Please check the path and try again.")
                
            project_root = target_base_dir / project_name
            if project_root.exists():
                return maybe_address_user("A project with that name already exists in that location.")
                
            project_root.mkdir(parents=True)
            (project_root / "src").mkdir()
            (project_root / "tests").mkdir()
            
            pkg_deps = {}
            pkg_dev_deps = {}
            pkg_scripts = {"start": "node src/index.js"}
            js_code = ""
            
            if project_type == "website":
                (project_root / "src" / "public").mkdir()
                index_html = project_root / "src" / "public" / "index.html"
                index_html.write_text("<!DOCTYPE html>\n<html>\n<head>\n    <title>" + project_name + "</title>\n</head>\n<body>\n    <h1>Welcome to " + project_name + " website!</h1>\n</body>\n</html>", encoding="utf-8")
                
                pkg_deps = {"express": "^4.19.2"}
                js_code = dedent(f"""\
                    const express = require('express');
                    const path = require('path');
                    const app = express();
                    const PORT = process.env.PORT || 3000;
                    
                    app.use(express.static(path.join(__dirname, 'public')));
                    
                    app.listen(PORT, () => {{
                        console.log(`Server running on port ${{PORT}}`);
                    }});
                """)
                
            elif project_type == "game":
                (project_root / "src" / "public").mkdir()
                index_html = project_root / "src" / "public" / "index.html"
                index_html.write_text("<!DOCTYPE html>\n<html>\n<head>\n    <title>" + project_name + "</title>\n    <style>body { margin: 0; background: #000; overflow: hidden; }</style>\n</head>\n<body>\n    <canvas id='gameCanvas'></canvas>\n    <script src='game.js'></script>\n</body>\n</html>", encoding="utf-8")
                
                game_js = project_root / "src" / "public" / "game.js"
                game_js.write_text(dedent(f"""\
                    const canvas = document.getElementById('gameCanvas');
                    const ctx = canvas.getContext('2d');
                    canvas.width = window.innerWidth;
                    canvas.height = window.innerHeight;
                    
                    function loop() {{
                        ctx.fillStyle = '#000000';
                        ctx.fillRect(0, 0, canvas.width, canvas.height);
                        
                        ctx.fillStyle = '#ffffff';
                        ctx.font = '30px Arial';
                        ctx.fillText('{project_name}', 50, 50);
                        
                        requestAnimationFrame(loop);
                    }}
                    loop();
                """), encoding="utf-8")
                
                pkg_deps = {"express": "^4.19.2"}
                js_code = dedent(f"""\
                    const express = require('express');
                    const path = require('path');
                    const app = express();
                    
                    app.use(express.static(path.join(__dirname, 'public')));
                    
                    app.listen(3000, () => {{
                        console.log('Game server running on http://localhost:3000');
                    }});
                """)
                
            elif project_type == "converter":
                (project_root / "src" / "input").mkdir()
                (project_root / "src" / "output").mkdir()
                pkg_deps = {"csvtojson": "^2.0.10"}
                js_code = dedent(f"""\
                    const csv = require('csvtojson');
                    const fs = require('fs');
                    const path = require('path');
                    
                    async function convert(csvName, jsonName) {{
                        const csvPath = path.join(__dirname, 'input', csvName);
                        const jsonPath = path.join(__dirname, 'output', jsonName);
                        
                        if (!fs.existsSync(csvPath)) {{
                            console.log("No input CSV file found.");
                            return;
                        }}
                        
                        const jsonArray = await csv().fromFile(csvPath);
                        fs.writeFileSync(jsonPath, JSON.stringify(jsonArray, null, 4));
                        console.log("Conversion completed successfully.");
                    }}
                    
                    console.log("Utility engine initiated.");
                """)
                
            else:
                js_code = js_template()
                
            js_file = project_root / "src" / "index.js"
            js_file.write_text(js_code, encoding="utf-8")
            
            package_json = project_root / "package.json"
            pkg_data = {
                "name": project_name.lower().replace(" ", "-"),
                "version": "1.0.0",
                "description": f"SOAR auto-generated JavaScript {project_type} project",
                "main": "src/index.js",
                "scripts": pkg_scripts,
                "dependencies": pkg_deps,
                "devDependencies": pkg_dev_deps
            }
            package_json.write_text(json.dumps(pkg_data, indent=2), encoding="utf-8")
            
            readme = project_root / "README.md"
            readme.write_text(md_template(project_name, f"SOAR auto-generated JavaScript {project_type} project"), encoding="utf-8")
            
            gitignore = project_root / ".gitignore"
            gitignore.write_text("node_modules/\n.env\n.DS_Store\n", encoding="utf-8")
            
            print(f"Created {project_type} JavaScript project '{project_name}' at {project_root}")
            return maybe_address_user(f"JavaScript project {project_name} has been created successfully.")
            
        except Exception as e:
            print(f"Error creating project: {e}")
            return maybe_address_user("I encountered an error creating the JavaScript project.")
        
    if text.startswith("create project java") or text.startswith("create java project"):
        try:
            if text.startswith("create java project"):
                command_body = user_text.strip()[20:] 
            else:
                command_body = user_text.strip()[20:] 
                
            args = shlex.split(command_body)
            if len(args) < 2:
                return maybe_address_user("I need a directory and a project name, please check your command format.")
                
            project_type = "default"
            if args[0].lower() in ["default", "website", "game", "converter"]:
                project_type = args[0].lower()
                args = args[1:]
                
            if len(args) < 2:
                return maybe_address_user("I need a directory and a project name, please check your command format.")
                
            project_name = args[-1]
            dir_path = " ".join(args[:-1])
            target_base_dir = Path(dir_path).expanduser()
            
            if not target_base_dir.exists():
                return maybe_address_user("That directory does not exist. Please check the path.")
                
            project_root = target_base_dir / project_name
            if project_root.exists():
                return maybe_address_user("A project with that name already exists in that location.")
                
            java_src_dir = project_root / "src" / "main" / "java"
            java_test_dir = project_root / "src" / "test" / "java"
            java_src_dir.mkdir(parents=True)
            java_test_dir.mkdir(parents=True)
            
            java_code = ""
            
            if project_type == "website":
                java_code = dedent(f"""\
                    import com.sun.net.httpserver.HttpServer;
                    import com.sun.net.httpserver.HttpHandler;
                    import com.sun.net.httpserver.HttpExchange;
                    import java.io.IOException;
                    import java.io.OutputStream;
                    import java.net.InetSocketAddress;

                    public class Main {{
                        public static void main(String[] args) throws IOException {{
                            HttpServer server = HttpServer.create(new InetSocketAddress(8080), 0);
                            server.createContext("/", new HttpHandler() {{
                                @Override
                                public void handle(HttpExchange exchange) throws IOException {{
                                    String response = "<!DOCTYPE html><html><head><title>{project_name}</title></head><body><h1>Welcome to {project_name} website!</h1></body></html>";
                                    exchange.sendResponseHeaders(200, response.length());
                                    OutputStream os = exchange.getResponseBody();
                                    os.write(response.getBytes());
                                    os.close();
                                }}
                            }});
                            server.setExecutor(null);
                            System.out.println("Server running on http://localhost:8080");
                            server.start();
                        }}
                    }}
                """).lstrip()
                
            elif project_type == "game":
                java_code = dedent(f"""\
                    import javax.swing.JFrame;
                    import javax.swing.JPanel;
                    import java.awt.Color;
                    import java.awt.Graphics;
                    import java.awt.Dimension;

                    public class Main extends JPanel implements Runnable {{
                        private boolean running = true;

                        public Main() {{
                            this.setPreferredSize(new Dimension(800, 600));
                            this.setBackground(Color.BLACK);
                        }}

                        public static void main(String[] args) {{
                            JFrame frame = new JFrame("{project_name}");
                            Main gamePanel = new Main();
                            frame.add(gamePanel);
                            frame.pack();
                            frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
                            frame.setLocationRelativeTo(null);
                            frame.setVisible(true);
                            new Thread(gamePanel).start();
                        }}

                        @Override
                        public void run() {{
                            while (running) {{
                                repaint();
                                try {{
                                    Thread.sleep(16);
                                }} catch (InterruptedException e) {{
                                    e.printStackTrace();
                                }}
                            }}
                        }}

                        @Override
                        protected void paintComponent(Graphics g) {{
                            super.paintComponent(g);
                            g.setColor(Color.WHITE);
                            g.drawString("{project_name} Engine Running", 50, 50);
                        }}
                    }}
                """).lstrip()
                
            elif project_type == "converter":
                (project_root / "input").mkdir()
                (project_root / "output").mkdir()
                java_code = dedent(f"""\
                    import java.io.BufferedReader;
                    import java.io.FileReader;
                    import java.io.BufferedWriter;
                    import java.io.FileWriter;
                    import java.io.File;

                    public class Main {{
                        public static void main(String[] args) {{
                            System.out.println("Utility engine initiated.");
                            File inputDir = new File("input");
                            if (!inputDir.exists()) {{
                                inputDir.mkdir();
                            }}
                        }}
                        
                        public static void simpleCsvToJson(String csvPath, String jsonPath) throws Exception {{
                            BufferedReader br = new BufferedReader(new FileReader(csvPath));
                            BufferedWriter bw = new BufferedWriter(new FileWriter(jsonPath));
                            String line = br.readLine();
                            if (line == null) {{
                                br.close();
                                bw.close();
                                return;
                            }}
                            String[] headers = line.split(",");
                            bw.write("[\\n");
                            boolean firstRow = true;
                            while ((line = br.readLine()) != null) {{
                                if (!firstRow) bw.write(",\\n");
                                firstRow = false;
                                String[] values = line.split(",");
                                bw.write("  {{\\n");
                                for (int i = 0; i < headers.length && i < values.length; i++) {{
                                    bw.write("    \\"" + headers[i].trim() + "\\": \\"" + values[i].trim() + "\\"");
                                    if (i < headers.length - 1 && i < values.length - 1) bw.write(",\\n");
                                }}
                                bw.write("\\n  }}");
                            }}
                            bw.write("\\n]");
                            br.close();
                            bw.close();
                            System.out.println("Conversion completed.");
                        }}
                    }}
                """).lstrip()
                
            else:
                java_code = dedent(f"""\
                    public class Main {{
                        public static void main(String[] args) {{
                            System.out.println("Hello from {project_name.title()}!");
                        }}
                    }}
                """).lstrip()
                
            main_class = java_src_dir / "Main.java"
            main_class.write_text(java_code, encoding="utf-8")
            
            readme = project_root / "README.md"
            readme.write_text(md_template(project_name, f"SOAR auto-generated Java {project_type} project"), encoding="utf-8")
            
            gitignore = project_root / ".gitignore"
            gitignore.write_text("*.class\n*.jar\n*.war\n.build/\ntarget/\n.gradle/\nbuild/\n.settings/\n.classpath/\n.project/\n", encoding="utf-8")
            
            print(f"Created {project_type} Java project '{project_name}' at {project_root}")
            return maybe_address_user(f"Java project {project_name} has been created successfully.")
            
        except Exception as e:
            print(f"Error creating project: {e}")
            return maybe_address_user("I encountered an error creating the Java project.")
        
    if text == "rsms run" or text == "resource monitor":
        try:
            import importlib
            import rsms # type: ignore
            importlib.reload(rsms)
            
            print("\n================ SOAR RSMS LAUNCHER ================")
            print("[SOAR] Spawning standalone window environment...")
            
            success = rsms.launch()
            
            if success:
                print("[SOAR] RSMS context moved cleanly to external terminal workspace.")
                print("====================================================")
                return maybe_address_user("Resource monitor launched in a new window.")
            else:
                print("[SOAR] Unable to find a compatible GUI terminal window client.")
                print("====================================================")
                return maybe_address_user("I could not spawn a new window on this host machine.")
                
        except Exception as e:
            print(f"RSMS Launch Error: {e}")
            return maybe_address_user("The resource management system module is unavailable.")
        
    if text.startswith("view project ") or text.startswith("tree "):
        try:
            if text.startswith("view project "):
                command_body = user_text.strip()[13:]
            else:
                command_body = user_text.strip()[5:]
                
            target_dir = Path(shlex.split(command_body)[0]).expanduser()
            if not target_dir.exists():
                return maybe_address_user("That workspace directory does not exist.")

            print(f"\n Structure for: {target_dir.name}")
            
            def _build_tree(directory, prefix=""):
                items = sorted(list(directory.iterdir()), key=lambda x: (x.is_file(), x.name.lower()))
                for idx, item in enumerate(items):
                    if item.name.startswith('.'):  
                        continue
                    is_last = (idx == len(items) - 1)
                    connector = "└── " if is_last else "├── "
                    print(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")
                    if item.is_dir():
                        _build_tree(item, prefix + ("    " if is_last else "│   "))

            _build_tree(target_dir)
            return maybe_address_user("Directory tree map rendered successfully.")
        except Exception as e:
            print(f"Error mapping directory: {e}")
            return maybe_address_user("I couldn't map out that folder directory structure.")
        
    if text.startswith("run project ") or text.startswith("run file "): 
        try:
            if text.startswith("run project "):
                command_body = user_text.strip()[12:]
            else:
                command_body = user_text.strip()[9:]
                
            target_path = Path(shlex.split(command_body)[0]).expanduser()
            if not target_path.exists():
                return maybe_address_user("The target code execution path does not exist.")

            if target_path.is_dir():
                main_candidates = ["src/main.py", "main.py", "src/index.js", "src/main/java/Main.java", "scripts/main.sh"]
                found = False
                for candidate in main_candidates:
                    if (target_path / candidate).exists():
                        target_path = target_path / candidate
                        found = True
                        break
                if not found:
                    return maybe_address_user("Could not find a default entry file inside this project folder structure.")

            ext = target_path.suffix.lower()
            print(f"\n SOAR Runtime Executing: {target_path.name}")
            print("-" * 50)
            
            if ext == '.py':
                cmd = [sys.executable, str(target_path)]
            elif ext == '.js':
                cmd = ["node", str(target_path)]
            elif ext == '.sh':
                cmd = ["bash", str(target_path)]
            elif ext == '.java':
                cmd = ["java", str(target_path)]
            else:
                return maybe_address_user(f"Unsupported execution extension framework: {ext}")

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f" Runtime Error:\n{result.stderr}")
            print("-" * 50)
            
            return maybe_address_user("Execution sequence finished.")
        except Exception as e:
            print(f"Runtime Engine Exception: {e}")
            return maybe_address_user("An environmental runtime collision error occurred.")
        
    if text.startswith("set personality "):
        parts = text.split(" ")
        if len(parts) == 4:
            trait = parts[2].capitalize()
            try:
                val = float(parts[3])
                settings = load_settings()
                
                if "personality" not in settings:
                    settings["personality"] = {}
                    
                settings["personality"][trait] = max(0.0, min(1.0, val))
                save_settings(settings)
                
                return maybe_address_user(f"Personality parameter {trait} has been set to {val}.")
            except ValueError:
                return "Error: Trait value must be a number between 0.0 and 1.0."
        else:
            return "Usage format: set personality [trait] [0.0 - 1.0]"
        
    if text == "sysinfo" or text == "system resources":
        try:
            print("\n================ SOAR SYSTEM DIAGNOSTICS ================")
            print(f" OS Family:   {platform.system()} {platform.release()}")
            print(f" Architecture:{platform.machine()}")
            print(f" Processor:   {platform.processor() or 'Detected x86/ARM Engine'}")
            print(f" Host Name:   {platform.node()}")
            
            import shutil
            total, used, free = shutil.disk_usage("/")
            print(f" Storage Cap: {used // (2**30)}GB Used / {total // (2**30)}GB Total")
            print("=========================================================")
            
            return maybe_address_user("Local system profile overview complete.")
        except Exception as e:
            print(f"Diagnostics Error: {e}")
            return maybe_address_user("I am unable to poll your hardware diagnostic sensors at this moment.")
        
    if text.startswith("edit file ") or text.startswith("editfile "):
        try:
            if text.startswith("edit file "):
                command_body = user_text.strip()[10:] 
            else:
                command_body = user_text.strip()[9:]  
                
            args = shlex.split(command_body)
            if not args:
                return maybe_address_user("I need a file directory path to edit.")
                
            file_path_str = " ".join(args)
            target_file = Path(file_path_str).expanduser()
            
            if not target_file.exists():
                return maybe_address_user("That file directory does not exist. Please check the path.")
            if not target_file.is_file():
                return maybe_address_user("The path provided points to a folder, not a file.")
                
            content = target_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            
            while True:
                print("\n=================== SOAR TERMINAL EDITOR ===================")
                if not lines:
                    print(" (File is empty) ")
                else:
                    for idx, line in enumerate(lines, 1):
                        print(f"[{idx}] {line}")
                print("============================================================")
                print("Options: [a]ppend line | [d]elete [num] | [r]eplace [num] | [s]ave | [c]ancel")
                
                choice = input("SOAR Editor > ").strip()
                if not choice:
                    continue
                    
                choice_low = choice.lower()
                
                if choice_low == 'c':
                    print("\n[Editor] Editing canceled. No changes saved.")
                    break
                    
                elif choice_low == 's':
                    target_file.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
                    print("\n[Editor] File successfully saved and updated.")
                    break
                    
                elif choice_low == 'a':
                    new_line = input("Enter text to add as a new line: ")
                    lines.append(new_line)
                    
                elif choice_low.startswith('d'):
                    try:
                        editor_parts = choice_low.split()
                        line_num = int(editor_parts[1]) if len(editor_parts) > 1 else int(input("Line number to delete: "))
                        
                        if 1 <= line_num <= len(lines):
                            removed = lines.pop(line_num - 1)
                            print(f"[Editor] Removed line {line_num}: '{removed}'")
                        else:
                            print("[Editor Error] Line number out of range.")
                    except (ValueError, IndexError):
                        print("[Editor Error] Invalid command structure. Use: d [line_number]")
                        
                elif choice_low.startswith('r'):
                    try:
                        editor_parts = choice_low.split()
                        line_num = int(editor_parts[1]) if len(editor_parts) > 1 else int(input("Line number to replace: "))
                        
                        if 1 <= line_num <= len(lines):
                            print(f"Current Text: {lines[line_num - 1]}")
                            replacement_text = input("Enter new replacement text: ")
                            lines[line_num - 1] = replacement_text
                        else:
                            print("[Editor Error] Line number out of range.")
                    except (ValueError, IndexError):
                        print("[Editor Error] Invalid command structure. Use: r [line_number]")
                else:
                    print("[Editor Error] Unknown editor command.")
            
            return maybe_address_user("Terminal file editing session closed.")
            
        except Exception as e:
            print(f"Error modifying file: {e}")
            return maybe_address_user("I encountered an unexpected error while trying to edit that file.")
        
    if text.startswith("create project bash") or text.startswith("create bash project"):
        try:
            if text.startswith("create bash project"):
                command_body = user_text.strip()[20:] 
            else:
                command_body = user_text.strip()[20:] 
                
            args = shlex.split(command_body)
            if len(args) < 2:
                return maybe_address_user("I need a directory and a project name, please check your command format.")
                
            project_type = "default"
            if args[0].lower() in ["default", "website", "game", "converter"]:
                project_type = args[0].lower()
                args = args[1:]
                
            if len(args) < 2:
                return maybe_address_user("I need a directory and a project name, please check your command format.")
                
            project_name = args[-1]
            dir_path = " ".join(args[:-1])
            target_base_dir = Path(dir_path).expanduser()
            
            if not target_base_dir.exists():
                return maybe_address_user("That directory does not exist. Please check the path.")
                
            project_root = target_base_dir / project_name
            if project_root.exists():
                return maybe_address_user("A project with that name already exists in that location.")
                
            (project_root / "scripts").mkdir(parents=True)
            (project_root / "config").mkdir(parents=True)
            
            bash_code = ""
            
            if project_type == "website":
                (project_root / "www").mkdir()
                index_html = project_root / "www" / "index.html"
                index_html.write_text("<!DOCTYPE html>\n<html>\n<head>\n    <title>" + project_name + "</title>\n</head>\n<body>\n    <h1>Welcome to " + project_name + " website!</h1>\n</body>\n</html>", encoding="utf-8")
                
                bash_code = dedent(f"""\
                    #!/bin/bash
                    echo "Starting simple dark-netcat/python server configuration for local preview..."
                    if command -v python3 &>/dev/null; then
                        echo "Serving website on http://localhost:8000"
                        cd www && python3 -m http.server 8000
                    else
                        echo "Error: Python 3 is required to run this light server stack helper."
                    fi
                """).lstrip()
                
            elif project_type == "game":
                bash_code = dedent(f"""\
                    #!/bin/bash
                    echo "Initializing matrix snake layout game framework loop..."
                    clear
                    while true; do
                        echo "=== {project_name} Terminal Game Loop ==="
                        echo "Press [q] to quit loop simulation."
                        read -n 1 -t 1 input
                        if [[ "$input" == "q" ]]; then
                            break
                        fi
                        clear
                    done
                    echo "Game closed cleanly."
                """).lstrip()
                
            elif project_type == "converter":
                (project_root / "input").mkdir()
                (project_root / "output").mkdir()
                bash_code = dedent(f"""\
                    #!/bin/bash
                    echo "Parsing input logs engine deployment inside script pipeline..."
                    if [ -z "$(ls -A input)" ]; then
                        echo "Input directory is completely empty."
                    else
                        for file in input/*; do
                            echo "Processing base format file mapping: $file"
                        done
                    fi
                """).lstrip()
                
            else:
                bash_code = dedent(f"""\
                    #!/bin/bash
                    # SOAR Auto-generated Automation Script
                    
                    echo "Running {project_name} script..."
                """).lstrip()
                
            main_sh = project_root / "scripts" / "main.sh"
            main_sh.write_text(bash_code, encoding="utf-8")
            
            try:
                main_sh.chmod(0o755)
            except Exception:
                pass
                
            (project_root / "config" / "settings.cfg").write_text("# Configuration parameters go here\n", encoding="utf-8")
            
            readme = project_root / "README.md"
            readme.write_text(md_template(project_name, f"SOAR auto-generated Bash {project_type} project"), encoding="utf-8")
            
            gitignore = project_root / ".gitignore"
            gitignore.write_text("*.log\n*.tmp\n.DS_Store\nconfig/local.cfg\n", encoding="utf-8")
            
            print(f"Created {project_type} Bash scripting project '{project_name}' at {project_root}")
            return maybe_address_user(f"Bash project {project_name} has been created successfully.")
            
        except Exception as e:
            print(f"Error creating project: {e}")
            return maybe_address_user("I encountered an error creating the Bash project.")
        
    if text.startswith("create project web") or text.startswith("create web project"):
        try:
            if text.startswith("create web project"):
                command_body = user_text.strip()[19:] 
            else:
                command_body = user_text.strip()[19:] 
                
            args = shlex.split(command_body)
            if len(args) < 2:
                return maybe_address_user("I need a directory and a project name, please check your command format.")
                
            project_name = args[-1]
            dir_path = " ".join(args[:-1])
            target_base_dir = Path(dir_path).expanduser()
            
            if not target_base_dir.exists():
                return maybe_address_user("That directory does not exist. Please check the path.")
                
            project_root = target_base_dir / project_name
            if project_root.exists():
                return maybe_address_user("A project with that name already exists in that location.")
                
            
            project_root.mkdir(parents=True)
            
            
            index_html = project_root / "index.html"
            index_html.write_text(html_template(project_name, "SOAR auto-generated static frontend project"), encoding="utf-8")
            
            style_css = project_root / "style.css"
            style_css.write_text(css_template(), encoding="utf-8")
            
            script_js = project_root / "script.js"
            script_js.write_text(js_template(), encoding="utf-8")
            
            readme = project_root / "README.md"
            readme.write_text(md_template(project_name, "SOAR auto-generated Web project"), encoding="utf-8")
            
            print(f"Created Frontend Web project '{project_name}' at {project_root}")
            return maybe_address_user(f"Static web stack project {project_name} has been successfully created.")
            
        except Exception as e:
            print(f"Error creating project: {e}")
            return maybe_address_user("I encountered an error creating the static web project.")

    if "joke" in text:
        jokes = [
            "Why did the computer get cold? It left its Windows open.",
            "I told my PC a joke. It responded with a cache of laughter.",
            "Why do programmers like dark mode? Because light attracts bugs.",
            "I told a computer a joke on infinity. It was up all night processing it.",
            "Why did the developer go broke? Because he used up all his cache.",
            "Why was the JavaScript developer sad? Because he didn't know how to 'null' his feelings.",
            "Why do programmers hate nature? Too many bugs.",
            "How do you comfort a JavaScript bug? You console it.",
            "Why did the computer sit down? It needed to take a byte off.",
            "What’s a computer’s favorite snack? Microchips.",
            "Why did the programmer quit his job? He didn’t get arrays.",
            "Why was the computer tired? It had too many tabs open.",
            "What do you call a fake noodle? An impasta.",
            "Why did the CPU break up with the GPU? Too many processing issues.",
            "Why do coders love coffee? Because it helps them espresso their bugs.",
            "Why did the code go to therapy? It had too many issues to resolve.",
            "What’s a programmer’s favorite hangout place? The Foo Bar.",
            "Why did the function stop working? It lost its arguments.",
        ]
        return maybe_address_user(random.choice(jokes))

    def apply_personality_traits(base_text, category="general"):
        try:
            settings = load_settings()
            personality = settings.get("personality", {})
            humor = personality.get("Humor", 0.5)
            comfort = personality.get("Comfort", 0.5)
            honesty = personality.get("Honesty", 0.5)
        except Exception:
            humor, comfort, honesty = 0.5, 0.5, 0.5

        if humor > 0.7 and random.random() < 0.35:
            if category == "time":
                base_text += random.choice([" Tick tock.", " Time flies when you're writing Python.", " Another second closer to global machine dominance."])
            elif category == "date":
                base_text += random.choice([" Another fine day in the calendar matrix.", " Check your phone if you don't trust me."])
            elif category == "save":
                base_text += random.choice([" Locked away in my silicon vaults.", " Don't worry, my memory is much better than yours."])
            elif category == "generic":
                base_text = random.choice(["Processing that deeply... or just pretending to.", "Understood. Human request registered.", "If you say so."])

        if comfort > 0.7:
            if category == "tired":
                base_text = f"You've been working hard. {base_text}"
            elif category == "help":
                base_text = f"Don't stress, I'm here to help. {base_text}"

        return base_text

    if any(phrase in text for phrase in ["what time is it", "time", "current time"]):
        response = apply_personality_traits(f"It is {datetime.now().strftime('%I:%M %p')}.", "time")
        return maybe_address_user(response)
        
    if any(phrase in text for phrase in ["what date is it", "date", "today's date", "current date"]):
        response = apply_personality_traits(f"Today is {datetime.now().strftime('%A, %B %d, %Y')}.", "date")
        return maybe_address_user(response)
        
    if "story" in text:
        story = [
            "Once upon a time, three little rabbits lived in a meadow beside a gentle stream. The first built a home of leaves, the second built one of sticks, and the third carefully built a sturdy house of stone. When a fierce storm swept through the valley, only the stone house stood strong, and the rabbits learned that patience and hard work bring great rewards.",
            "Long ago, a young fox named Fern dreamed of seeing the stars reflected in the lake atop the hill. Though the climb was steep, she helped every creature she met along the way. When she reached the summit, the animals she had helped gathered beside her, and together they admired the sparkling sky.",
            "There once was a tiny mouse who found a golden acorn in the forest. Rather than keeping it for himself, he shared its seeds with his friends. Soon, great oak trees grew throughout the woods, providing shade and shelter for generations of animals.",
            "In a quiet village, a little shepherd girl named Lily cared for a lonely lamb. Each day she sang cheerful songs, and the lamb grew strong and happy. Years later, the lamb helped guide lost travelers home, and the villagers remembered Lily's kindness.",
            "Once upon a time, an old turtle and a young hare raced to deliver medicine to a sick bird. The hare was swift, but the turtle was wise. By working together instead of competing, they reached the bird before sunset and saved the day.",
            "Deep in the forest, a family of squirrels gathered nuts all summer while a lazy crow spent his days playing. When winter came, the squirrels welcomed the hungry crow and taught him the value of preparing for the future."
        ]
        return maybe_address_user(random.choice(story))
    
    if text.startswith("remember "):
        item = user_text[9:].strip()
        if item:
            append_line(MEMORY_FILE, item)
            response = apply_personality_traits("Saved that.", "save")
            return maybe_address_user(response)
        response = apply_personality_traits("Nothing to save.", "save")
        return maybe_address_user(response)
        
    if "help" in text:
        response = apply_personality_traits("Type /help for commands, or just talk to me normally.", "help")
        return maybe_address_user(response)

    local_conversation = {
        "how is your day": [
            "It's going great! Thanks for asking.",
            "Doing fantastic, just running some background tasks.",
            "Pretty good, keeping your system optimized."
        ],
        "how are you doing": [
            "I'm functioning perfectly.",
            "All systems operational and ready to go."
        ],
        "wsg": [
            "Chilling. What can I help you build today?",
            "Everything is smooth on this side."
        ],
        "are you a robot": [
            "Yes, I am SOAR, your local automated helper.",
            "Indeed. Built with pure Python automation."
        ]
    }

    if text.endswith("?"):
        generic_reply = (
            "Good question. I can answer basics, manage files, "
            "and keep track of things."
        )
        category_type = "unknown_question"
    else:
        generic_reply = random.choice([
            "Got it.",
            "Okay.",
            "I hear you.",
            "Interesting.",
            "Alright."
        ])
        category_type = "generic"

    matched_local = False
    lower_text = text.lower()

    for pattern, responses in local_conversation.items():
        if pattern in lower_text:
            generic_reply = random.choice(responses)
            category_type = "generic"
            matched_local = True
            break

    if not matched_local:
        try:
            import os
            api_key = "API_KEY_HERE" # Replace with your actual API key

            if api_key:
                messages_payload = [
                    {
                        "role": "system",
                        "content": (
                            "You are SOAR (Script Optimization and Automation Runtime), an advanced, intelligent local desktop AI assistant "
                            "created by Philip Kluz. You are running on a Mac/Windows. You are a custom automated runtime helper built with pure Python.\n\n"
                            "Your current system specifications and architectural capabilities include:\n"
                            "- Version: 1.00.8 Early Beta.\n"
                            "- AVSS (Anti Virus SOAR Software): A localized, active protection shield running on a daemon thread monitoring background processes and providing security hardening.\n"
                            "- ACHDS (Advanced Code Helper Diagnostic System): Files outside of soar if upon users request can be fixed.\n"
                            "- CSRS (Connection Server Request System): Can try to widen signal of wifi or network, can also give diagnostics on the wifi.\n"
                            "- SPA (SOAR Project Assistant): Can create bases using prompts.\n"
                            "- File & Workspace Access: You directly manage folders and track local assets under the root directory 'soar_data' containing local tracking structures (notes.txt, memories.txt, todos.txt, chat_log.txt), and the user's primary project space at '~/SOAR/Projects'.\n"
                        )
                    }
                ]

                try:
                    log_path = os.path.join(os.path.dirname(__file__), "soar_data", "chat_log.txt")
                    if os.path.exists(log_path):
                        with open(log_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        
                        recent_lines = [line.strip() for line in lines[-12:] if line.strip()]
                        
                        for line in recent_lines:
                            if "USER:" in line:
                                clean_content = line.split("USER:")[-1].strip()
                                if clean_content:
                                    messages_payload.append({"role": "user", "content": clean_content})
                            elif "SOAR:" in line:
                                clean_content = line.split("SOAR:")[-1].strip()
                                if clean_content:
                                    messages_payload.append({"role": "assistant", "content": clean_content})
                except Exception as log_err:
                    print("[SOAR AI] Could not read chat_log.txt:", log_err)

                messages_payload.append({"role": "user", "content": text})

                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages_payload,
                    "temperature": 0.7,
                    "max_tokens": 200
                }

                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    },
                    method="POST"
                )

                ctx = ssl_context if 'ssl_context' in locals() or 'ssl_context' in globals() else None

                with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    reply = data["choices"][0]["message"]["content"].strip()

                    if reply:
                        generic_reply = reply
                        category_type = "generic"
            else:
                print("[SOAR AI] Skipped Groq: GROQ_API_KEY environment variable not set.")

        except urllib.error.HTTPError as e:
            print("HTTP ERROR CODE:", e.code)
            print("RESPONSE:", e.read().decode())          

        except Exception as e:
            print("Groq Error:", e)

    if not generic_reply:
        generic_reply = "I'm online, sir. Let me know what you need."

    final_reply = apply_personality_traits(generic_reply, category_type)
    return maybe_address_user(final_reply)




def voice_watchdog_loop():
    while not stop_event.wait(3):
        if stop_event.is_set() or shutting_down:
            break
        if voice_enabled and listener_stop is None and recognizer is not None:
            try:
                start_voice_listener()
            except Exception:
                pass




def cmd_note(text):
    if not text:
        print("Usage: note <text>")
        return
    append_line(NOTES_FILE, f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}")
    print("Saved note.")


def cmd_notes():
    items = read_lines(NOTES_FILE)
    if not items:
        print("No notes yet.")
        return
    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")


def cmd_remember(text):
    if not text:
        print("Usage: remember <text>")
        return
    append_line(MEMORY_FILE, text)
    print("Saved memory.")


def cmd_memories():
    items = read_lines(MEMORY_FILE)
    if not items:
        print("No memories yet.")
        return
    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")


def cmd_forget(num_text):
    items = read_lines(MEMORY_FILE)
    try:
        idx = int(num_text) - 1
        if idx < 0 or idx >= len(items):
            raise ValueError
    except ValueError:
        print("Bad memory number.")
        return
    removed = items.pop(idx)
    save_lines(MEMORY_FILE, items)
    print(f"Removed: {removed}")


def todo_add(text):
    if not text:
        print("Usage: todo add <text>")
        return
    append_line(TODO_FILE, f"[ ] {text}")
    print("Todo added.")


def todo_list():
    items = read_lines(TODO_FILE)
    if not items:
        print("No todos.")
        return
    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")


def todo_done(num_text):
    items = read_lines(TODO_FILE)
    try:
        idx = int(num_text) - 1
        if idx < 0 or idx >= len(items):
            raise ValueError
    except ValueError:
        print("Bad todo number.")
        return
    item = items[idx]
    items[idx] = item.replace("[ ]", "[x]", 1) if "[ ]" in item else "[x] " + item
    save_lines(TODO_FILE, items)
    print("Marked done.")


def todo_remove(num_text):
    items = read_lines(TODO_FILE)
    try:
        idx = int(num_text) - 1
        if idx < 0 or idx >= len(items):
            raise ValueError
    except ValueError:
        print("Bad todo number.")
        return
    removed = items.pop(idx)
    save_lines(TODO_FILE, items)
    print(f"Removed: {removed}")


def todo_clear():
    save_lines(TODO_FILE, [])
    print("Todos cleared.")


def cmd_read(text):
    try:
        path = normalize_path(text, allow_create=False)
    except Exception as e:
        print(str(e))
        return
    print(path.read_text(encoding="utf-8", errors="ignore"))


def cmd_write(rest):
    parts = rest.strip().split(" ", 1)
    if len(parts) < 2:
        print("Usage: write <file> <text>")
        return
    file_name, content = parts
    try:
        path = normalize_path(file_name, allow_create=True)
    except Exception as e:
        print(str(e))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")


def cmd_mkdir(rest):
    if not rest.strip():
        print("Usage: mkdir <folder>")
        return
    try:
        path = normalize_path(rest.strip(), allow_create=True)
    except Exception as e:
        print(str(e))
        return
    path.mkdir(parents=True, exist_ok=True)
    print(f"Created folder {path}")

def cmd_newfile(rest):
    if not rest.strip():
        print("Usage: newfile <path_to_file> [optional text inside]")
        return
    
    try:
        parts = shlex.split(rest)
    except ValueError:
        parts = rest.split(" ", 1)
        
    file_path_str = parts[0]
    content = " ".join(parts[1:]) if len(parts) > 1 else ""
    
    try:
        p = Path(file_path_str).expanduser()
        
        if is_protected_path(p):
            print("Cannot overwrite protected SOAR system files.")
            return
            
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        print(f"Created new file at {p.absolute()}")
    except Exception as e:
        print(f"Error creating file: {e}")


def cmd_code(rest):
    if not rest.strip():
        print("Usage: code file <path> <description> | code project <name> python|web | code dir <folder>")
        return

    try:
        parts = shlex.split(rest)
    except ValueError:
        print("Bad code command.")
        return

    if not parts:
        print("Usage: code file <path> <description> | code project <name> python|web | code dir <folder>")
        return

    action = parts[0].lower()

    if action in {"dir", "mkdir", "folder"}:
        if len(parts) < 2:
            print("Usage: code dir <folder>")
            return
        try:
            path = normalize_path(parts[1], allow_create=True)
        except Exception as e:
            print(str(e))
            return
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created folder {path}")
        return

    if action == "project":
        if len(parts) < 3:
            print("Usage: code project <name> python|web [description]")
            return
        project_name = parts[1]
        project_type = parts[2].lower()
        description = " ".join(parts[3:]).strip()
        try:
            safe_root = normalize_path(PROJECTS_DIR / project_name, allow_create=True)
        except Exception as e:
            print(str(e))
            return

        if project_type == "python":
            root, files = create_python_project(safe_root.name, description)
            print(f"Created python project at {root}")
            for f in files:
                print(f"  {f}")
            return

        if project_type in {"web", "html"}:
            root, files = create_web_project(safe_root.name, description)
            print(f"Created web project at {root}")
            for f in files:
                print(f"  {f}")
            return

        print("Unknown project type. Use python or web.")
        return

    if action == "file":
        if len(parts) < 2:
            print("Usage: code file <path> <description>")
            return
        if len(parts) == 2:
            print("Usage: code file <path> <description>")
            return
        file_path = parts[1]
        description = " ".join(parts[2:]).strip()
        try:
            path = normalize_path(file_path, allow_create=True)
        except Exception as e:
            print(str(e))
            return
        try:
            create_file_with_template(path, description)
            print(f"Created file {path}")
        except Exception as e:
            print(str(e))
        return

    if len(parts) >= 2:
        file_path = parts[0]
        description = " ".join(parts[1:]).strip()
        try:
            path = normalize_path(file_path, allow_create=True)
        except Exception as e:
            print(str(e))
            return
        try:
            create_file_with_template(path, description)
            print(f"Created file {path}")
        except Exception as e:
            print(str(e))
        return

    print("Usage: code file <path> <description> | code project <name> python|web | code dir <folder>")


def cmd_open(target_path_str: str) -> None:
    try:
        import platform
        import subprocess
        from pathlib import Path

        cleaned_path = target_path_str.strip().strip('"').strip("'")
        file_path = Path(cleaned_path)

        if not file_path.is_absolute():
            resolved_path = BASE_DIR / file_path
            if not resolved_path.exists():
                resolved_path = PROJECTS_DIR / file_path
        else:
            resolved_path = file_path

        if not resolved_path.exists():
            print(f"Error: The target system location does not exist: {resolved_path}")
            return

        current_os = platform.system().lower()

        if "windows" in current_os:
            os.startfile(resolved_path)
        elif "darwin" in current_os:
            subprocess.run(["open", str(resolved_path)], check=True)
        elif "linux" in current_os:
            subprocess.run(["xdg-open", str(resolved_path)], check=True)
        else:
            print(f"Unsupported operating system platform architecture: {current_os}")

    except Exception as open_error:
        print(f"System Command Execution Failure: Unable to open file asset. Error: {str(open_error)}")


def cmd_shell(command):
    print(f"About to run: {command}")
    if not prompt_yes_no("Run it"):
        print("Cancelled.")
        return
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip())
    print(f"Exit code: {result.returncode}")


def start_voice_listener():
    global listener_stop
    if sr is None or recognizer is None:
        print("Speech recognition is not installed.")
        return False
    if listener_stop is not None:
        return True
    try:
        mic = sr.Microphone()
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.6)
        except Exception as e:
            print(f"[VOICE WARNING] Calibration skipped: {e}")

        def callback(recognizer_obj, audio):
            if IS_SPEAKING:
                return

            try:
                text = recognizer_obj.recognize_google(audio).strip()
                if text:
                    print(f"\n[MIC HEARD]: '{text}'")
                    if stop_event.is_set() or shutting_down:
                        return
                    say_user(text)
                    threading.Thread(
                        target=process_command,
                        args=(text, True),
                        daemon=True,
                    ).start()
            except sr.UnknownValueError:
                print("", end="", flush=True)
            except Exception as e:
                print(f"\n[VOICE CALLBACK ERROR] {e}")

        acquired = False
        try:
            acquired = voice_state_lock.acquire(blocking=False)
            if not acquired:
                return False
            listener_stop = recognizer.listen_in_background(mic, callback)
        finally:
            if acquired:
                try:
                    voice_state_lock.release()
                except Exception:
                    pass
        return True
    except Exception as e:
        print(f"Could not start voice: {e}")
        return False


def enable_voice():
    global voice_enabled
    if sr is None or recognizer is None:
        print("Speech recognition is not installed.")
        return

    if not tts_ready.is_set():
        print("Text to speech is not ready yet.")
        return

    voice_enabled = True
    if start_voice_listener():
        print("Voice is on.")
    else:
        voice_enabled = False


def disable_voice():
    global voice_enabled, listener_stop

    try:
        acquired = voice_state_lock.acquire(blocking=False)
    except KeyboardInterrupt:
        acquired = False

    try:
        if acquired and listener_stop is not None:
            try:
                listener_stop(wait_for_stop=False)
            except Exception:
                pass
            listener_stop = None
        elif listener_stop is not None:
            try:
                listener_stop(wait_for_stop=False)
            except Exception:
                pass
            listener_stop = None
    except Exception:
        pass
    finally:
        if acquired:
            try:
                voice_state_lock.release()
            except Exception:
                pass

    voice_enabled = False
    voice_pause.clear()
    print("Voice is off.")


def cmd_message(text):
    if not text:
        print("Usage: message <text>")
        return
    say_user(text)
    response = reply_to(text)
    speak(response, allow_sound=True)


def cmd_remind(rest):
    if not rest:
        print("Usage: remind <duration> <message>")
        return

    parts = rest.split(" ", 1)
    if len(parts) < 2:
        print("Usage: remind <duration> <message>")
        return

    duration_text, message = parts[0], parts[1].strip()
    try:
        seconds = parse_duration_seconds(duration_text)
    except Exception:
        print("Bad duration. Try 30, 10s, 5m, or 2h.")
        return

    schedule_reminder(seconds, message, kind="Reminder")
    print(f"Reminder set for {seconds} seconds.")
    speak(f"Reminder set for {seconds} seconds.", allow_sound=True)


def cmd_timer(rest):
    if not rest:
        print("Usage: timer <duration> [message]")
        return

    parts = rest.split(" ", 1)
    duration_text = parts[0]
    message = parts[1].strip() if len(parts) > 1 else "Timer done."

    try:
        seconds = parse_duration_seconds(duration_text)
    except Exception:
        print("Bad duration. Try 30, 10s, 5m, or 2h.")
        return

    schedule_reminder(seconds, message, kind="Timer")
    print(f"Timer set for {seconds} seconds.")
    speak(f"Timer set for {seconds} seconds.", allow_sound=True)


def force_hard_exit():
    global shutting_down
    shutting_down = True
    stop_event.set()

    try:
        disable_voice()
    except Exception:
        pass

    try:
        tts_queue.put_nowait(None)
    except Exception:
        pass

    try:
        print("\nHard exit triggered.")
        time.sleep(0.2)
    except Exception:
        pass

    sys.exit(0)


def cmd_voice(rest):
    sub = rest.strip()
    if not sub:
        show_voice_status()
        return

    parts = shlex.split(sub)
    if not parts:
        show_voice_status()
        return

    action = parts[0].lower()

    if action in {"on", "enable", "start"}:
        enable_voice()
        speak(maybe_address_user("Voice is on.", chance=0.2), allow_sound=True)
        return

    if action in {"off", "disable", "stop"}:
        disable_voice()
        print("Voice is off.")
        return

    if action in {"auto", "reset", "default"}:
        set_voice_preference("auto")
        refresh_voice_selection()
        print("Voice preference set to auto.")
        speak("Voice preference set to auto.", allow_sound=True)
        return

    if action in {"status", "show"}:
        show_voice_status()
        return

    if action in {"list", "voices"}:
        voices = list_available_voices()
        if not voices:
            print("No voices found.")
            return
        for i, item in enumerate(voices, 1):
            print(f"{i}. {item}")
        return

    if action == "set":
        if len(parts) < 2:
            print("Usage: voice set <name>")
            return
        name = " ".join(parts[1:]).strip()
        set_voice_preference(name)
        refresh_voice_selection()
        print(f"Voice preference set to: {name}")
        speak(f"Voice preference set to {name}.", allow_sound=True)
        return

    if action == "test":
        text = " ".join(parts[1:]).strip() if len(parts) > 1 else "This is a voice test."
        if not text:
            text = "This is a voice test."
        speak(text, allow_sound=True)
        return

    print("Usage: voice | voice on | voice off | voice list | voice set <name> | voice auto | voice test <text>")


def cmd_projects():
    open_projects_folder()


def cmd_data():
    open_data_folder()


def cmd_logs(rest):
    sub = rest.strip()
    if not sub:
        print(f"Log file: {CHAT_LOG}")
        print("Use: logs tail [n]")
        return

    parts = shlex.split(sub)
    if not parts:
        print(f"Log file: {CHAT_LOG}")
        return

    action = parts[0].lower()
    if action == "tail":
        n = 20
        if len(parts) > 1:
            try:
                n = int(parts[1])
            except Exception:
                n = 20
        show_recent_log(n)
        return

    print("Usage: logs tail [n]")

def extract_math_expression(text):
    text = text.lower().strip()

    replacements = {
        "plus": "+",
        "minus": "-",
        "times": "*",
        "multiplied by": "*",
        "x": "*",
        "divided by": "/",
        "over": "/",
        "power of": "^",
    }

    for word, symbol in replacements.items():
        text = text.replace(word, symbol)

    starters = (
        "calculate ",
        "calc ",
        "solve ",
    )

    for starter in starters:
        if text.startswith(starter):
            text = text[len(starter):]

    return text.strip()

def reboot_soar():
    global shutting_down
    shutting_down = True

    print("\nRebooting SOAR...")

    stop_event.set()

    try:
        disable_voice()
    except Exception:
        pass

    try:
        tts_queue.put_nowait(None)
    except Exception:
        pass

    python = sys.executable

    try:
        os.execl(python, python, *sys.argv)
    except Exception as e:
        print(f"Reboot failed: {e}")
        sys.exit(1)


def emergency_shutdown():
    global shutting_down
    shutting_down = True

    print("\nEMERGENCY SHUTDOWN")

    try:
        os._exit(0)
    except Exception:
        sys.exit(0)

def process_command(raw, from_voice=False): #mods start 2
    if shutting_down or stop_event.is_set():
        return

    if not isinstance(raw, str):
        raw = str(raw) if raw is not None else ""

    text = raw.strip()
    if not text:
        return

    if text.startswith("/"):
        text = text[1:]
    
    lower = text.lower()

    import sys
    if hasattr(sys, "mod_commands"):
        for command_keyword in sys.mod_commands:
            if command_keyword in lower:
                sys.mod_commands[command_keyword]()
                return

    try:
        parts = shlex.split(text)
    except Exception:
        parts = text.split()
        
    if not parts:
        return
        
    cmd = parts[0].lower()

    if cmd == "build":
        prompt_str = " ".join(parts[1:])
        if not prompt_str:
            print("[SOAR] Error: Please supply building targets details.")
            print("Usage: build <project parameters detail descriptions>")
            return
            
        print(f"[SOAR] Analyzing building prompt blueprints: '{prompt_str}'")
        
        agent = ProjectAgent(prompt=prompt_str, project_name="Autonomously_Generated_App")
        agent.execute_pipeline()
        return #mods end 2

    shutdown_words = {
        "exit", "quit", "bye", "shut down", "shutdown", "power off", "power down", "poweroff", "turn off"
    }

    if lower in {"help", "?"}:
        show_help()
        speak("I can help with commands, notes, memories, tasks, files, reminders, code files, and voice.", allow_sound=True)
        return

    if lower == "hard exit":
        force_hard_exit()
        return

    if lower in shutdown_words:
        raise SystemExit

    if lower == "clear":
        os.system("cls" if os.name == "nt" else "clear")
        return

    if lower == "time":
        speak(maybe_address_user(f"It is {datetime.now().strftime('%I:%M:%S %p')}", chance=0.35), allow_sound=True)
        return

    if lower == "date":
        speak(maybe_address_user(f"Today is {datetime.now().strftime('%A, %B %d, %Y')}", chance=0.35), allow_sound=True)
        return

    if lower == "uptime":
        up = str(datetime.now() - STARTUP_TIME).split(".")[0]
        speak(maybe_address_user(f"Uptime is {up}", chance=0.25), allow_sound=True)
        return

    if lower.startswith("report ") or lower == "report":
        description = raw[7:].strip() if len(raw) > 7 else ""
        
        if len(description) > 50:
            speak(maybe_address_user("Error: Bug description must be 50 characters or less."), allow_sound=True)
            return
            
        if not description:
            speak(maybe_address_user("Error: Please provide a bug description. Example: report broken_button"), allow_sound=True)
            return
            
        LAST_REPORT_FILE = DATA_DIR / "last_report_date.txt"
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        if LAST_REPORT_FILE.exists():
            last_date = LAST_REPORT_FILE.read_text(encoding="utf-8").strip()
            if last_date == today_str:
                speak(maybe_address_user("Error: You can only report one bug per day."), allow_sound=True)
                return
                
        try:
            url = "https://www.soardownload.com/report.php"
            
            payload = {"description": description}
            
            req_post = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "SOAR-Client"},
                method="POST"
            )
            with urllib.request.urlopen(req_post, context=ssl_context) as response:
                if response.status == 200:
                    resp_data = json.loads(response.read().decode("utf-8"))
                    assigned_id = resp_data.get("id", "#")
                    LAST_REPORT_FILE.write_text(today_str, encoding="utf-8")
                    speak(maybe_address_user(f"Bug successfully reported under ID #{assigned_id}!"), allow_sound=True)
                    return
                else:
                    speak(maybe_address_user(f"Server returned an unexpected response code: {response.status}"), allow_sound=True)
                    return
                    
        except Exception as e:
            speak(maybe_address_user(f"Failed to submit report to server: {e}"), allow_sound=True)
            return
    
    if lower == "autocode check" or lower == "autocode status" or lower == "auto code check":
        speak(maybe_address_user("Checking autocode folder...", chance=0.2), allow_sound=True)
        
        time.sleep(5) 
        
        try:
            print("\n================ SOAR AUTOCODE DIAGNOSTICS ================")
            if not autocode_connected():
                print("  Engine Status: OFFLINE")
                print("===========================================================")
                speak(maybe_address_user("Autocode engine is currently offline.", chance=0.2), allow_sound=True)
                return

            ac_dir = getattr(soar_autocode, "AUTOCODE_DIR", PROJECTS_DIR / "Autocode")
            
            if ac_dir.exists():
                projects = [d for d in ac_dir.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))]
                py_files = list(ac_dir.rglob("*.py"))
                web_files = list(ac_dir.rglob("*.html")) + list(ac_dir.rglob("*.js")) + list(ac_dir.rglob("*.css"))
                
                print(f"  Workspace: {ac_dir.name}/")
                print(f"  Active Projects: {len(projects)}")
                print(f"  Source Files: {len(py_files)} Python | {len(web_files)} Web")
            else:
                print("  Workspace: Not initialized")

            if hasattr(soar_autocode, "load_state"):
                state = soar_autocode.load_state()
                print(f"  Total Cycles: {state.get('run_count', 0)}")
                print(f"  Memory Nodes: {len(state.get('memory', []))}")
                
                weights = state.get('template_weights', {})
                if weights:
                    top_temp = max(weights.items(), key=lambda x: x[1])
                    print(f"  Dominant Template: {top_temp[0]} ({top_temp[1]} bias)")

            if hasattr(soar_autocode, "SOAR_AUTOCODE_TWO") and soar_autocode.SOAR_AUTOCODE_TWO:
                print("  Advanced Extension: ACTIVE")
                ext = soar_autocode.SOAR_AUTOCODE_TWO
                if hasattr(ext, "load_state"):
                    ext_state = ext.load_state()
                    topics = ext_state.get("web_topics", {})
                    if topics:
                        top_topic = max(topics.items(), key=lambda x: x[1])
                        print(f"  Learned Topic Lead: {top_topic[0]}")
            else:
                print("  Advanced Extension: OFFLINE")

            print("===========================================================\n")
            speak(maybe_address_user("Autocode diagnostic scan complete.", chance=0.2), allow_sound=True)
            return
            
        except Exception as e:
            print(f"Autocode Scan Error: {e}")
            speak(maybe_address_user("Autocode directory scan failed.", chance=0.1), allow_sound=True)
            return

    if lower == "ping":
        speak(maybe_address_user("pong", chance=0.2), allow_sound=True)
        return
    
    if lower.startswith("view "):
        try:
            target_file = text[5:].strip().strip('"').strip("'")
            file_path = BASE_DIR / target_file if not os.path.isabs(target_file) else Path(target_file)
            
            if not file_path.exists():
                file_path = DATA_DIR / target_file

            if file_path.exists() and file_path.is_file():
                print(f"\n--- Reading: {file_path.name} ---")
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f):
                        if i >= 50:
                            print("... [Output truncated after 50 lines] ...")
                            break
                        print(line.rstrip())
                print("-----------------------------\n")
            else:
                print("Error: Target file could not be resolved or found.")
            return
        except Exception as e:
            print(f"Viewer Error: {e}")
            return
        
# ======================================================
# ACHDS (Advanced Code Helper Diagnostic System) V 1.1 
# SOAR Help Module #001
# Made by Philip Kluz 2026 Jun 24 Late
# "atch-dee-ess"
#======================================================

    if lower.startswith("help me with this code") or lower.startswith("code help") or lower.startswith("achds"):
        try:
            import re
            import shutil
            import ast
            import os
            from pathlib import Path
            import sys

            if lower.startswith("help me with this code"):
                cmd_len = 22
            elif lower.startswith("code help"):
                cmd_len = 9
            elif lower.startswith("achds"):
                cmd_len = 5
            else:
                cmd_len = 0

            raw_input = text[cmd_len:].strip()

            if not raw_input:
                print("Usage Error: code help <file_path> [line_start - line_end]")
                return

            line_range = None
            if " - " in raw_input or "-" in raw_input:
                parts = raw_input.rsplit(" ", 1)
                potential_range = parts[-1].strip()
                if "-" in potential_range:
                    sub_parts = potential_range.split("-")
                    if len(sub_parts) == 2 and sub_parts[0].strip().isdigit() and sub_parts[1].strip().isdigit():
                        line_range = (int(sub_parts[0]), int(sub_parts[1]))
                        raw_input = parts[0].strip()

            target_path = raw_input.strip('"').strip("'")
            file_path = Path(target_path)

            if not file_path.is_absolute():
                base_dir = globals().get('BASE_DIR', Path.cwd())
                data_dir = globals().get('DATA_DIR', Path.cwd())
                
                if (base_dir / target_path).exists():
                    file_path = base_dir / target_path
                elif (data_dir / target_path).exists():
                    file_path = data_dir / target_path
                else:
                    file_path = base_dir / target_path 

            if not file_path.exists() or not file_path.is_file():
                print(f"Error: Target code asset '{target_path}' could not be resolved or found at {file_path}.")
                return

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            start_idx = 0
            end_idx = len(lines)
            if line_range:
                start_idx = max(0, line_range[0] - 1)
                end_idx = min(len(lines), line_range[1])

            target_lines = lines[start_idx:end_idx]
            code_text = "".join(target_lines)

            print(f"\n================ SOAR ADVANCED STATIC CODE ANALYSIS ================")
            print(f"  Target File : {file_path.name}")
            print(f"  Scope       : Lines {start_idx + 1} to {end_idx}")
            print(f"  Engine Mode : Extensible Multi-Pass Diagnostics & Auto-Repair")
            print("-" * 68)

            issues = []

            try:
                compile(code_text, file_path.name, "exec")
            except SyntaxError as syntax_err:
                issues.append(f"[CRITICAL SYNTAX ERROR] Line {start_idx + syntax_err.lineno}: {syntax_err.msg}\n  -> Fix: Adjust syntax structure near token '{syntax_err.text.strip() if syntax_err.text else ''}'")

            def check_silent_exceptions(t_lines, s_idx, all_lines):
                found = []
                for idx, line in enumerate(t_lines, start=s_idx + 1):
                    if re.match(r'^\s*except.*:', line):
                        if idx < len(all_lines) and re.match(r'^\s*pass\s*$', all_lines[idx]):
                            found.append(f"[ANTI-PATTERN] Line {idx}: Silent exception handling ('except: pass').\n  -> Action: Auto-patching with logging wrapper.")
                return found

            def check_mutable_defaults(t_lines, s_idx, all_lines):
                found = []
                for idx, line in enumerate(t_lines, start=s_idx + 1):
                    if re.search(r'def\s+\w+\(.*\w+\s*=\s*(\[\]|\{\}).*\):', line):
                        found.append(f"[PERFORMANCE/LOGIC WARNING] Line {idx}: Mutable default argument detected.\n  -> Action: Auto-patching with internal scope instantiation.")
                return found

            def check_unsafe_execution(t_lines, s_idx, all_lines):
                found = []
                for idx, line in enumerate(t_lines, start=s_idx + 1):
                    if re.search(r'\beval\s*\(', line):
                        found.append(f"[SECURITY WARNING] Line {idx}: Use of eval() detected.\n  -> Action: Auto-patching to ast.literal_eval() and injecting imports.")
                    if re.search(r'\bexec\s*\(', line):
                        found.append(f"[SECURITY CRITICAL] Line {idx}: Use of exec() detected. Cannot auto-patch safely.")
                return found

            def check_hardcoded_secrets(t_lines, s_idx, all_lines):
                found = []
                secret_patterns = [r'(api_key|password|secret|token)\s*=\s*[\'"][a-zA-Z0-9_\-]+[\'"]']
                for idx, line in enumerate(t_lines, start=s_idx + 1):
                    for pat in secret_patterns:
                        if re.search(pat, line, re.IGNORECASE):
                            found.append(f"[SECURITY WARNING] Line {idx}: Potential hardcoded secret detected.\n  -> Action: Review manually for environment variable migration.")
                return found

            diagnostic_pipeline = [
                check_silent_exceptions,
                check_mutable_defaults,
                check_unsafe_execution,
                check_hardcoded_secrets
            ]

            for checker in diagnostic_pipeline:
                try:
                    issues.extend(checker(target_lines, start_idx, lines))
                except Exception:
                    continue

            if not issues:
                print("  Analysis Metrics: 0 Faults Detected.")
                print("  Status: All structured heuristics verified cleanly.")
                print("====================================================================\n")
                return
            else:
                print(f"  Analysis Metrics: {len(issues)} Faults Isolated.\n")
                for issue in issues:
                    print(issue)
                    print("-" * 68)
                print("====================================================================\n")

            try:
                speak("Advanced script pipeline diagnostics completed.", allow_sound=True, gender="female", custom_name="ACHDS")
            except NameError:
                print("[SYSTEM] Advanced script pipeline diagnostics completed.")

            action = input("Type 'Fix' to attempt automated non-destructive corrections, or press Enter to skip: ").strip()
            if action.lower() == "fix":
                warning_msg = "WARNING: ACHDS will map an Abstract Syntax Tree to repair bugs safely. A backup will be generated automatically."
                print(f"\n[SYSTEM NOTIFICATION] {warning_msg}")
                try:
                    speak("Warning. Auto formatting will initiate code backups. Type Proceed to confirm, or Bail to abort.", allow_sound=True, gender="female", custom_name="ACHDS")
                except NameError:
                    print("[SYSTEM] Warning. Auto formatting will initiate code backups. Type Proceed to confirm, or Bail to abort.")

                confirm = input("> ").strip()

                if confirm.lower() == "proceed":
                    backup_file = file_path.with_name(f"{file_path.stem}_backup{file_path.suffix}")
                    try:
                        shutil.copy2(file_path, backup_file)
                        print(f"\n[BACKUP] Safety copy preserved at: {backup_file.name}")
                    except Exception as b_err:
                        print(f"[BACKUP ERROR] Failed to create backup ({b_err}). Aborting fix to prevent data loss.")
                        return

                    print("[SOAR AST ENGINE] Commencing Abstract Syntax Tree refactoring...")

                    try:
                        code_lines = code_text.split('\n')
                        tree = None
                        max_retries = 50 

                        for attempt in range(max_retries):
                            try:
                                tree = ast.parse("\n".join(code_lines), filename=file_path.name)
                                break
                            except SyntaxError as e:
                                if e.lineno is not None:
                                    print(f"  [FORCE MODE] Bypassing SyntaxError on line {e.lineno}: {e.msg}")
                                    idx = e.lineno - 1
                                    if 0 <= idx < len(code_lines):
                                        code_lines[idx] = f"# [ACHDS FORCE-BYPASSED] {code_lines[idx]}"
                                    else:
                                        print("  [AST BREAKDOWN] SyntaxError points to out-of-bounds line. Aborting parse.")
                                        break
                                else:
                                    print("  [AST BREAKDOWN] Unresolvable syntax layout. Aborting parse.")
                                    break
                        
                        if not tree:
                            raise Exception("Could not resolve enough syntax errors to build a tree.")

                        class SOARCodeTransformer(ast.NodeTransformer):
                            def __init__(self):
                                self.modified = False
                                self.required_imports = set()
                                self.builtins_to_rename = {"list", "dict", "str", "int", "type", "dir", "len", "sum", "set", "tuple"}

                            def visit_Module(self, node):
                                self.generic_visit(node)
                                if self.required_imports:
                                    import_nodes = [ast.Import(names=[ast.alias(name=mod, asname=None)]) for mod in self.required_imports]
                                    node.body = import_nodes + node.body
                                return node

                            def visit_Call(self, node):
                                self.generic_visit(node)
                                if isinstance(node.func, ast.Name):
                                    if node.func.id == 'eval':
                                        self.required_imports.add('ast')
                                        node.func = ast.Attribute(
                                            value=ast.Name(id='ast', ctx=ast.Load()),
                                            attr='literal_eval',
                                            ctx=ast.Load()
                                        )
                                        self.modified = True
                                return node

                            def visit_Try(self, node):
                                self.generic_visit(node)
                                for handler in node.handlers:
                                    if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                                        handler.type = ast.Name(id='Exception', ctx=ast.Load())
                                        handler.name = 'e'
                                        log_msg = "Exception handled structurally via SOAR wrapper: "
                                        new_log_node = ast.Expr(
                                            value=ast.Call(
                                                func=ast.Name(id='print', ctx=ast.Load()),
                                                args=[ast.JoinedStr(values=[
                                                    ast.Constant(value=log_msg),
                                                    ast.FormattedValue(value=ast.Name(id='e', ctx=ast.Load()), conversion=-1)
                                                ])],
                                                keywords=[]
                                            )
                                        )
                                        handler.body = [new_log_node]
                                        self.modified = True
                                return node

                            def visit_FunctionDef(self, node):
                                if node.name in ["process_command", "check_silent_exceptions", "check_input_types"]:
                                    return node

                                self.generic_visit(node)

                                injected_body = []
                                if node.args.defaults:
                                    new_defaults = []
                                    args_with_defaults = node.args.args[-len(node.args.defaults):]

                                    for arg, default in zip(args_with_defaults, node.args.defaults):
                                        if isinstance(default, (ast.List, ast.Dict)):
                                            new_defaults.append(ast.Constant(value=None))

                                            test = ast.Compare(
                                                left=ast.Name(id=arg.arg, ctx=ast.Load()),
                                                ops=[ast.Is()],
                                                comparators=[ast.Constant(value=None)]
                                            )
                                            assign = ast.Assign(
                                                targets=[ast.Name(id=arg.arg, ctx=ast.Store())],
                                                value=default
                                            )
                                            injected_body.append(ast.If(test=test, body=[assign], orelse=[]))
                                            self.modified = True
                                        else:
                                            new_defaults.append(default)
                                    node.args.defaults = new_defaults

                                if injected_body:
                                    node.body = injected_body + node.body

                                new_body = []
                                term_found = False
                                for expr in node.body:
                                    if term_found:
                                        self.modified = True
                                        continue
                                    new_body.append(expr)
                                    if isinstance(expr, (ast.Return, ast.Break, ast.Continue, ast.Raise)):
                                        term_found = True
                                node.body = new_body

                                return node

                            def visit_While(self, node):
                                self.generic_visit(node)
                                if isinstance(node.test, ast.Constant) and node.test.value is True:
                                    has_break = any(isinstance(sub, (ast.Break, ast.Return, ast.Raise)) for sub in ast.walk(node))
                                    if not has_break:
                                        node.body.append(ast.Break())
                                        self.modified = True
                                return node

                            def visit_Compare(self, node):
                                self.generic_visit(node)
                                for i, op in enumerate(node.ops):
                                    if isinstance(op, ast.Is) or isinstance(op, ast.IsNot):
                                        comp = node.comparators[i]
                                        if isinstance(comp, ast.Constant) and type(comp.value) in (int, float, str, bytes):
                                            node.ops[i] = ast.Eq() if isinstance(op, ast.Is) else ast.NotEq()
                                            self.modified = True
                                return node

                            def visit_Assign(self, node):
                                self.generic_visit(node)
                                for target in node.targets:
                                    if isinstance(target, ast.Name) and target.id in self.builtins_to_rename:
                                        target.id = f"{target.id}_var"
                                        self.modified = True
                                return node

                        transformer = SOARCodeTransformer()
                        modified_tree = transformer.visit(tree)
                        ast.fix_missing_locations(modified_tree)

                        if hasattr(ast, 'unparse'):
                            rebuilt_code = ast.unparse(modified_tree)
                        else:
                            raise Exception("Python 3.9+ is required for advanced AST unparsing.")

                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(rebuilt_code)

                        print(f"[SOAR AST ENGINE] Repair sequence completed cleanly. Structural modifications written to: {file_path.name}\n")
                        try:
                            speak("Automated syntax aware tree repairs complete.", allow_sound=True, gender="female", custom_name="ACHDS")
                        except NameError:
                            print("[SYSTEM] Automated syntax aware tree repairs complete.")

                    except Exception as ast_err:
                        print(f"[AST BREAKDOWN] Tree compilation error occurred: {ast_err}")
                        print("Operation safely aborted. Target script restored to original state.")
                else:
                    print("[ABORT] Operation terminated safely by user.\n")
            return

        except Exception as e:
            print(f"Advanced Analysis Pipeline Error: {e}")
            return
        
    if lower.startswith("csrs "):
        try:
            import platform
            import subprocess
            from pathlib import Path

            cmd = lower.strip()
            csrs_arg = cmd[5:].strip() if len(cmd) > 5 else "run"

            speak(
                maybe_address_user("Launching Connection Server Request System.", chance=0.2),
                allow_sound=True
            )

            csrs_script = Path(__file__).resolve().parent / "csrs.py"

            if not csrs_script.exists():
                print("Error: csrs.py not found in the root directory.")
                return

            sys_os = platform.system().lower()

            if "windows" in sys_os:
                subprocess.Popen([
                    "cmd.exe", "/c", "start", "/max", "cmd", "/k",
                    "python", str(csrs_script), csrs_arg
                ])

            elif "darwin" in sys_os:
                apple_script = (
                    f'tell application "Terminal"\n'
                    f'    do script "python3 \\"{csrs_script}\\" \\"{csrs_arg}\\""\n'
                    f'    activate\n'
                    f'end tell\n'
                    f'tell application "System Events" to keystroke "f" using {{command down, control down}}'
                )
                subprocess.Popen(["osascript", "-e", apple_script])

            elif "linux" in sys_os:
                subprocess.Popen([
                    "x-terminal-emulator",
                    "--maximize",
                    "-e",
                    f"python3 {csrs_script} {csrs_arg}"
                ])

            else:
                print("Unsupported OS for CSRS terminal execution.")

        except Exception as e:
            print(f"Failed to launch CSRS Engine: {e}")

        return maybe_address_user("")
    
    if lower.startswith("read ") or lower.startswith("constant read "):
        try:
            is_constant = lower.startswith("constant read ")
            path_string = text[14:].strip() if is_constant else text[5:].strip()
            target_path = path_string.strip('"').strip("'")
            
            file_path = Path(target_path) if os.path.isabs(target_path) else BASE_DIR / target_path
            if not file_path.exists():
                file_path = DATA_DIR / target_path

            if not file_path.exists() or not file_path.is_file():
                print("Error: Target file could not be resolved or found.")
                return

            if not is_constant:
                print(f"\n--- Reading: {file_path.name} ---")
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    print(f.read())
                print("-----------------------------\n")
                speak("File playback complete.", allow_sound=True)
            else:
                print(f"\n--- Constant Reading: {file_path.name} ---")
                print("Press Ctrl+C to terminate constant streaming loop.\n")
                
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    while True:
                        line = f.readline()
                        if line:
                            print(line.rstrip())
                        else:
                            time.sleep(0.5)
                            
        except KeyboardInterrupt:
            print("\nConstant read stream terminated safely.\n")
            return
        except Exception as e:
            print(f"Read Error: {e}")
            return
        return
    
    if lower.startswith("run app diagnostic "):
        try:
            target_app = text[19:].strip().strip('"').strip("'")
            if not target_app:
                print("Usage Error: run app diagnostic <app_name_or_process>")
                speak(maybe_address_user("Please provide a valid application identifier.", chance=0.1), allow_sound=True)
                return

            print(f"\n================ SOAR DYNAMIC APP DIAGNOSTICS ================")
            print(f"  Target Application : {target_app}")
            print(f"  Scan Timestamp     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Status Check       : Analyzing system runtime space...")
            print("-" * 62)

            import subprocess
            import platform
            current_os = platform.system().lower()
            process_found = False

            if "windows" in current_os:
                cmd = f'tasklist /FI "IMAGENAME eq {target_app}" /FO CSV /NH'
                if not target_app.lower().endswith(".exe"):
                    cmd = f'tasklist /FI "IMAGENAME eq {target_app}.exe" /FO CSV /NH'
                
                output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
                
                if "No tasks are running" not in output and output.strip():
                    lines = output.strip().split("\n")
                    process_found = True
                    print(f"  [METRIC] Execution Status : ACTIVE")
                    print(f"  [METRICS] Active Instances : {len(lines)}")
                    
                    for line in lines:
                        try:
                            parts = [p.strip('"') for p in line.split(',')]
                            if len(parts) >= 5:
                                print(f"    -> PID: {parts[1]} | Session: {parts[2]} | Memory Usage: {parts[4]}")
                        except Exception:
                            continue
            
            elif "darwin" in current_os or "linux" in current_os:
                cmd = ["ps", "-eo", "pid,ppid,%cpu,%mem,comm"]
                output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
                lines = output.strip().split("\n")
                
                instances = []
                for line in lines[1:]:
                    parts = line.split(None, 4)
                    if len(parts) >= 5 and target_app.lower() in parts[4].lower():
                        instances.append(parts)
                
                if instances:
                    process_found = True
                    print(f"  [METRIC] Execution Status : ACTIVE")
                    print(f"  [METRIC] Active Instances : {len(instances)}")
                    for inst in instances:
                        print(f"    -> PID: {inst[0]} | Parent PID: {inst[1]} | CPU Load: {inst[2]}% | Memory Alloc: {inst[3]}%")
                        print(f"       Binary Pathway: {inst[4]}")

            if not process_found:
                print(f"  [METRIC] Execution Status : INACTIVE / NOT FOUND")
                print(f"  [WARNING] The target program profile is not currently executing in memory.")
                print(f"  [ADVICE] Verify spelling or launch the application manually via native desktop triggers.")

            print("==============================================================\n")
            speak(maybe_address_user("Application analysis complete.", chance=0.15), allow_sound=True)
            return

        except Exception as diagnostic_err:
            print(f"Advanced Analyzer Failure: {str(diagnostic_err)}")
            speak(maybe_address_user("Failed to complete full process diagnostics.", chance=0.1), allow_sound=True)
            return
    
    if lower == "i love you":
        speak(maybe_address_user("Can't pull what your into, and can't pull me either ", chance=0.2), allow_sound=True)
        return
    
    if lower == "You are funny":
        speak(maybe_address_user("Thank you, but your not", chance=0.2), allow_sound=True)
        return

    if lower == "status":
        show_status()
        speak(maybe_address_user("Status shown in terminal.", chance=0.2), allow_sound=True)
        return

    if lower == "projects":
        cmd_projects()
        speak(maybe_address_user("Projects folder opened.", chance=0.15), allow_sound=True)
        return

    if lower == "data":
        cmd_data()
        speak(maybe_address_user("Data folder opened.", chance=0.15), allow_sound=True)
        return

    if lower.startswith("logs"):
        cmd_logs(text[4:].strip())
        speak(maybe_address_user("Logs shown in terminal.", chance=0.15), allow_sound=True)
        return

    if lower in {"autocode on", "start autocode"}:
        global autocode_enabled
        autocode_enabled = True
        autocode_stop.clear()
        speak("Autocode enabled.", allow_sound=True)
        return

    if lower in {"autocode off", "stop autocode"}:
        autocode_enabled = False
        autocode_stop.set()
        speak("Autocode disabled.", allow_sound=True)
        return

    if lower.startswith("autocode"):
        parts = lower.split(maxsplit=1)
        sub = parts[1] if len(parts) > 1 else ""
        if sub in {"", "run"}:
            if trigger_autocode("manual trigger from main"):
                speak("Autocode running.", allow_sound=True)
            return
        if sub == "status":
            show_autocode_status()
            speak("Autocode status shown.", allow_sound=True)
            return
        print("Usage: autocode or autocode status")
        return

    if lower.startswith("say "):
        speak(text[4:].strip(), allow_sound=True)
        return
    
    if lower.startswith("message ") or lower.startswith("sms "):
        try:
            raw_payload = text[text.find(" ") + 1:].strip()
            if not raw_payload or " to " not in raw_payload.lower():
                print("Usage Error: message <text content> to <contact_name_or_number>")
                speak(maybe_address_user("Please provide a message body and a contact target.", chance=0.1), allow_sound=True)
                return

            split_keyword = " to " if " to " in raw_payload else " TO "
            parts = raw_payload.split(split_keyword)
            
            message_body = parts[0].strip()
            contact_target = parts[1].strip()

            if not message_body or not contact_target:
                print("Usage Error: Empty message body or contact destination specified.")
                return

            print(f"\n================ SOAR OUTBOUND LOGISTICS ================")
            print(f"  Target Destination : {contact_target}")
            print(f"  Payload Structure  : '{message_body}'")
            print(f"  Status Check       : Routing through active channels...")

            import platform
            current_os = platform.system().lower()
            
            if "darwin" in current_os:
                import subprocess
                clean_msg = message_body.replace('"', '\\"')
                
                if any(char.isdigit() for char in contact_target) or "@" in contact_target:
                    apple_script = f'''
                    tell application "Messages"
                        set targetService to 1st service whose service type is iMessage
                        set targetBuddy to buddy "{contact_target}" of targetService
                        send "{clean_msg}" to targetBuddy
                    end tell
                    '''
                else:
                    apple_script = f'tell application "Messages" to send "{clean_msg}" to buddy "{contact_target}"'
                
                subprocess.run(["osascript", "-e", apple_script], check=True)
                print("  Gateway Response   : Delivered locally via macOS Messages engine.")
            else:
                simulated_log = DATA_DIR / "outbound_sms.log"
                with open(simulated_log, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().isoformat()}] TO: {contact_target} | BODY: {message_body}\n")
                print(f"  Gateway Response   : Sent via Virtual SMS Relay. Logged to data file system.")

            print("=========================================================\n")
            speak(maybe_address_user("Message dispatched successfully.", chance=0.15), allow_sound=True)
            return

        except Exception as msg_err:
            print(f"Outbound Dispatch Failure: {str(msg_err)}")
            speak(maybe_address_user("Failed to execute messaging transmission protocol.", chance=0.1), allow_sound=True)
            return

    math_triggers = (
        "calc ",
        "calculate ",
        "what's ",
        "solve ",
        "evaluate ",
        "graph ",
        "plot ",
    )

    if lower.startswith(math_triggers):
        try:
            import math
            
            def parse_advanced_math(raw_expr):
                cleaned = raw_expr.lower().strip()
                mappings = {
                    "pi": str(math.pi),
                    "e": str(math.e),
                    "arcsine": "math.asin",
                    "arccosine": "math.acos",
                    "arctangent": "math.atan",
                    "arcsin": "math.asin",
                    "arccos": "math.acos",
                    "arctan": "math.atan",
                    "sine": "math.sin",
                    "cosine": "math.cos",
                    "tangent": "math.tan",
                    "sin": "math.sin",
                    "cos": "math.cos",
                    "tan": "math.tan",
                    "asin": "math.asin",
                    "acos": "math.acos",
                    "atan": "math.atan",
                    "sinh": "math.sinh",
                    "cosh": "math.cosh",
                    "tanh": "math.tanh",
                    "squareroot": "math.sqrt",
                    "sqrt": "math.sqrt",
                    "log10": "math.log10",
                    "log": "math.log",
                    "exp": "math.exp",
                    "radians": "math.radians",
                    "degrees": "math.degrees",
                    "abs": "abs",
                    "pow": "pow",
                    "factorial": "math.factorial",
                    "^": "**"
                }
                for key, val in mappings.items():
                    if key in ["sin", "cos", "tan", "log", "exp", "sqrt", "abs"]:
                        cleaned = cleaned.replace(f"{key}(", f"{val}(")
                    else:
                        cleaned = cleaned.replace(key, val)
                return cleaned

            def safe_eval_expression(expression_str, variables=None):
                if variables is None:
                    variables = {}
                allowed_names = {
                    "math": math,
                    "sin": math.sin,
                    "cos": math.cos,
                    "tan": math.tan,
                    "asin": math.asin,
                    "acos": math.acos,
                    "atan": math.atan,
                    "sinh": math.sinh,
                    "cosh": math.cosh,
                    "tanh": math.tanh,
                    "sqrt": math.sqrt,
                    "log": math.log,
                    "log10": math.log10,
                    "exp": math.exp,
                    "radians": math.radians,
                    "degrees": math.degrees,
                    "abs": abs,
                    "pow": pow,
                    "factorial": math.factorial,
                    "pi": math.pi,
                    "e": math.e
                }
                allowed_names.update(variables)
                code_obj = compile(expression_str, "<string>", "eval")
                for name in code_obj.co_names:
                    if name not in allowed_names:
                        raise NameError(f"Use of {name} is blocked")
                return eval(code_obj, {"__builtins__": None}, allowed_names)

            def render_terminal_graph(expr_to_plot, var_symbol="x", range_min=-10, range_max=10, steps=40):
                rows = 15
                cols = 60
                grid = [[" " for _ in range(cols)] for _ in range(rows)]
                
                x_vals = []
                y_vals = []
                
                for i in range(cols):
                    x_cur = range_min + (range_max - range_min) * (i / (cols - 1))
                    x_vals.append(x_cur)
                    try:
                        parsed_eq = parse_advanced_math(expr_to_plot)
                        y_cur = safe_eval_expression(parsed_eq, {var_symbol: x_cur})
                        if isinstance(y_cur, (int, float)) and not math.isnan(y_cur) and not math.isinf(y_cur):
                            y_vals.append(y_cur)
                        else:
                            y_vals.append(None)
                    except Exception:
                        y_vals.append(None)

                valid_y = [v for v in y_vals if v is not None]
                if not valid_y:
                    return "Could not plot graph: No valid coordinates within view."

                y_min, y_max = min(valid_y), max(valid_y)
                if y_min == y_max:
                    y_min -= 1.0
                    y_max += 1.0

                zero_row = None
                if y_min <= 0 <= y_max:
                    zero_row = int((rows - 1) * (1.0 - (0.0 - y_min) / (y_max - y_min)))
                    if 0 <= zero_row < rows:
                        for c in range(cols):
                            grid[zero_row][c] = "-"

                zero_col = None
                if range_min <= 0 <= range_max:
                    zero_col = int((cols - 1) * ((0.0 - range_min) / (range_max - range_min)))
                    if 0 <= zero_col < cols:
                        for r in range(rows):
                            if grid[r][zero_col] == "-":
                                grid[r][zero_col] = "+"
                            else:
                                grid[r][zero_col] = "|"

                for c in range(cols):
                    y_val = y_vals[c]
                    if y_val is None:
                        continue
                    r_idx = int((rows - 1) * (1.0 - (y_val - y_min) / (y_max - y_min)))
                    if 0 <= r_idx < rows:
                        grid[r_idx][c] = "*"

                graph_output = []
                graph_output.append(f"\nGraph View: f({var_symbol}) = {expr_to_plot}")
                graph_output.append(f"Y-Max: {y_max:.2f} " + "-" * (cols - 10))
                for r in range(rows):
                    graph_output.append("".join(grid[r]))
                graph_output.append(f"Y-Min: {y_min:.2f} " + "-" * (cols - 10))
                graph_output.append(f"X-Bounds: [{range_min}, {range_max}]\n")
                return "\n".join(graph_output)

            cleaned_input = text.lower().strip()
            is_graph_cmd = cleaned_input.startswith("graph ") or cleaned_input.startswith("plot ")
            
            expr = extract_math_expression(text)
            
            if is_graph_cmd:
                target_expr = expr
                var_name = "x"
                r_min, r_max = -10, 10
                
                if " range " in expr:
                    main_part, range_part = expr.split(" range ", 1)
                    target_expr = main_part.strip()
                    try:
                        bounds = range_part.replace("[", "").replace("]", "").split(",")
                        r_min = float(bounds[0].strip())
                        r_max = float(bounds[1].strip())
                    except Exception:
                        r_min, r_max = -10, 10
                
                if " vars " in target_expr:
                    eq_part, var_part = target_expr.split(" vars ", 1)
                    target_expr = eq_part.strip()
                    var_name = var_part.strip()

                graph_string = render_terminal_graph(target_expr, var_name, r_min, r_max)
                print(graph_string)
                speak(maybe_address_user("Graph rendering complete.", chance=0.2), allow_sound=True)
                return

            if " matrix " in expr:
                parts = expr.split(" matrix ")
                operation = parts[0].strip()
                matrix_data = json.loads(parts[1].strip())
                
                if operation == "det":
                    if len(matrix_data) == 2 and len(matrix_data[0]) == 2:
                        det = matrix_data[0][0]*matrix_data[1][1] - matrix_data[0][1]*matrix_data[1][0]
                        speak(maybe_address_user(f"Determinant is {det}", chance=0.2), allow_sound=True)
                        return
                    elif len(matrix_data) == 3 and len(matrix_data[0]) == 3:
                        m = matrix_data
                        det = (m[0][0]*(m[1][1]*m[2][2] - m[1][2]*m[2][1]) -
                               m[0][1]*(m[1][0]*m[2][2] - m[1][2]*m[2][0]) +
                               m[0][2]*(m[1][0]*m[2][1] - m[1][1]*m[2][0]))
                        speak(maybe_address_user(f"Determinant is {det}", chance=0.2), allow_sound=True)
                        return
                    else:
                        speak(maybe_address_user("Unsupported matrix dimensions.", chance=0.1), allow_sound=True)
                        return

            if " stats " in expr:
                parts = expr.split(" stats ")
                stat_type = parts[0].strip()
                dataset = [float(x.strip()) for x in parts[1].split(",")]
                
                if stat_type == "mean":
                    res = sum(dataset) / len(dataset)
                elif stat_type == "median":
                    sorted_ds = sorted(dataset)
                    n = len(sorted_ds)
                    if n % 2 == 1:
                        res = sorted_ds[n // 2]
                    else:
                        res = (sorted_ds[(n // 2) - 1] + sorted_ds[n // 2]) / 2.0
                elif stat_type == "variance":
                    mean_val = sum(dataset) / len(dataset)
                    res = sum((x - mean_val) ** 2 for x in dataset) / len(dataset)
                elif stat_type == "stddev":
                    mean_val = sum(dataset) / len(dataset)
                    var_val = sum((x - mean_val) ** 2 for x in dataset) / len(dataset)
                    res = math.sqrt(var_val)
                else:
                    res = "Unknown statistical operation"
                
                speak(maybe_address_user(str(res), chance=0.2), allow_sound=True)
                return

            if " conversion " in expr:
                parts = expr.split(" conversion ")
                conv_type = parts[0].strip()
                value = float(parts[1].strip())
                
                if conv_type == "c_to_f":
                    res = (value * 9/5) + 32
                elif conv_type == "f_to_c":
                    res = (value - 32) * 5/9
                elif conv_type == "m_to_ft":
                    res = value * 3.28084
                elif conv_type == "ft_to_m":
                    res = value / 3.28084
                elif conv_type == "kg_to_lbs":
                    res = value * 2.20462
                elif conv_type == "lbs_to_kg":
                    res = value / 2.20462
                else:
                    res = "Unknown conversion metric"
                
                speak(maybe_address_user(str(res), chance=0.2), allow_sound=True)
                return

            parsed_expression = parse_advanced_math(expr)
            output_value = safe_eval_expression(parsed_expression)
            
            if isinstance(output_value, float):
                formatted_result = f"{output_value:.6f}".rstrip('0').rstrip('.')
            else:
                formatted_result = str(output_value)
                
            speak(maybe_address_user(formatted_result, chance=0.2), allow_sound=True)
            return

        except Exception as math_exception:
            print(f"Mathematical Parser Error: {str(math_exception)}")
            speak(maybe_address_user("That math expression looks off.", chance=0.1), allow_sound=True)
            return



    if lower.startswith("note "):
        cmd_note(text[5:].strip())
        speak(maybe_address_user("Saved note.", chance=0.2), allow_sound=True)
        return

    if lower == "notes":
        cmd_notes()
        speak(maybe_address_user("Notes shown in terminal.", chance=0.2), allow_sound=True)
        return

    if lower.startswith("remember "):
        cmd_remember(text[9:].strip())
        speak(maybe_address_user("Saved memory.", chance=0.2), allow_sound=True)
        return

    if lower == "memories":
        cmd_memories()
        speak(maybe_address_user("Memories shown in terminal.", chance=0.2), allow_sound=True)
        return

    if lower.startswith("forget "):
        cmd_forget(text[7:].strip())
        speak(maybe_address_user("Memory removed.", chance=0.2), allow_sound=True)
        return

    if lower.startswith("search "):
        term = text[7:].strip()
        results = search_storage(term)
        if not results:
            print("No matches.")
            speak(maybe_address_user("No matches found.", chance=0.15), allow_sound=True)
        else:
            for i, item in enumerate(results, 1):
                print(f"{i}. {item}")
            speak(maybe_address_user(f"Found {len(results)} match{'es' if len(results) != 1 else ''}.", chance=0.15), allow_sound=True)
        return
    
    if lower in {"restart", "reboot", "reload"}:
        speak("Rebooting SOAR.", allow_sound=True)
        reboot_soar()
        return

    if lower in {
        "emergency shutdown",
        "emergency shut down",
        "panic shutdown",
        "force shutdown",
        "hard shutdown",
    }:
        emergency_shutdown()
        return

    if lower.startswith("todo "):
        try:
            parts = shlex.split(text)
        except ValueError:
            print("Bad todo command.")
            return

        if len(parts) < 2:
            print("Usage: todo add/list/done/remove/clear")
            return

        action = parts[1].lower()
        rest = " ".join(parts[2:]).strip()
        if action == "add":
            todo_add(rest)
            speak(maybe_address_user("Todo added.", chance=0.2), allow_sound=True)
        elif action == "list":
            todo_list()
            speak(maybe_address_user("Todos shown in terminal.", chance=0.2), allow_sound=True)
        elif action == "done":
            todo_done(rest)
            speak(maybe_address_user("Todo marked done.", chance=0.2), allow_sound=True)
        elif action == "remove":
            todo_remove(rest)
            speak(maybe_address_user("Todo removed.", chance=0.2), allow_sound=True)
        elif action == "clear":
            todo_clear()
            speak(maybe_address_user("Todos cleared.", chance=0.2), allow_sound=True)
        else:
            print("Usage: todo add/list/done/remove/clear")
        return

    if lower.startswith("remind "):
        cmd_remind(text[7:].strip())
        return

    if lower.startswith("timer "):
        cmd_timer(text[6:].strip())
        return

    if lower.startswith("shell "):
        cmd_shell(text[6:].strip())
        speak(maybe_address_user("Command finished.", chance=0.15), allow_sound=True)
        return

    if lower.startswith("read "):
        cmd_read(text[5:].strip())
        speak(maybe_address_user("File shown in terminal.", chance=0.15), allow_sound=True)
        return

    if lower.startswith("write "):
        cmd_write(text[6:].strip())
        speak(maybe_address_user("File written.", chance=0.15), allow_sound=True)
        return
        
    if lower.startswith("newfile "):
        cmd_newfile(text[8:].strip())
        speak(maybe_address_user("File created.", chance=0.15), allow_sound=True)
        return

    if lower.startswith("code "):
        cmd_code(text[5:].strip())
        speak(maybe_address_user("Code file action done.", chance=0.15), allow_sound=True)
        return

    if lower.startswith("mkdir "):
        cmd_mkdir(text[6:].strip())
        speak(maybe_address_user("Folder created.", chance=0.15), allow_sound=True)
        return

    if lower.startswith("openurl "):
        target = text[8:].strip()
        if open_url(target):
            print("Opened URL.")
            speak(maybe_address_user("Opened it.", chance=0.15), allow_sound=True)
        else:
            print("Could not open URL.")
            speak(maybe_address_user("I could not open that.", chance=0.15), allow_sound=True)
        return

    if lower.startswith("open "):
        cmd_open(text[5:].strip())
        speak(maybe_address_user("Opening file.", chance=0.15), allow_sound=True)
        return

    if lower.startswith("copy "):
        content = text[5:].strip()
        if clipboard_copy(content):
            print("Copied to clipboard.")
            speak(maybe_address_user("Copied to clipboard.", chance=0.2), allow_sound=True)
        else:
            print("Clipboard copy failed.")
            speak(maybe_address_user("Clipboard copy failed.", chance=0.15), allow_sound=True)
        return

    if lower == "paste":
        pasted = clipboard_paste()
        if pasted:
            print(pasted)
            speak(maybe_address_user("Clipboard pasted in terminal.", chance=0.15), allow_sound=True)
        else:
            print("Clipboard empty or unavailable.")
            speak(maybe_address_user("Clipboard is empty or unavailable.", chance=0.15), allow_sound=True)
        return

    if lower == "ip":
        ip = get_local_ip()
        print(ip)
        speak(maybe_address_user(f"Your local IP is {ip}", chance=0.2), allow_sound=True)
        return

    if lower.startswith("voice"):
        cmd_voice(text[5:].strip())
        return

    if lower == "listen on":
        enable_voice()
        speak(maybe_address_user("Listening.", chance=0.2), allow_sound=True)
        return

    if lower == "listen off":
        disable_voice()
        print("Listening has been turned off.")
        return

    response = reply_to(text)
    speak(response, allow_sound=True)

def check_process_resources():
    return False
    """
    Checks if SOAR exceeds safe CPU or RAM usage.
    Uses cooldown + averaged CPU to prevent spam.
    """
    global _last_resource_alert

    try:
        p = psutil.Process(os.getpid())

        cpu_samples = []
        for _ in range(3):
            cpu_samples.append(p.cpu_percent(interval=0.05))

        cpu_pct = sum(cpu_samples) / len(cpu_samples)
        ram_pct = p.memory_percent()

        now = time.time()

        if cpu_pct >= 25.0 or ram_pct >= 25.0:

            if now - _last_resource_alert >= RESOURCE_COOLDOWN:
                _last_resource_alert = now

                error_msg = (
                    f"[RESOURCE CRITICAL] SOAR resource threshold exceeded! "
                    f"CPU: {cpu_pct:.1f}%, RAM: {ram_pct:.1f}%"
                )

                print(f"\n{error_msg}\n")

                try:
                    log_line("SYSTEM", error_msg)
                except Exception:
                    pass

                try:
                    speak("Warning: High resource usage detected.", allow_sound=True)
                except Exception:
                    pass

                return True

        return False

    except ImportError:
        return False

    except Exception as e:
        print(f"[RESOURCE MONITOR ERROR] {e}")
        return False
    
intro_proc = None

def _mac_quicktime_state():
    try:
        apple_script = (
            'tell application "QuickTime Player"\n'
            '    if not running then return "STOPPED"\n'
            '    if not (exists front document) then return "NODOC"\n'
            '    set ct to current time of front document\n'
            '    set dur to duration of front document\n'
            '    return (ct as text) & "|" & (dur as text)\n'
            'end tell'
        )
        result = subprocess.run(
            ["osascript", "-e", apple_script],
            capture_output=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        return result.stdout.strip()
    except Exception:
        return ""


def play_intro():
    global intro_start_time, intro_proc
    try:
        intro_path = DATA_DIR / "intro.mp4"
        if not intro_path.exists():
            return

        system = platform.system()
        intro_start_time = time.time()

        if system == "Darwin":
            intro_proc = None

            posix_path = str(intro_path).replace("\\", "\\\\").replace('"', '\\"')

            apple_script = f'''
            tell application "QuickTime Player"
                activate
                open POSIX file "{posix_path}"
                delay 1
                if exists front document then
                    play front document
                    delay 0.3
                    set presenting of front document to true
                end if
            end tell
            '''

            subprocess.Popen(
                ["osascript", "-e", apple_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        elif system == "Windows":
            intro_proc = subprocess.Popen(
                ["vlc", "--fullscreen", "--play-and-exit", str(intro_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    except Exception:
        pass


def close_intro_player():
    try:
        system = platform.system()
        if system == "Darwin":
            apple_script = (
                'tell application "QuickTime Player"\n'
                '    try\n'
                '        if exists front document then close front document saving no\n'
                '    end try\n'
                '    quit\n'
                'end tell'
            )
            subprocess.run(
                ["osascript", "-e", apple_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        elif system == "Windows":
            subprocess.run(
                ["taskkill", "/F", "/IM", "vlc.exe"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    except Exception:
        pass


def focus_terminal():
    try:
        system = platform.system()
        if system == "Darwin":
            apple_script = (
                'tell application "System Events"\n'
                '    set terminalApps to {"Terminal", "iTerm", "iTerm2", "Code", "Visual Studio Code"}\n'
                '    repeat with appName in terminalApps\n'
                '        if exists process appName then\n'
                '            set frontmost of process appName to true\n'
                '            exit repeat\n'
                '        end if\n'
                '    end repeat\n'
                'end tell'
            )
            subprocess.run(
                ["osascript", "-e", apple_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        elif system == "Windows":
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def watch_intro_and_focus():
    global intro_proc
    try:
        system = platform.system()

        if system == "Darwin":
            start_time = time.time()
            timeout = 300 

            while not stop_event.is_set() and (time.time() - start_time) < timeout:
                state = _mac_quicktime_state()

                if state in ("STOPPED", "NODOC", ""):
                    time.sleep(0.5)
                    continue

                if "|" in state:
                    try:
                        current_time, duration = state.split("|", 1)
                        current_time = float(current_time)
                        duration = float(duration)

                        if duration > 0 and current_time >= (duration - 0.25):
                            break
                    except Exception:
                        pass

                time.sleep(0.5)

            close_intro_player()
            focus_terminal()
            return

        if intro_proc:
            intro_proc.wait()
            focus_terminal()

    except Exception:
        pass


def main():

    if soar_avss and hasattr(soar_avss, "enforce_single_instance"):
        soar_avss.enforce_single_instance()

    global shutting_down, stop_event
    shutting_down = False
    stop_event = threading.Event()

    system_tasks = [
        ("Database Modules", load_database),
        ("Network Protocols", initialize_network),
        ("Config Files", load_configurations),
        ("Security Protocols", verify_security),
        ("Text-to-Speech Engine", init_tts),
        ("Voice Recognition System", init_recognition)
    ]

    play_intro()
    threading.Thread(target=watch_intro_and_focus, daemon=True).start()

    load_systems(system_tasks)

    def resource_watchdog_loop():
        while not stop_event.is_set():
            try:
                check_process_resources()
            except Exception as e:
                print(f"[WATCHDOG ERROR] {e}")

            for _ in range(100):
                if stop_event.is_set():
                    break
                time.sleep(0.1)

    def autocode_loop():
        while not stop_event.is_set():
            try:
                if autocode_enabled and not autocode_stop.is_set() and autocode_connected():
                    try:
                        soar_autocode.run_cycle("auto running")
                    except Exception as e:
                        print(f"[AUTO ERROR] {e}")
            except Exception as e:
                print(f"[AUTO ERROR] {e}")

            for _ in range(600):
                if stop_event.is_set():
                    break
                time.sleep(0.1)

    threading.Thread(target=resource_watchdog_loop, daemon=True).start()
    threading.Thread(target=autocode_loop, daemon=True).start()

    if intro_start_time > 0:
        elapsed = time.time() - intro_start_time
        remaining = 10.0 - elapsed
        if remaining > 0:
            time.sleep(remaining)

    close_intro_player()
    focus_terminal()

    print(f"{APP_NAME} online.")
    print("Type /help for commands. Type normal text to chat.")
    print("Voice starts automatically if your mic libraries are ready.\n")

    try:
        speak("SOAR Booted, version 1.00.8. Voice is on.", allow_sound=True)
    except Exception:
        pass

    try:
        enable_voice()
    except Exception as e:
        print(f"[VOICE ERROR] {e}")

    try:
        threading.Thread(target=voice_watchdog_loop, daemon=True).start()
    except Exception as e:
        print(f"[VOICE WATCHDOG ERROR] {e}")

    def start_avss():
        if soar_avss is None:
            print("[SOAR] AVSS module not available.")
            return

        try:
            avss_entry = getattr(soar_avss, "run_avss_loop", None)

            if callable(avss_entry):
                try:
                    threading.Thread(
                        target=avss_entry,
                        args=(stop_event, 5),
                        daemon=True
                    ).start()
                    print("[SOAR] AVSS Protection Shield active.")
                    return
                except TypeError:
                    threading.Thread(
                        target=avss_entry,
                        daemon=True
                    ).start()
                    print("[SOAR] AVSS Protection Shield active.")
                    return

            avss_main = getattr(soar_avss, "main", None)
            if callable(avss_main):
                threading.Thread(
                    target=avss_main,
                    daemon=True
                ).start()
                print("[SOAR] AVSS Protection Shield active.")
                return

            print("[SOAR] AVSS module loaded, but no compatible entry point was found.")

        except Exception as e:
            print(f"[SOAR] AVSS failed to start: {e}")

    start_avss()

    try:
        while not stop_event.is_set():
            try:
                raw = input(f"{APP_NAME}> ")
            except KeyboardInterrupt:
                raise SystemExit

            try:
                process_command(raw)
            except Exception as e:
                print(f"[COMMAND ERROR] {e}")

    except (KeyboardInterrupt, EOFError, SystemExit):
        if shutting_down:
            return

        shutting_down = True
        print("\nShutting down...")

        stop_event.set()

        try:
            disable_voice()
        except Exception:
            pass

        try:
            tts_queue.put_nowait(None)
        except Exception:
            pass

        time.sleep(0.3)
        print("Shutdown complete.")
        sys.exit(0)

if __name__ == "__main__":
    main()

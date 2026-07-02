import subprocess
import sys
import platform

def run(command):
    try:
        subprocess.check_call(command)
        return True
    except subprocess.CalledProcessError:
        return False

print("====================================")
print("SOAR Dependency Installer")
print("====================================\n")

print("Upgrading pip...")
run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

packages = [
    "pyttsx3",
    "SpeechRecognition",
    "psutil"
]

for package in packages:
    print(f"\nInstalling {package}...")
    if run([sys.executable, "-m", "pip", "install", package]):
        print(f"✓ {package} installed")
    else:
        print(f"✗ Failed to install {package}")

system = platform.system()

print("\nInstalling PyAudio...")

if system == "Windows":
    if not run([sys.executable, "-m", "pip", "install", "pyaudio"]):
        print("Trying pipwin...")
        run([sys.executable, "-m", "pip", "install", "pipwin"])
        run([sys.executable, "-m", "pipwin", "install", "pyaudio"])

elif system == "Darwin":  
    print("If PyAudio fails, run:")
    print("brew install portaudio")
    run([sys.executable, "-m", "pip", "install", "pyaudio"])

else:  
    print("If PyAudio fails, install portaudio development libraries.")
    run([sys.executable, "-m", "pip", "install", "pyaudio"])

print("\n====================================")
print("Installation Complete!")
print("====================================")

input("\nPress Enter to exit...")

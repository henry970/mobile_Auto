"""Checks that everything needed to run the tests is in place.

Run:  python check_setup.py
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OK, FAIL, WARN = "[ OK ]", "[FAIL]", "[WARN]"
problems = 0


def run(cmd: list[str]) -> str:
    try:
        exe = shutil.which(cmd[0]) or shutil.which(cmd[0] + ".cmd") or cmd[0]
        out = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=60)
        return (out.stdout + out.stderr).strip()
    except Exception:
        return ""


def check(ok: bool, label: str, fix: str = "", warn_only: bool = False) -> None:
    global problems
    if ok:
        print(f"{OK} {label}")
    else:
        print(f"{WARN if warn_only else FAIL} {label}")
        if fix:
            print(f"       -> {fix}")
        if not warn_only:
            problems += 1


print("\nChecking your mobile test setup...\n")

check(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]} (need 3.10+)",
      "Install Python 3.10 or newer from python.org")

for pkg in ("appium", "pytest", "pytest_html", "allure", "yaml"):
    try:
        __import__(pkg)
        check(True, f"Python package: {pkg}")
    except ImportError:
        check(False, f"Python package: {pkg}", "pip install -r requirements.txt")

node = run(["node", "--version"])
check(node.startswith("v") and int(node[1:].split(".")[0]) >= 18,
      f"Node.js {node or '(not found)'} (need 18+)", "Install Node.js LTS from nodejs.org")

appium = run(["appium", "--version"])
check(bool(appium) and appium[0].isdigit(), f"Appium {appium or '(not found)'}",
      "npm install -g appium")

drivers = run(["appium", "driver", "list", "--installed"])
check("uiautomator2" in drivers, "Appium UiAutomator2 driver",
      "appium driver install uiautomator2")

allure_v = run(["allure", "--version"])
check(bool(allure_v) and allure_v[0].isdigit(), f"Allure report tool {allure_v or '(not found)'}",
      "npm install -g allure-commandline  (optional: needed only to open the Allure report)", warn_only=True)

android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
check(bool(android_home) and Path(android_home).is_dir(), f"ANDROID_HOME = {android_home or '(not set)'}",
      "Re-run the setup script, or point ANDROID_HOME at your Android SDK folder")

java_home = os.environ.get("JAVA_HOME")
check(bool(java_home) or bool(shutil.which("java")), f"Java (JAVA_HOME = {java_home or 'not set'})",
      "Install Java 17 (Temurin) and set JAVA_HOME")

adb = shutil.which("adb")
if not adb and android_home:
    candidate = Path(android_home) / "platform-tools" / ("adb.exe" if os.name == "nt" else "adb")
    adb = str(candidate) if candidate.exists() else None
check(bool(adb), "adb (Android Debug Bridge)", "Install Android platform-tools")

if adb:
    lines = run([adb, "devices"]).splitlines()[1:]
    devices = [l.split()[0] for l in lines if l.strip().endswith("device")]
    unauthorized = [l.split()[0] for l in lines if "unauthorized" in l]
    if unauthorized:
        check(False, f"Device {unauthorized[0]} is unauthorized",
              "Unlock the phone and tap 'Allow' on the USB debugging popup")
    check(bool(devices), f"Connected device(s): {', '.join(devices) or 'none'}",
          "Plug in your phone with USB debugging ON, or start an emulator")

try:
    import yaml
    cfg = yaml.safe_load((ROOT / "config" / "config.yaml").read_text())
    apk = ROOT / cfg["app"]["path"]
    check(apk.is_file(), f"APK: {cfg['app']['path']}",
          "Put your APK in apps/ and update config/config.yaml (or re-run setup to get the demo app)",
          warn_only=bool(cfg["app"].get("package")))
except Exception as e:
    check(False, f"config/config.yaml readable ({e})")

print()
if problems:
    print(f"{problems} problem(s) found. Fix the items marked [FAIL] above, then run this again.")
    sys.exit(1)
print("All good! Run the tests with:  run_tests  (Windows)  or  ./run_tests.sh  (Mac/Linux)")

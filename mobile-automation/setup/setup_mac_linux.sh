#!/usr/bin/env bash
# ------------------------------------------------------------------
# One-command setup for macOS and Ubuntu/Debian Linux.
#   bash setup/setup_mac_linux.sh
# Safe to run more than once — it skips anything already installed.
# ------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")/.."
step() { printf "\n\033[36m==> %s\033[0m\n" "$1"; }
has()  { command -v "$1" >/dev/null 2>&1; }

OS="$(uname -s)"
SDK="${ANDROID_HOME:-$HOME/Android/Sdk}"
[ "$OS" = "Darwin" ] && [ -z "${ANDROID_HOME:-}" ] && [ -d "$HOME/Library/Android/sdk" ] && SDK="$HOME/Library/Android/sdk"
PROFILE="$HOME/.bashrc"; [ "$OS" = "Darwin" ] && PROFILE="$HOME/.zshrc"

step "System packages (Python, Node.js, Java 17)"
if [ "$OS" = "Darwin" ]; then
  has brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  has python3 || brew install python
  python3 -c 'import tkinter' 2>/dev/null || brew install python-tk
  if ! has node; then brew install node@20; brew link --overwrite node@20 || true; fi
  /usr/libexec/java_home -v 17 >/dev/null 2>&1 || brew install --cask temurin@17
  JAVA_HOME_VAL="$(/usr/libexec/java_home -v 17)"
else
  sudo apt-get update -y
  sudo apt-get install -y python3 python3-venv python3-pip python3-tk openjdk-17-jdk unzip curl
  if ! has node || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 18 ]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
  fi
  JAVA_HOME_VAL="$(dirname "$(dirname "$(readlink -f "$(which javac)")")")"
fi
export JAVA_HOME="$JAVA_HOME_VAL"

step "Android SDK (platform-tools + build-tools)"
SDKMANAGER="$SDK/cmdline-tools/latest/bin/sdkmanager"
if [ ! -x "$SDKMANAGER" ]; then
  PLATFORM=linux; [ "$OS" = "Darwin" ] && PLATFORM=mac
  mkdir -p "$SDK/cmdline-tools"
  curl -fsSL -o /tmp/cmdline-tools.zip \
    "https://dl.google.com/android/repository/commandlinetools-${PLATFORM}-11076708_latest.zip"
  rm -rf "$SDK/cmdline-tools/tmp" && unzip -q /tmp/cmdline-tools.zip -d "$SDK/cmdline-tools/tmp"
  rm -rf "$SDK/cmdline-tools/latest" && mv "$SDK/cmdline-tools/tmp/cmdline-tools" "$SDK/cmdline-tools/latest"
  rm -rf "$SDK/cmdline-tools/tmp"
fi
yes | "$SDKMANAGER" --licenses >/dev/null || true
"$SDKMANAGER" "platform-tools" "build-tools;34.0.0" >/dev/null
export ANDROID_HOME="$SDK"
export PATH="$PATH:$SDK/platform-tools"

if ! grep -q "ANDROID_HOME" "$PROFILE" 2>/dev/null; then
  {
    echo ""
    echo "# Added by mobile-automation setup"
    echo "export ANDROID_HOME=\"$SDK\""
    echo "export JAVA_HOME=\"$JAVA_HOME_VAL\""
    echo "export PATH=\"\$PATH:\$ANDROID_HOME/platform-tools\""
  } >> "$PROFILE"
fi

step "Appium + UiAutomator2 driver"
if ! has appium; then
  if [ "$OS" = "Darwin" ]; then npm install -g appium; else sudo npm install -g appium; fi
fi
appium driver list --installed 2>&1 | grep -q uiautomator2 || appium driver install uiautomator2

step "Allure report tool"
if ! has allure; then
  if [ "$OS" = "Darwin" ]; then npm install -g allure-commandline; else sudo npm install -g allure-commandline; fi
fi

step "Python virtual environment + packages"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip -q
.venv/bin/python -m pip install -r requirements.txt -q

step "Demo app (ApiDemos) for the sample tests"
mkdir -p apps
if [ ! -f apps/ApiDemos-debug.apk ]; then
  URL="$(curl -fsSL https://api.github.com/repos/appium/android-apidemos/releases/latest \
        | grep -o '"browser_download_url": *"[^"]*ApiDemos-debug.apk"' | head -1 | cut -d'"' -f4)"
  curl -fsSL -o apps/ApiDemos-debug.apk "$URL"
fi

step "Checking everything"
.venv/bin/python check_setup.py || true
printf "\n\033[32mSetup finished. Open a new terminal (or run: source %s) so the new PATH is picked up.\033[0m\n" "$PROFILE"

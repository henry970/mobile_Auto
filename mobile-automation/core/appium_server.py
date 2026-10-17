"""Starts and stops a local Appium server so testers never have to open a second terminal."""
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from core.config_loader import PROJECT_ROOT


class AppiumServer:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/")
        parsed = urlparse(self.server_url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 4723
        self.process: subprocess.Popen | None = None
        self.log_file = PROJECT_ROOT / "reports" / "appium.log"

    def is_running(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.server_url}/status", timeout=2) as r:
                return r.status == 200
        except Exception:
            return False

    def start(self, timeout: int = 30) -> None:
        if self.is_running():
            return  # someone already started it — reuse
        appium = shutil.which("appium") or shutil.which("appium.cmd")
        if not appium:
            raise RuntimeError(
                "Appium is not installed. Run the setup script first:\n"
                "  Windows:     setup\\setup_windows.ps1\n"
                "  Mac / Linux: bash setup/setup_mac_linux.sh"
            )
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        log = open(self.log_file, "w", encoding="utf-8")
        self.process = subprocess.Popen(
            [appium, "--address", self.host, "--port", str(self.port), "--relaxed-security"],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_running():
                return
            if self.process.poll() is not None:
                break
            time.sleep(1)
        raise RuntimeError(f"Appium did not start. See the log: {self.log_file}")

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None

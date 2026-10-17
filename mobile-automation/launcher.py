"""Test Runner — a simple window to pick and run mobile tests.

Start it with:  launcher.bat (Windows)  or  ./launcher.sh (Mac/Linux)
             or  python launcher.py
"""
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent
TESTS_DIR = ROOT / "tests"
APPS_DIR = ROOT / "apps"
REPORTS = ROOT / "reports"
IS_WIN = os.name == "nt"

_venv = ROOT / ".venv" / ("Scripts/python.exe" if IS_WIN else "bin/python")
PYTHON = str(_venv) if _venv.exists() else sys.executable

FROM_CONFIG = "App from config.yaml"
AUTO_DEVICE = "Auto (the only connected device)"


# ---------------------------------------------------------------- discovery
def discover_test_types() -> dict[str, list[str]]:
    """Dropdown label -> extra pytest arguments."""
    types = {"All tests": []}
    ini = (ROOT / "pytest.ini").read_text(encoding="utf-8")
    in_markers = False
    for line in ini.splitlines():
        if line.strip().startswith("markers"):
            in_markers = True
            continue
        if in_markers:
            if not line.startswith((" ", "\t")) or ":" not in line:
                if line.strip() and not line.startswith((" ", "\t")):
                    in_markers = False
                continue
            name, desc = line.strip().split(":", 1)
            types[f"{name.capitalize()} — {desc.strip()}"] = ["-m", name]
    for f in sorted(TESTS_DIR.glob("test_*.py")):
        doc = re.search(r'^\s*"""(.+?)(?:"""|\n)', f.read_text(encoding="utf-8"))
        label = doc.group(1).strip().rstrip(".") if doc else ""
        feature = f.stem.removeprefix("test_").replace("_", " ").title()
        types[f"Feature: {feature}" + (f" — {label}" if label else "")] = [str(f.relative_to(ROOT))]
    return types


def find_adb() -> str | None:
    adb = shutil.which("adb")
    if adb:
        return adb
    home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if home:
        p = Path(home) / "platform-tools" / ("adb.exe" if IS_WIN else "adb")
        if p.exists():
            return str(p)
    return None


def list_devices() -> dict[str, str]:
    """Label -> udid ('' means auto)."""
    devices = {AUTO_DEVICE: ""}
    adb = find_adb()
    if not adb:
        return devices
    try:
        out = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return devices
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            udid = parts[0]
            try:
                model = subprocess.run([adb, "-s", udid, "shell", "getprop", "ro.product.model"],
                                       capture_output=True, text=True, timeout=10).stdout.strip()
            except Exception:
                model = ""
            devices[f"{model or 'Android'} ({udid})"] = udid
        elif len(parts) >= 2 and parts[1] == "unauthorized":
            devices[f"⚠ {parts[0]} — tap 'Allow' on the phone"] = parts[0]
    return devices


def find_aapt() -> str | None:
    home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not home:
        return None
    tools = sorted((Path(home) / "build-tools").glob("*"), reverse=True)
    for t in tools:
        p = t / ("aapt.exe" if IS_WIN else "aapt")
        if p.exists():
            return str(p)
    return None


def apk_info(apk: Path) -> tuple[str, str]:
    """Returns (package, launch activity) read from the APK, or ('', '')."""
    aapt = find_aapt()
    if not aapt:
        return "", ""
    try:
        out = subprocess.run([aapt, "dump", "badging", str(apk)],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return "", ""
    pkg = re.search(r"package: name='([^']+)'", out)
    act = re.search(r"launchable-activity: name='([^']+)'", out)
    return (pkg.group(1) if pkg else "", act.group(1) if act else "")


# ---------------------------------------------------------------- window
class TestRunner(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mobile Test Runner")
        self.geometry("980x680")
        self.minsize(820, 560)
        self.proc: subprocess.Popen | None = None
        self.lines: queue.Queue[str | None] = queue.Queue()
        self.counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
        self.stopping = False

        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Run.TButton", font=("Segoe UI", 11, "bold"), padding=(18, 6))
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Summary.TLabel", font=("Segoe UI", 11, "bold"))

        self._build()
        self.refresh_devices()
        self.after(100, self._drain_output)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- layout ----------
    def _build(self):
        top = ttk.Frame(self, padding=(16, 12, 16, 4))
        top.pack(fill="x")
        ttk.Label(top, text="📱 Mobile Test Runner", style="Title.TLabel").pack(side="left")

        form = ttk.LabelFrame(self, text="What do you want to test?", padding=12)
        form.pack(fill="x", padx=16, pady=6)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        # Row 0: test type (the main dropdown)
        self.test_types = discover_test_types()
        ttk.Label(form, text="Test type:").grid(row=0, column=0, sticky="w", pady=4)
        self.test_type = ttk.Combobox(form, state="readonly", values=list(self.test_types))
        self.test_type.current(0)
        self.test_type.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=4)

        # Row 1: device + app
        ttk.Label(form, text="Device:").grid(row=1, column=0, sticky="w", pady=4)
        dev_box = ttk.Frame(form)
        dev_box.grid(row=1, column=1, sticky="ew", padx=(8, 16), pady=4)
        dev_box.columnconfigure(0, weight=1)
        self.device = ttk.Combobox(dev_box, state="readonly")
        self.device.grid(row=0, column=0, sticky="ew")
        ttk.Button(dev_box, text="⟳", width=3, command=self.refresh_devices).grid(row=0, column=1, padx=(4, 0))

        ttk.Label(form, text="App:").grid(row=1, column=2, sticky="w", pady=4)
        apks = [p.name for p in sorted(APPS_DIR.glob("*.apk"))]
        self.app = ttk.Combobox(form, state="readonly", values=[FROM_CONFIG, *apks])
        self.app.current(0)
        self.app.grid(row=1, column=3, sticky="ew", padx=(8, 0), pady=4)

        # Row 2: options
        ttk.Label(form, text="Video:").grid(row=2, column=0, sticky="w", pady=4)
        self.video = ttk.Combobox(form, state="readonly", width=18,
                                  values=["Only on failure", "Always", "Never"])
        self.video.current(0)
        self.video.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=4)

        ttk.Label(form, text="Retry failed tests:").grid(row=2, column=2, sticky="w", pady=4)
        self.reruns = ttk.Combobox(form, state="readonly", width=6, values=["0", "1", "2", "3"])
        self.reruns.current(0)
        self.reruns.grid(row=2, column=3, sticky="w", padx=(8, 0), pady=4)

        # Row 3: name filter
        ttk.Label(form, text="Name contains:").grid(row=3, column=0, sticky="w", pady=4)
        self.keyword = ttk.Entry(form)
        self.keyword.grid(row=3, column=1, sticky="ew", padx=(8, 16), pady=4)
        ttk.Label(form, text="(optional, e.g. checkbox or dialog)", foreground="#777").grid(
            row=3, column=2, columnspan=2, sticky="w")

        # Buttons
        bar = ttk.Frame(self, padding=(16, 4))
        bar.pack(fill="x")
        self.run_btn = ttk.Button(bar, text="▶  Run tests", style="Run.TButton", command=self.run_tests)
        self.run_btn.pack(side="left")
        self.stop_btn = ttk.Button(bar, text="■  Stop", command=self.stop_tests, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        ttk.Button(bar, text="🐞 Bug reports", command=lambda: self._open_folder(REPORTS / "bugs")).pack(side="right")
        ttk.Button(bar, text="📊 Allure report", command=self.open_allure).pack(side="right", padx=6)
        ttk.Button(bar, text="📄 HTML report", command=self.open_html).pack(side="right")

        # Summary + progress
        status = ttk.Frame(self, padding=(16, 6))
        status.pack(fill="x")
        self.summary = ttk.Label(status, text="Ready. Pick a test type and press Run.", style="Summary.TLabel")
        self.summary.pack(side="left")
        self.progress = ttk.Progressbar(status, mode="indeterminate", length=180)
        self.progress.pack(side="right")

        # Output console
        out = ttk.Frame(self, padding=(16, 0, 16, 16))
        out.pack(fill="both", expand=True)
        self.console = tk.Text(out, wrap="none", bg="#1e1e1e", fg="#d4d4d4", insertbackground="#fff",
                               font=("Consolas" if IS_WIN else "Menlo" if sys.platform == "darwin" else "Monospace", 10))
        ys = ttk.Scrollbar(out, orient="vertical", command=self.console.yview)
        self.console.configure(yscrollcommand=ys.set, state="disabled")
        self.console.pack(side="left", fill="both", expand=True)
        ys.pack(side="right", fill="y")
        for tag, color in [("pass", "#4ec9b0"), ("fail", "#f48771"), ("skip", "#dcdcaa"), ("info", "#9cdcfe")]:
            self.console.tag_configure(tag, foreground=color)

    # ---------- actions ----------
    def refresh_devices(self):
        self.devices = list_devices()
        self.device.configure(values=list(self.devices))
        self.device.current(1 if len(self.devices) > 1 else 0)

    def build_command(self) -> list[str] | None:
        cmd = [PYTHON, "-m", "pytest", *self.test_types[self.test_type.get()]]

        udid = self.devices.get(self.device.get(), "")
        if udid:
            cmd += ["--device", udid]

        if self.app.get() != FROM_CONFIG:
            apk = APPS_DIR / self.app.get()
            pkg, act = apk_info(apk)
            if not pkg:
                messagebox.showwarning(
                    "Can't read the APK",
                    f"Couldn't read the package name from {apk.name}.\n\n"
                    "Set app.path, app.package and app.activity in config/config.yaml, "
                    "then choose 'App from config.yaml'.")
                return None
            cmd += ["--app", str(apk), "--package", pkg]
            if act:
                cmd += ["--activity", act]

        cmd += ["--video", {"Only on failure": "on_failure", "Always": "always", "Never": "never"}[self.video.get()]]
        if self.reruns.get() != "0":
            cmd += ["--reruns", self.reruns.get()]
        if self.keyword.get().strip():
            cmd += ["-k", self.keyword.get().strip()]
        return cmd

    def run_tests(self):
        if self.proc:
            return
        cmd = self.build_command()
        if not cmd:
            return
        self._clear_console()
        self._write("$ " + " ".join(Path(c).name if i == 0 else c for i, c in enumerate(cmd)) + "\n\n", "info")
        self.counts = dict.fromkeys(self.counts, 0)
        self.stopping = False
        self.summary.configure(text="Running…  (the first test takes longer while the app installs)", foreground="")
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress.start(12)

        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
        kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if IS_WIN else {"start_new_session": True}
        self.proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding="utf-8", errors="replace", bufsize=1, **kwargs)
        threading.Thread(target=self._read_output, args=(self.proc,), daemon=True).start()

    def stop_tests(self):
        if not self.proc:
            return
        self.stopping = True
        self._write("\n■ Stopping…\n", "fail")
        try:
            if IS_WIN:
                self.proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(self.proc.pid, signal.SIGINT)  # lets pytest clean up and close Appium
        except Exception:
            pass
        self.after(8000, self._force_kill, self.proc)

    def _force_kill(self, proc):
        if proc.poll() is None:
            proc.kill()

    def open_html(self):
        report = REPORTS / "report.html"
        if report.exists():
            webbrowser.open(report.as_uri())
        else:
            messagebox.showinfo("No report yet", "Run the tests first.")

    def open_allure(self):
        results = REPORTS / "allure-results"
        allure = shutil.which("allure") or shutil.which("allure.cmd")
        if not allure:
            messagebox.showinfo("Allure not installed", "Install it with:\n\nnpm install -g allure-commandline")
        elif not results.exists() or not any(results.iterdir()):
            messagebox.showinfo("No report yet", "Run the tests first.")
        else:
            subprocess.Popen([allure, "serve", str(results)], cwd=ROOT)

    def _open_folder(self, folder: Path):
        if not folder.exists() or not any(folder.iterdir()):
            messagebox.showinfo("Nothing here yet", "No bug reports — no tests have failed in the last run. 🎉")
            return
        if IS_WIN:
            os.startfile(folder)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(folder)])

    # ---------- output handling ----------
    def _read_output(self, proc):
        for line in proc.stdout:
            self.lines.put(line)
        proc.wait()
        self.lines.put(None)  # finished marker

    def _drain_output(self):
        try:
            while True:
                line = self.lines.get_nowait()
                if line is None:
                    self._finished()
                    break
                self._handle_line(line)
        except queue.Empty:
            pass
        self.after(100, self._drain_output)

    def _handle_line(self, line: str):
        tag = None
        # Per-test result lines look like:  tests/test_x.py::test_name[id] PASSED   [ 40%]
        m = re.match(r"^\S.*::.*?\s(PASSED|FAILED|ERROR|SKIPPED)\s+\[", line)
        if m:
            status = m.group(1)
            tag = {"PASSED": "pass", "SKIPPED": "skip"}.get(status, "fail")
            self.counts[{"PASSED": "passed", "FAILED": "failed",
                         "ERROR": "error", "SKIPPED": "skipped"}[status]] += 1
        elif line.startswith(("FAILED ", "ERROR ", "E ")):
            tag = "fail"
        elif line.startswith("="):
            tag = "fail" if (" failed" in line or " error" in line) else "info"
        self._write(line, tag)
        if tag in ("pass", "fail", "skip"):
            c = self.counts
            self.summary.configure(text=f"Running…   ✅ {c['passed']} passed   ❌ {c['failed'] + c['error']} failed"
                                        + (f"   ⏭ {c['skipped']} skipped" if c["skipped"] else ""))

    def _finished(self):
        code = self.proc.returncode if self.proc else 1
        self.proc = None
        self.progress.stop()
        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        c = self.counts
        failed = c["failed"] + c["error"]
        if self.stopping:
            text, color = "■ Stopped", "#9a6700"
        elif code == 0:
            text, color = f"✅ All {c['passed']} tests passed", "#1a7f37"
        elif code == 5:
            text, color = "No tests matched your selection", "#9a6700"
        else:
            text, color = (f"❌ {failed} failed, {c['passed']} passed — see 🐞 Bug reports", "#cf222e") if failed \
                else ("❌ Run failed to start — read the output below", "#cf222e")
        self.summary.configure(text=text, foreground=color)

    def _write(self, text: str, tag: str | None = None):
        self.console.configure(state="normal")
        self.console.insert("end", text, tag or ())
        self.console.see("end")
        self.console.configure(state="disabled")

    def _clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def _on_close(self):
        if self.proc and not messagebox.askyesno("Tests are running", "Stop the tests and close?"):
            return
        if self.proc:
            self.stop_tests()
        self.destroy()


if __name__ == "__main__":
    TestRunner().mainloop()

"""pytest setup: config, Appium server, driver, and failure evidence
(screenshot, video, logcat, crash detection, auto bug report)."""
import base64
import re
import shutil
from datetime import datetime

import pytest

from core import artifacts
from core.appium_server import AppiumServer
from core.config_loader import PROJECT_ROOT, load_config
from core.driver_factory import create_driver
from core.reporting import RUN, StepLog, attach_bytes, device_info, write_allure_environment

REPORTS = PROJECT_ROOT / "reports"
EVIDENCE_DIRS = ["screenshots", "videos", "logcat", "bugs"]


# ---------- command-line options ----------
def pytest_addoption(parser):
    group = parser.getgroup("mobile")
    group.addoption("--app", help="Path to the APK under test")
    group.addoption("--package", help="App package, e.g. com.example.app")
    group.addoption("--activity", help="Launch activity, e.g. .MainActivity")
    group.addoption("--device", help="Device UDID from 'adb devices'")
    group.addoption("--server", help="Appium server URL")
    group.addoption("--no-auto-appium", action="store_true",
                    help="Don't start Appium automatically")
    group.addoption("--video", choices=["always", "on_failure", "never"],
                    help="Override reports.video from config.yaml")


def pytest_sessionstart(session):
    """Start every run with clean evidence folders."""
    for d in EVIDENCE_DIRS:
        shutil.rmtree(REPORTS / d, ignore_errors=True)
    REPORTS.mkdir(exist_ok=True)


def pytest_html_report_title(report):
    report.title = "Mobile App Test Report"


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def config(request):
    opt = request.config.getoption
    cfg = load_config({
        "app": opt("--app"), "package": opt("--package"), "activity": opt("--activity"),
        "device": opt("--device"), "server": opt("--server"),
    })
    if opt("--video"):
        cfg["reports"]["video"] = opt("--video")
    return cfg


@pytest.fixture(scope="session")
def appium_server(config, request):
    server = AppiumServer(config["appium"]["server_url"])
    auto = config["appium"].get("auto_start", True) and not request.config.getoption("--no-auto-appium")
    if auto:
        server.start()
    elif not server.is_running():
        pytest.exit(f"Appium is not running at {server.server_url}", returncode=3)
    yield server
    server.stop()  # only stops a server this run started


@pytest.fixture(scope="session")
def _session_driver(config, appium_server):
    drv = create_driver(config)
    RUN["cfg"] = config
    RUN["device"] = device_info(drv, config)
    write_allure_environment(REPORTS / "allure-results", RUN["device"])
    yield drv
    drv.quit()


@pytest.fixture
def driver(_session_driver, config):
    """A driver with the app freshly restarted for every test."""
    drv = _session_driver
    StepLog.reset()
    package = config["app"]["package"]
    if package:
        drv.terminate_app(package)
        drv.activate_app(package)
    artifacts.flush_logcat(drv)
    rep = config["reports"]
    drv._recording = rep.get("video", "never") != "never" and artifacts.start_video(
        drv, rep.get("video_time_limit", 180)
    )
    yield drv
    if getattr(drv, "_recording", False):  # e.g. the test errored before the report hook ran
        artifacts.stop_video(drv)
        drv._recording = False


# ---------- evidence collection after each test ----------
def _html_extras():
    try:
        import pytest_html
        return pytest_html.extras
    except ImportError:
        return None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    drv = item.funcargs.get("driver")
    cfg = RUN.get("cfg")
    if report.when != "call" or drv is None or cfg is None:
        return

    rep = cfg["reports"]
    package = cfg["app"].get("package", "")
    name = re.sub(r"[^\w.-]", "_", item.name)[:100]
    stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
    extras_mod = _html_extras()
    extras = getattr(report, "extras", [])
    files: dict = {"Screenshot": None, "Video": None, "Logcat": None}

    # 1) logcat + crash detection
    lines = artifacts.read_logcat(drv) if (rep.get("logcat") != "never" or rep.get("fail_on_crash")) else []
    crashes = artifacts.find_crashes(lines, package)
    if crashes and report.passed and rep.get("fail_on_crash", True):
        report.outcome = "failed"
        report.longrepr = "App crash detected in logcat (the test's own checks passed):\n\n" + crashes[0]
    failed = report.failed

    # 2) screenshot
    if failed and rep.get("screenshot_on_failure", True):
        try:
            png_b64 = drv.get_screenshot_as_base64()
            png = base64.b64decode(png_b64)
            path = REPORTS / "screenshots" / f"{name}_{stamp}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(png)
            files["Screenshot"] = path.relative_to(PROJECT_ROOT)
            attach_bytes(png, "Screenshot on failure", "png")
            if extras_mod:
                extras.append(extras_mod.png(png_b64, name="Screenshot"))
        except Exception:
            pass

    # 3) video
    if getattr(drv, "_recording", False):
        video = artifacts.stop_video(drv)
        drv._recording = False
        if video and (failed or rep.get("video") == "always"):
            path = REPORTS / "videos" / f"{name}_{stamp}.mp4"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(video)
            files["Video"] = path.relative_to(PROJECT_ROOT)
            attach_bytes(video, "Screen recording", "mp4")
            if extras_mod:
                rel = path.relative_to(REPORTS).as_posix()
                extras.append(extras_mod.html(
                    f'<div><b>Screen recording:</b><br><video controls width="320" src="{rel}"></video></div>'
                ))

    # 4) logcat file
    if lines and (failed or rep.get("logcat") == "always") and rep.get("logcat") != "never":
        text = "\n".join(lines)
        path = REPORTS / "logcat" / f"{name}_{stamp}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        files["Logcat"] = path.relative_to(PROJECT_ROOT)
        attach_bytes(text.encode(), "Logcat", "text")
        if extras_mod:
            extras.append(extras_mod.text("\n".join(lines[-300:]), name="Logcat (last 300 lines)"))

    # 5) bug report
    if failed and rep.get("bug_report", True):
        if call.excinfo is not None:
            err_type, err_msg = call.excinfo.typename, str(call.excinfo.value)
        else:
            err_type, err_msg = "AppCrash", crashes[0] if crashes else "Test failed"
        bug = artifacts.write_bug_report(
            REPORTS / "bugs", item.name, item.obj.__doc__ or "", StepLog.all(),
            err_type, err_msg, RUN["device"], crashes, files,
        )
        attach_bytes(bug.read_bytes(), "Bug report", "text")
        if extras_mod:
            extras.append(extras_mod.text(bug.read_text(encoding="utf-8"), name="Bug report"))

    report.extras = extras

"""Step logging + Allure helpers.

Use `step()` in tests or page objects to make readable steps that appear in
the Allure report AND in the auto-generated bug report:

    from core.reporting import step
    with step("Log in as a standard user"):
        LoginPage(driver).login("user@test.com", "Secret123")
"""
from contextlib import contextmanager, nullcontext
from pathlib import Path

try:
    import allure
    from allure_commons.types import AttachmentType
    HAS_ALLURE = True
except ImportError:  # framework still works without allure-pytest
    allure = None
    AttachmentType = None
    HAS_ALLURE = False

# Shared state for the current run (filled in by conftest.py)
RUN: dict = {"cfg": None, "device": {}}


class StepLog:
    """Keeps the steps of the test that is currently running."""
    _steps: list[str] = []

    @classmethod
    def reset(cls) -> None:
        cls._steps = []

    @classmethod
    def add(cls, text: str) -> None:
        cls._steps.append(text)

    @classmethod
    def all(cls) -> list[str]:
        return list(cls._steps)


@contextmanager
def step(title: str):
    StepLog.add(title)
    ctx = allure.step(title) if HAS_ALLURE else nullcontext()
    with ctx:
        yield


def attach_bytes(data: bytes, name: str, kind: str) -> None:
    """kind: png | mp4 | text"""
    if not HAS_ALLURE:
        return
    types = {"png": AttachmentType.PNG, "mp4": AttachmentType.MP4, "text": AttachmentType.TEXT}
    allure.attach(data, name=name, attachment_type=types[kind])


def device_info(driver, cfg: dict) -> dict:
    """Collects device + app details for reports. Never raises."""
    info = {
        "Platform": "Android",
        "Device UDID": driver.capabilities.get("deviceUDID") or driver.capabilities.get("udid", ""),
        "App package": cfg["app"].get("package", ""),
    }
    try:
        d = driver.execute_script("mobile: deviceInfo")
        info.update({
            "Device": f"{d.get('manufacturer', '')} {d.get('model', '')}".strip(),
            "Android version": d.get("platformVersion", ""),
            "API level": d.get("apiVersion", ""),
            "Screen": d.get("realDisplaySize", ""),
        })
    except Exception:
        info["Device"] = driver.capabilities.get("deviceModel", "")
        info["Android version"] = driver.capabilities.get("platformVersion", "")
    try:  # app version (needs Appium started with --relaxed-security, which we do)
        out = driver.execute_script(
            "mobile: shell", {"command": "dumpsys", "args": ["package", cfg["app"]["package"]]}
        )
        for line in str(out).splitlines():
            if "versionName=" in line:
                info["App version"] = line.split("versionName=")[1].strip()
                break
    except Exception:
        pass
    return {k: v for k, v in info.items() if v}


def write_allure_environment(results_dir: Path, info: dict) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"{k.replace(' ', '.')}={v}" for k, v in info.items()]
    (results_dir / "environment.properties").write_text("\n".join(lines), encoding="utf-8")

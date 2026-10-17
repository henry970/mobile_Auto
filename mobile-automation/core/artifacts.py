"""Video recording, logcat capture, crash detection and bug reports."""
import base64
from datetime import datetime
from pathlib import Path


# ---------------- video ----------------
def start_video(driver, time_limit: int = 180) -> bool:
    try:
        driver.start_recording_screen(timeLimit=str(time_limit), forceRestart=True)
        return True
    except Exception:
        return False


def stop_video(driver) -> bytes | None:
    try:
        b64 = driver.stop_recording_screen()
        return base64.b64decode(b64) if b64 else None
    except Exception:
        return None


# ---------------- logcat ----------------
def flush_logcat(driver) -> None:
    """Reading the log marks it as read, so the next read only has new lines."""
    try:
        driver.get_log("logcat")
    except Exception:
        pass


def read_logcat(driver) -> list[str]:
    try:
        return [e.get("message", "") for e in driver.get_log("logcat")]
    except Exception:
        return []


def find_crashes(lines: list[str], package: str = "") -> list[str]:
    """Returns crash / ANR blocks that belong to the app under test."""
    crashes = []
    for i, line in enumerate(lines):
        if "FATAL EXCEPTION" in line:
            block = lines[i:i + 40]
            if not package or any(package in l for l in block):
                # keep the block up to the first line that isn't part of the stack trace
                out = [block[0]]
                for l in block[1:]:
                    if "AndroidRuntime" not in l and "\tat " not in l and "Caused by" not in l:
                        break
                    out.append(l)
                crashes.append("\n".join(out))
        elif "ANR in" in line and (not package or package in line):
            crashes.append("\n".join(lines[i:i + 10]))
    return crashes


# ---------------- bug report ----------------
def write_bug_report(
    out_dir: Path,
    test_name: str,
    test_doc: str,
    steps: list[str],
    error_type: str,
    error_message: str,
    device: dict,
    crashes: list[str],
    files: dict[str, Path | None],
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    title_hint = crashes and "App crashes" or (error_message.splitlines() or ["Test failed"])[0][:90]

    md = [
        f"# Bug: {test_name} — {title_hint}",
        "",
        f"**Date:** {now:%Y-%m-%d %H:%M}  ",
        f"**Severity (suggested):** {'Critical' if crashes else 'Major'}  ",
        f"**Found by:** automated test `{test_name}`",
        "",
        "## Environment",
        *[f"- **{k}:** {v}" for k, v in device.items()],
        "",
        "## Steps to reproduce",
    ]
    md += [f"{n}. {s}" for n, s in enumerate(steps, 1)] or ["1. Run the test above"]
    md += [
        "",
        "## Expected result",
        test_doc.strip() or "The test passes (see the assertion below).",
        "",
        "## Actual result",
        "The app crashed (see crash log below)." if crashes else f"`{error_type}`",
        "",
        "```",
        error_message.strip()[:2000] or "(no message)",
        "```",
    ]
    if crashes:
        md += ["", "## Crash log", "```", "\n\n".join(crashes)[:4000], "```"]
    attached = {k: v for k, v in files.items() if v}
    if attached:
        md += ["", "## Attachments"]
        md += [f"- {k}: `{v.as_posix()}`" for k, v in attached.items()]

    path = out_dir / f"BUG_{test_name}_{now:%Y%m%d_%H%M%S}.md"
    path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return path

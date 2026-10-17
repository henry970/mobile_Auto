# Mobile App Automation — Appium + Selenium (Python) + pytest

Automated tests for **native Android apps (APKs)**, using:

- **Appium** (UiAutomator2) to drive the phone
- **Selenium / Appium Python client** for the test code
- **pytest** to run tests, with **Allure** and **HTML** reports
- **Automatic failure evidence**: screenshot, screen video, logcat, crash detection and a ready-to-paste bug report
- **Page Object Model**, so each screen's locators live in one place

Appium is started and stopped for you automatically. You never need a second terminal.

---

## 1. Setup (one time, about 10 minutes)

### Step 1: Prepare your phone
1. Open **Settings → About phone** and tap **Build number** 7 times. This unlocks Developer options.
2. Open **Settings → Developer options** and turn on **USB debugging**.
3. Plug the phone into your computer with a USB cable, then tap **Allow** on the popup.

*(An Android emulator from Android Studio works too, with no phone needed.)*

### Step 2: Run the setup script
This installs Python, Node.js, Java 17, the Android SDK tools, Appium, the UiAutomator2 driver, the Python packages, and the demo app.

**Windows** (PowerShell as Administrator, in this folder):
```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force; .\setup\setup_windows.ps1
```

**Mac / Linux:**
```bash
bash setup/setup_mac_linux.sh
```

Close and reopen the terminal when it finishes.

### Step 3: Check everything
```bash
python check_setup.py
```
Every line should show `[ OK ]`. Each `[FAIL]` line tells you exactly how to fix it.

---

## 2. Run the tests

### Easiest: the Test Runner window
Double-click **`launcher.bat`** (Windows), or run `./launcher.sh` (Mac/Linux).

| Dropdown | Choices |
|---|---|
| **Test type** | All tests · Smoke · Regression · or one feature (Controls, Dialogs, …) |
| **Device** | Any connected phone or emulator (press ⟳ after plugging one in) |
| **App** | The app in `config.yaml`, or any APK you dropped into `apps/` (package and activity are detected automatically) |
| **Video** | Only on failure · Always · Never |
| **Retry failed tests** | 0–3 |
| **Name contains** | Optional filter, e.g. `checkbox` |

Press **▶ Run tests** to watch results live in green and red. When the run finishes, use the **📄 HTML report**, **📊 Allure report** and **🐞 Bug reports** buttons.

New test files and new markers in `pytest.ini` appear in the **Test type** dropdown automatically.

### From the command line

| What | Windows | Mac / Linux |
|---|---|---|
| All tests | `run_tests` | `./run_tests.sh` |
| Smoke tests only | `run_tests -m smoke` | `./run_tests.sh -m smoke` |
| One file | `run_tests tests\test_controls.py` | `./run_tests.sh tests/test_controls.py` |
| Retry flaky tests twice | `run_tests --reruns 2` | `./run_tests.sh --reruns 2` |
| A specific phone | `run_tests --device <udid>` | `./run_tests.sh --device <udid>` |

### Reports
| Report | How to open |
|---|---|
| **Allure dashboard** (steps, charts, attachments) | `open_allure_report` (Windows) or `./open_allure_report.sh` (Mac/Linux) |
| **Simple HTML report** | open `reports/report.html` in your browser |

### What you get for every failed test
| Evidence | Where |
|---|---|
| 📸 Screenshot at the moment of failure | `reports/screenshots/`, plus both reports |
| 🎥 Screen recording of the whole test | `reports/videos/`, plus both reports |
| 📜 Device log (logcat) | `reports/logcat/`, plus both reports |
| 🐞 **Ready-to-paste bug report** with steps, expected vs actual, device, app version and crash log | `reports/bugs/BUG_<test>.md`, plus both reports |
| 💥 **Crash detection**: if the app crashes (`FATAL EXCEPTION`) or freezes (ANR), the test fails even if its own checks passed | shown in the report and the bug report |

The Appium server log is in `reports/appium.log`. Evidence folders are cleared at the start of each run.

Control all of this in the `reports:` section of `config/config.yaml`:
```yaml
reports:
  screenshot_on_failure: true
  video: "on_failure"       # always | on_failure | never
  logcat: "on_failure"      # always | on_failure | never
  fail_on_crash: true
  bug_report: true
```

### Make bug reports read well
- **Steps** are recorded automatically from page actions (`Tap 'Login'`, `Type 'x' into 'email'`, `Open 'Settings'`…). Add your own with:
  ```python
  from core.reporting import step
  with step("Log in as a premium user"):
      ...
  ```
- **Expected result** comes from the test's docstring, so write one line describing what should happen:
  ```python
  def test_valid_login(driver):
      """The user lands on the Home screen and sees 'Welcome'."""
  ```

---

## 3. Test YOUR app

1. Copy your APK into the `apps/` folder.
2. Find its package and launch activity (with the app open on the phone):
   ```bash
   adb shell dumpsys window | findstr mCurrentFocus     # Windows
   adb shell dumpsys window | grep mCurrentFocus        # Mac / Linux
   ```
   The output looks like `com.mycompany.app/.MainActivity`, which means package = `com.mycompany.app` and activity = `.MainActivity`.
3. Update the `app:` section of `config/config.yaml`:
   ```yaml
   app:
     path: "apps/myapp.apk"
     package: "com.mycompany.app"
     activity: ".MainActivity"
   ```
4. Find element locators with **[Appium Inspector](https://github.com/appium/appium-inspector/releases)** (a free desktop app). Start Appium (`appium`), connect the Inspector, click any button on the screenshot, and copy its `resource-id` or `content-desc`.
5. Create a page object in `pages/` and tests in `tests/`, following the examples.

**Locator priority (most to least stable):**
1. `AppiumBy.ACCESSIBILITY_ID`, using content-desc
2. `AppiumBy.ID`, using resource-id such as `com.app:id/login_button`
3. `BasePage.by_text("Login")`, using the visible text
4. `AppiumBy.XPATH`, as a last resort because it's slow and fragile

---

## 4. Writing tests (cheat sheet)

```python
# pages/login_page.py
from appium.webdriver.common.appiumby import AppiumBy
from core.base_page import BasePage

class LoginPage(BasePage):
    EMAIL    = (AppiumBy.ID, "com.mycompany.app:id/email")
    PASSWORD = (AppiumBy.ID, "com.mycompany.app:id/password")
    LOGIN    = (AppiumBy.ACCESSIBILITY_ID, "Login")
    ERROR    = (AppiumBy.ID, "com.mycompany.app:id/error")

    def login(self, email, password):
        self.type_text(self.EMAIL, email)
        self.type_text(self.PASSWORD, password)
        self.hide_keyboard()
        self.tap(self.LOGIN)
```

```python
# tests/test_login.py
import pytest
from pages.login_page import LoginPage

@pytest.mark.smoke
def test_valid_login(driver):
    LoginPage(driver).login("user@test.com", "Secret123")
    assert LoginPage(driver).is_text_visible("Welcome")
```

**Actions available in every page (`core/base_page.py`):**
`tap` · `tap_text` · `type_text` · `get_text` · `get_attribute` · `is_checked` · `is_visible` · `is_text_visible` · `scroll_to_text` · `swipe("up"|"down"|"left"|"right")` · `long_press` · `back` · `hide_keyboard` · `find` · `find_all`

All waits are automatic (explicit waits, 15 seconds by default, set in `config.yaml`).

---

## 5. Project structure

```
mobile-automation/
├── config/config.yaml        ← app path, package, device, timeouts
├── core/
│   ├── base_page.py          ← reusable actions (tap, type, swipe, scroll…)
│   ├── driver_factory.py     ← builds the Appium driver
│   ├── appium_server.py      ← auto-starts / stops Appium
│   ├── artifacts.py          ← video, logcat, crash detection, bug reports
│   ├── reporting.py          ← steps + Allure helpers
│   └── config_loader.py
├── pages/                    ← one class per app screen (Page Object Model)
├── tests/                    ← pytest tests (smoke + regression)
├── data/test_data.json       ← data for parametrized tests
├── apps/                     ← put APKs here
├── reports/                  ← HTML/Allure reports, screenshots, videos, logcat, bugs
├── setup/                    ← one-command setup scripts
├── check_setup.py            ← "is everything ready?" checker
├── conftest.py               ← fixtures + screenshot-on-failure
├── launcher.py             ← Test Runner window (launcher.bat / launcher.sh)
├── run_tests.bat / .sh
├── open_allure_report.bat / .sh
└── .github/workflows/        ← runs tests on an emulator in GitHub Actions
```

---

## 6. Troubleshooting

| Problem | Fix |
|---|---|
| `adb devices` shows `unauthorized` | Unlock the phone and tap **Allow** on the USB debugging popup |
| No device listed | Try another cable (some only charge) and check that USB debugging is on |
| Windows doesn't detect the phone | Install your phone maker's USB driver (Samsung, Tecno/Infinix, Xiaomi, etc.) |
| Xiaomi / Redmi / POCO: taps don't work | Developer options → turn on **USB debugging (Security settings)** and **Install via USB** |
| `Element not found` | Check the locator in Appium Inspector. The screen may not have loaded yet, so increase `timeouts.explicit` |
| Video is missing | Some emulators or phones block screen recording, so the test still runs without it. One recording is limited to 180 s |
| `allure` not found | `npm install -g allure-commandline` (needs Java, which setup installs) |
| Test Runner won't open on Linux | `sudo apt install python3-tk` |
| Appium won't start | Open `reports/appium.log`, or run `appium` by hand to see the error |
| `ANDROID_HOME` / `JAVA_HOME` not set | Reopen the terminal after setup, or re-run the setup script |

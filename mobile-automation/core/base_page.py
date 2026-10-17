"""Reusable actions every page object inherits.

Locators are tuples, for example:
    LOGIN = (AppiumBy.ACCESSIBILITY_ID, "Login")
    EMAIL = (AppiumBy.ID, "com.example:id/email")
    TITLE = (AppiumBy.XPATH, "//android.widget.TextView[@text='Home']")
"""
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.reporting import step

Locator = tuple[str, str]


def describe(locator: Locator) -> str:
    """Readable name for a locator in steps/bug reports, e.g. 'check1'."""
    value = locator[1]
    marker = 'text("'
    if marker in value:
        name = value.split(marker, 1)[1].split('"', 1)[0]
    else:
        name = value.split("/")[-1]
    return "'" + name + "'"


class BasePage:
    def __init__(self, driver, timeout: int = 15):
        self.driver = driver
        self.timeout = timeout

    # ---------- finding ----------
    def wait(self, timeout: int | None = None) -> WebDriverWait:
        return WebDriverWait(self.driver, timeout or self.timeout)

    def find(self, locator: Locator, timeout: int | None = None):
        return self.wait(timeout).until(
            EC.presence_of_element_located(locator), message=f"Element not found: {locator}"
        )

    def find_all(self, locator: Locator):
        return self.driver.find_elements(*locator)

    @staticmethod
    def by_text(text: str) -> Locator:
        return (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{text}")')

    @staticmethod
    def by_text_contains(text: str) -> Locator:
        return (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().textContains("{text}")')

    # ---------- actions ----------
    def tap(self, locator: Locator) -> None:
        with step(f"Tap {describe(locator)}"):
            self.wait().until(
                EC.element_to_be_clickable(locator), message=f"Not clickable: {locator}"
            ).click()

    def tap_text(self, text: str) -> None:
        self.tap(self.by_text(text))

    def type_text(self, locator: Locator, text: str, clear: bool = True) -> None:
        with step(f"Type '{text}' into {describe(locator)}"):
            el = self.find(locator)
            if clear:
                el.clear()
            el.send_keys(text)

    def get_text(self, locator: Locator) -> str:
        return self.find(locator).text

    def get_attribute(self, locator: Locator, name: str) -> str:
        return self.find(locator).get_attribute(name)

    def is_checked(self, locator: Locator) -> bool:
        return self.get_attribute(locator, "checked") == "true"

    def scroll_to_text(self, text: str):
        """Scroll the first scrollable view until an element with this text is visible."""
        with step(f"Scroll to '{text}'"):
            return self._scroll_into_view(text)

    def _scroll_into_view(self, text: str):
        selector = (
            "new UiScrollable(new UiSelector().scrollable(true).instance(0))"
            f'.scrollIntoView(new UiSelector().text("{text}"))'
        )
        return self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, selector)

    def swipe(self, direction: str = "up", percent: float = 0.75) -> None:
        """Swipe the whole screen: direction = up / down / left / right."""
        size = self.driver.get_window_size()
        area = {
            "left": int(size["width"] * 0.1),
            "top": int(size["height"] * 0.2),
            "width": int(size["width"] * 0.8),
            "height": int(size["height"] * 0.6),
        }
        with step(f"Swipe {direction}"):
            self.driver.execute_script(
                "mobile: swipeGesture", {**area, "direction": direction, "percent": percent}
            )

    def long_press(self, locator: Locator, duration_ms: int = 1000) -> None:
        with step(f"Long-press {describe(locator)}"):
            el = self.find(locator)
            self.driver.execute_script(
                "mobile: longClickGesture", {"elementId": el.id, "duration": duration_ms}
            )

    def back(self) -> None:
        with step("Press Back"):
            self.driver.back()

    def hide_keyboard(self) -> None:
        try:
            if self.driver.is_keyboard_shown():
                self.driver.hide_keyboard()
        except Exception:
            pass

    # ---------- checks ----------
    def is_visible(self, locator: Locator, timeout: int = 5) -> bool:
        try:
            self.wait(timeout).until(EC.visibility_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def is_text_visible(self, text: str, timeout: int = 5) -> bool:
        return self.is_visible(self.by_text(text), timeout)

    def current_activity(self) -> str:
        return self.driver.current_activity

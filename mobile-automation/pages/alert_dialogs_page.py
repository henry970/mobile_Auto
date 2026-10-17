"""App > Alert Dialogs — buttons that open system dialogs."""
from appium.webdriver.common.appiumby import AppiumBy

from core.base_page import BasePage
from pages.home_page import HomePage


class AlertDialogsPage(BasePage):
    OK_CANCEL_BUTTON_TEXT = "OK Cancel dialog with a message"
    DIALOG_OK = (AppiumBy.ID, "android:id/button1")
    DIALOG_CANCEL = (AppiumBy.ID, "android:id/button2")

    @classmethod
    def open_from_home(cls, driver) -> "AlertDialogsPage":
        HomePage(driver).open("App", "Alert Dialogs")
        return cls(driver)

    def open_ok_cancel_dialog(self) -> None:
        self.tap_text(self.OK_CANCEL_BUTTON_TEXT)

    def is_dialog_open(self, timeout: int = 5) -> bool:
        return self.is_visible(self.DIALOG_OK, timeout)

    def press_ok(self) -> None:
        self.tap(self.DIALOG_OK)

    def press_cancel(self) -> None:
        self.tap(self.DIALOG_CANCEL)

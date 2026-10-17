"""Views > Controls > 1. Light Theme — a form with a text field, checkboxes, radios and toggles."""
from appium.webdriver.common.appiumby import AppiumBy

from core.base_page import BasePage
from pages.home_page import HomePage

PKG = "io.appium.android.apis:id"


class ControlsPage(BasePage):
    TEXT_FIELD = (AppiumBy.ID, f"{PKG}/edit")
    CHECKBOX_1 = (AppiumBy.ID, f"{PKG}/check1")
    CHECKBOX_2 = (AppiumBy.ID, f"{PKG}/check2")
    RADIO_1 = (AppiumBy.ID, f"{PKG}/radio1")
    RADIO_2 = (AppiumBy.ID, f"{PKG}/radio2")
    TOGGLE_1 = (AppiumBy.ID, f"{PKG}/toggle1")

    @classmethod
    def open_from_home(cls, driver) -> "ControlsPage":
        HomePage(driver).open("Views", "Controls", "1. Light Theme")
        page = cls(driver)
        page.find(page.TEXT_FIELD)
        return page

    def enter_text(self, text: str) -> None:
        self.type_text(self.TEXT_FIELD, text)
        self.hide_keyboard()

    def entered_text(self) -> str:
        return self.get_text(self.TEXT_FIELD)

    def toggle_checkbox_1(self) -> None:
        self.tap(self.CHECKBOX_1)

    def select_radio(self, number: int) -> None:
        self.tap(self.RADIO_1 if number == 1 else self.RADIO_2)

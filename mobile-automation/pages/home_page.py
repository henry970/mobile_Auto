"""Home screen of the ApiDemos sample app (a list of menu items)."""
from appium.webdriver.common.appiumby import AppiumBy

from core.base_page import BasePage
from core.reporting import step


class HomePage(BasePage):
    MENU_LIST = (AppiumBy.ID, "android:id/list")
    MENU_ITEMS = ["Accessibility", "Animation", "App", "Content", "Graphics", "Media",
                  "NFC", "OS", "Preference", "Text", "Views"]

    def is_loaded(self) -> bool:
        return self.is_visible(self.MENU_LIST, timeout=15)

    def open(self, *path: str) -> None:
        """Open a menu path, e.g. open("Views", "Controls", "1. Light Theme")."""
        for item in path:
            with step(f"Open '{item}'"):
                self._scroll_into_view(item).click()

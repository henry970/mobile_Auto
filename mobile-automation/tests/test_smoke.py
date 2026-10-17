"""Smoke tests: does the app open and show its main screen?"""
import pytest

from pages.home_page import HomePage


@pytest.mark.smoke
def test_app_launches(driver, config):
    """The app opens and is in the foreground."""
    assert driver.current_package == config["app"]["package"]


@pytest.mark.smoke
def test_home_menu_is_visible(driver):
    """The home screen shows the main menu, including the 'App' item."""
    home = HomePage(driver)
    assert home.is_loaded(), "Home menu did not load"
    assert home.is_text_visible("App")


@pytest.mark.smoke
def test_scroll_to_last_menu_item(driver):
    """Scrolling the home menu reaches the last item, 'Views'."""
    home = HomePage(driver)
    assert home.scroll_to_text("Views").is_displayed()

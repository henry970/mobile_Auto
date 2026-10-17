"""System dialogs: open, confirm, cancel."""
import pytest

from pages.alert_dialogs_page import AlertDialogsPage


@pytest.mark.regression
def test_dialog_closes_on_ok(driver):
    """The OK/Cancel dialog opens and closes when OK is pressed."""
    page = AlertDialogsPage.open_from_home(driver)
    page.open_ok_cancel_dialog()
    assert page.is_dialog_open()
    page.press_ok()
    assert not page.is_dialog_open(timeout=2)


@pytest.mark.regression
def test_dialog_closes_on_cancel(driver):
    """The OK/Cancel dialog closes when Cancel is pressed."""
    page = AlertDialogsPage.open_from_home(driver)
    page.open_ok_cancel_dialog()
    page.press_cancel()
    assert not page.is_dialog_open(timeout=2)


@pytest.mark.regression
def test_back_button_returns_home(driver):
    """Pressing Back twice from Alert Dialogs returns to the home menu."""
    page = AlertDialogsPage.open_from_home(driver)
    page.back()
    page.back()
    assert page.is_text_visible("Accessibility")

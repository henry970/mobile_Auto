"""Form controls: typing, checkboxes, radio buttons."""
import json
from pathlib import Path

import pytest

from pages.controls_page import ControlsPage

DATA = json.loads((Path(__file__).parent.parent / "data" / "test_data.json").read_text())


@pytest.mark.regression
@pytest.mark.parametrize("text", DATA["text_inputs"])
def test_type_into_text_field(driver, text):
    """The text field shows exactly what was typed."""
    page = ControlsPage.open_from_home(driver)
    page.enter_text(text)
    assert page.entered_text() == text


@pytest.mark.regression
def test_checkbox_can_be_checked_and_unchecked(driver):
    """Checkbox 1 starts unchecked, becomes checked on tap, and unchecked on a second tap."""
    page = ControlsPage.open_from_home(driver)
    assert not page.is_checked(page.CHECKBOX_1)
    page.toggle_checkbox_1()
    assert page.is_checked(page.CHECKBOX_1)
    page.toggle_checkbox_1()
    assert not page.is_checked(page.CHECKBOX_1)


@pytest.mark.regression
def test_only_one_radio_selected(driver):
    """Selecting a radio button deselects the other one."""
    page = ControlsPage.open_from_home(driver)
    page.select_radio(1)
    assert page.is_checked(page.RADIO_1) and not page.is_checked(page.RADIO_2)
    page.select_radio(2)
    assert page.is_checked(page.RADIO_2) and not page.is_checked(page.RADIO_1)

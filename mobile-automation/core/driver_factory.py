"""Creates the Appium driver from config."""
from pathlib import Path

from appium import webdriver
from appium.options.android import UiAutomator2Options


def create_driver(cfg: dict) -> webdriver.Remote:
    options = UiAutomator2Options()
    options.platform_name = cfg["device"]["platform_name"]
    options.automation_name = cfg["device"]["automation_name"]
    options.device_name = cfg["device"]["device_name"]
    if cfg["device"].get("udid"):
        options.udid = cfg["device"]["udid"]

    app = cfg["app"]
    if Path(app["path"]).is_file():
        options.app = app["path"]  # install / reinstall the APK
    elif not app.get("package"):
        raise FileNotFoundError(
            f"APK not found: {app['path']}\n"
            "Put your APK in the apps/ folder or set app.package in config/config.yaml "
            "to test an app that is already installed."
        )
    if app.get("package"):
        options.app_package = app["package"]
    if app.get("activity"):
        options.app_activity = app["activity"]
    options.no_reset = app.get("no_reset", False)
    options.auto_grant_permissions = app.get("auto_grant_permissions", True)
    options.new_command_timeout = cfg["timeouts"]["new_command"]

    driver = webdriver.Remote(cfg["appium"]["server_url"], options=options)
    driver.implicitly_wait(cfg["timeouts"]["implicit"])
    return driver

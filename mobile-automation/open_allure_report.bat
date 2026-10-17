@echo off
REM Opens the Allure report for the last test run in your browser.
cd /d "%~dp0"
allure serve reports\allure-results

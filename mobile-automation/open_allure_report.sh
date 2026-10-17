#!/usr/bin/env bash
# Opens the Allure report for the last test run in your browser.
cd "$(dirname "$0")"
allure serve reports/allure-results

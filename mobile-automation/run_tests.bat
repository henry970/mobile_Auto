@echo off
REM Run the tests. Examples:
REM   run_tests -m smoke
REM   run_tests --app apps\myapp.apk --package com.my.app --activity .MainActivity
cd /d "%~dp0"
.venv\Scripts\python.exe -m pytest %*
echo.
echo Report: reports\report.html

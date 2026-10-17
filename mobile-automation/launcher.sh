#!/usr/bin/env bash
# Opens the Mobile Test Runner window.
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then .venv/bin/python launcher.py; else python3 launcher.py; fi

#!/usr/bin/env bash
# Run the tests. Any pytest options can be added, e.g.:
#   ./run_tests.sh -m smoke
#   ./run_tests.sh --app apps/myapp.apk --package com.my.app --activity .MainActivity
cd "$(dirname "$0")"
.venv/bin/python -m pytest "$@"
echo ""
echo "Report: reports/report.html"

#!/bin/bash
# scripts/check_vulnerabilities.sh
# Verifica vulnerabilidades em dependências Python e Node.js

EMAIL="kuramopr@gmail.com"
REPORT="/tmp/vuln_report.txt"
cd /home/felipe/MT5-Process-Core-full

# Python
if [ -f requirements.txt ]; then
    pip install --quiet safety
    safety check -r requirements.txt > "$REPORT"
fi
if [ -f requirements-ml.txt ]; then
    pip install --quiet safety
    safety check -r requirements-ml.txt >> "$REPORT"
fi

# Node.js
if [ -f package.json ]; then
    npm install --quiet
    npm audit --json >> "$REPORT"
fi

cat "$REPORT" | mailx -s "[MT5] Relatório de vulnerabilidades" "$EMAIL"

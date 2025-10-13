#!/usr/bin/env bash
set -euo pipefail
# Exemplo de ingest teste via CSV
python scripts/import_csv.py sample_m1.csv EURUSD M1

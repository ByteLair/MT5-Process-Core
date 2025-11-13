#!/usr/bin/env bash
# Freeze pip requirements for api and ml services into requirements.lock files
set -euo pipefail
pushd api >/dev/null
python -m pip freeze > requirements.lock || true
popd >/dev/null
pushd ml >/dev/null
python -m pip freeze > requirements.lock || true
popd >/dev/null
echo "Wrote requirements.lock in api/ and ml/ (if virtualenv python is accessible)."

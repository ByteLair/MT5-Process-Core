.PHONY: venv dev run seed lint train schedule

venv:
	python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r api/requirements.txt

dev:
	. .venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload

run:
	. .venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8001

seed:
	psql "$${DATABASE_URL}" -f db/init/01-init.sql && psql "$${DATABASE_URL}" -f db/init/02-ml.sql

lint:
	. .venv/bin/activate && python -m pip install ruff black && ruff check api && black --check api

train:
	. .venv/bin/activate && python ml/worker/train.py

schedule:
	. .venv/bin/activate && python ml/scheduler.py

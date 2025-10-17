.PHONY: venv dev run seed lint train schedule api-up api-logs db-sql-signals seed-signal

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

api-up:
	docker compose up -d --build api

api-logs:
	docker compose logs -f api

db-sql-signals:
	docker compose exec -T db psql -U trader -d mt5_trading -v ON_ERROR_STOP=1 -f db/init/20-signals.sql

seed-signal:
	docker compose exec db psql -U trader -d mt5_trading -c "INSERT INTO public.signals_queue (id,account_id,symbol,timeframe,side,confidence,sl_pips,tp_pips,ttl_sec,meta) VALUES ('sig_demo_1','$(ACCOUNT)','EURUSD','M1','BUY',0.85,10,15,90,'{\"model\":\"rf_m1\",\"ver\":\"1.0.0\"}') ON CONFLICT (id) DO NOTHING;"

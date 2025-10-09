.PHONY: up down logs api-logs db-logs build test ingest-one
up:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f
api-logs:
	docker compose logs -f api
db-logs:
	docker compose logs -f db
build:
	docker compose build
test:
	bash scripts/smoke_test_single.sh
ingest-one:
	bash scripts/smoke_test_single.sh

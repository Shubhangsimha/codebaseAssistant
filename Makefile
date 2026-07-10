.PHONY: dev build down test test-e2e lint

dev:
	docker-compose up

build:
	docker-compose build

down:
	docker-compose down

# Unit tests only (fast, no running server needed)
test:
	docker-compose run --rm api pytest tests/ --ignore=tests/e2e -v

# End-to-end smoke test (requires backend running at localhost:8000)
test-e2e:
	cd backend && pytest tests/e2e/ -v -s

lint:
	cd backend && python -m ruff check app/ && python -m mypy app/

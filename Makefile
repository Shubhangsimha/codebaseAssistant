.PHONY: dev build down test lint

dev:
	docker-compose up

build:
	docker-compose build

down:
	docker-compose down

test:
	docker-compose run --rm api pytest tests/ -v

lint:
	cd backend && python -m ruff check app/ && python -m mypy app/

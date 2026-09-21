PYTHON ?= server/.venv/bin/python
RUFF ?= server/.venv/bin/ruff
MYPY ?= server/.venv/bin/mypy

.PHONY: server-install web-install dev-server dev-web test typecheck lint build check
server-install:
	python3 -m venv server/.venv
	$(PYTHON) -m pip install -e 'server[dev]'
web-install:
	cd web && npm ci
dev-server:
	cd server && .venv/bin/python -m uvicorn spl_dashboard.main:app --reload --host 0.0.0.0 --port 8000
dev-web:
	cd web && npm run dev
test:
	$(PYTHON) -m pytest server/tests
	cd web && npm test -- --run
typecheck:
	$(MYPY) --config-file server/pyproject.toml server/src
	cd web && npm run typecheck
lint:
	$(RUFF) check server
build:
	cd web && npm run build
check: lint test typecheck build

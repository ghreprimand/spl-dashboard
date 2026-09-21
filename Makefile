PYTHON ?= server/.venv/bin/python
RUFF ?= server/.venv/bin/ruff
MYPY ?= server/.venv/bin/mypy
STATIC ?= server/src/spl_dashboard/static
DIST ?= dist

.PHONY: server-install web-install dev-server dev-web test typecheck lint build check \
        ui-bundle wheel screenshots
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

# Build the web UI and copy it into the Python package so the wheel is self-contained.
# --include=dev guards against environments that set NODE_ENV=production.
ui-bundle:
	cd web && npm ci --include=dev && npm run build
	rm -rf $(STATIC)
	cp -a web/dist $(STATIC)

# Produce dist/spl_dashboard-<version>-py3-none-any.whl with the UI bundled inside.
wheel: ui-bundle
	rm -f $(DIST)/spl_dashboard-*.whl
	uv build --wheel server --out-dir $(DIST)
	@ls -1 $(DIST)/spl_dashboard-*.whl

# Regenerate the documentation screenshots with a headless browser.
screenshots:
	cd web && npm run build
	node scripts/capture-screenshots.mjs

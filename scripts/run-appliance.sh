#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export SPL_WEB_DIST="${SPL_WEB_DIST:-$project_dir/web/dist}"
cd "$project_dir/server"
exec .venv/bin/python -m uvicorn spl_dashboard.main:app --host "${SPL_BIND:-0.0.0.0}" --port 8000 --workers 1

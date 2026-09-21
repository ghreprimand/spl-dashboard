# Releasing

SPL Dashboard is published to PyPI as `spl-dashboard`. Releases are built and
published by GitHub Actions using **PyPI Trusted Publishing** (OIDC) — there are
no API tokens or passwords stored anywhere.

## One-time setup: register the Trusted Publishers

Do this once per index, before the first release, in the project's settings on
each site (create the project as a "pending publisher" if it does not exist yet).

**On [PyPI](https://pypi.org/manage/account/publishing/):**

| Field | Value |
| --- | --- |
| PyPI project name | `spl-dashboard` |
| Owner | `ghreprimand` |
| Repository name | `spl-dashboard` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

Also create the GitHub Actions **environment** `pypi` in the repository settings
(`Settings → Environments`). You may add required reviewers to it to gate the
publish. TestPyPI is deliberately not used: `twine check` runs in the build job,
and PyPI versions are immutable, so bump the version rather than re-tagging.

## Cutting a release

1. **Bump the version** in `server/pyproject.toml` (`version = "X.Y.Z"`) and in
   `create_app`'s `FastAPI(..., version=...)` in `server/src/spl_dashboard/main.py`.
   Add a matching entry to [`CHANGELOG.md`](../CHANGELOG.md).
2. **Verify locally:** `make server-install` (refreshes the editable install's
   version metadata, which `--version` reads), then `make check`, then `make wheel` and a smoke test:
   `uvx --from dist/spl_dashboard-X.Y.Z-py3-none-any.whl spl-dashboard`.
3. **Commit** the version bump and changelog.
4. **Tag and push:**

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

## What the workflow does

On any `v*` tag, `.github/workflows/release.yml` runs three jobs:

1. **build** — builds the web UI, bundles it into the package (`make ui-bundle`),
   builds the sdist and wheel (`python -m build`), runs `twine check`, and uploads
   both as workflow artifacts named `distributions`.
2. **pypi** — downloads the artifacts and publishes them to **PyPI** via
   Trusted Publishing (environment `pypi`, OIDC, no stored token).
3. **github-release** — creates the GitHub Release for the tag, with the
   matching `CHANGELOG.md` section as notes and the wheel/sdist attached. Keep
   the changelog heading in the form `## 0.5.0 ...` or `## [0.5.0] ...` so it
   is found.

## Verify a published release

```bash
uvx spl-dashboard@X.Y.Z          # runs the exact version from PyPI
```

Open `http://localhost:8000/` and `http://localhost:8000/display` and confirm the
UI loads and telemetry streams.

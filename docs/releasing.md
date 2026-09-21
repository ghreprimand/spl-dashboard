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

**On [TestPyPI](https://test.pypi.org/manage/account/publishing/):** the same,
but with environment name `testpypi`.

Also create the two GitHub Actions **environments** in the repository settings
(`Settings → Environments`): `pypi` and `testpypi`. You may add required
reviewers to the `pypi` environment to gate the final publish.

## Cutting a release

1. **Bump the version** in `server/pyproject.toml` (`version = "X.Y.Z"`) and in
   `create_app`'s `FastAPI(..., version=...)` in `server/src/spl_dashboard/main.py`.
   Add a matching entry to [`CHANGELOG.md`](../CHANGELOG.md).
2. **Verify locally:** `make check`, then `make wheel` and a smoke test:
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
2. **testpypi** — downloads the artifacts and publishes them to **TestPyPI** via
   Trusted Publishing (environment `testpypi`). `skip-existing` lets a re-run pass
   if that version is already there.
3. **pypi** — after TestPyPI succeeds, publishes the same artifacts to **PyPI**
   via Trusted Publishing (environment `pypi`).

For the very first publish, watch the TestPyPI job succeed before approving/allowing
the PyPI job, and confirm the TestPyPI page renders the README correctly.

## Verify a published release

```bash
uvx spl-dashboard@X.Y.Z          # runs the exact version from PyPI
```

From TestPyPI (before the PyPI publish, for the first run):

```bash
uvx --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    spl-dashboard@X.Y.Z
```

Open `http://localhost:8000/` and `http://localhost:8000/display` and confirm the
UI loads and telemetry streams.

"""Address reporting and the spl-dashboard console entry point."""

from pathlib import Path

from fastapi.testclient import TestClient

from spl_dashboard import cli
from spl_dashboard.addresses import IPAD_NOTE, address_report, local_ipv4_addresses
from spl_dashboard.main import create_app


def test_local_addresses_exclude_loopback_and_link_local():
    for address in local_ipv4_addresses():
        assert not address.startswith("127.")
        assert not address.startswith("169.254.")


def test_address_report_builds_local_and_lan_urls():
    report = address_report(8000)
    assert report["localAdmin"] == "http://localhost:8000/"
    assert report["localDisplay"] == "http://localhost:8000/display"
    assert report["note"] == IPAD_NOTE
    for entry in report["lan"]:
        assert entry["display"] == f"http://{entry['host']}:8000/display"
        assert entry["admin"] == f"http://{entry['host']}:8000/"


def test_addresses_endpoint_uses_request_port(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        payload = client.get("/api/addresses", headers={"host": "example.local:8123"}).json()
        assert payload["port"] == 8123
        assert payload["localDisplay"] == "http://localhost:8123/display"
        health = client.get("/api/health", headers={"host": "example.local:8123"}).json()
        assert health["addresses"]["port"] == 8123


def test_cli_default_data_dir_is_per_user():
    directory = cli.default_data_dir()
    assert isinstance(directory, Path)
    assert directory.name == "spl-dashboard"


def test_cli_parses_host_port_data_dir(tmp_path):
    args = cli._parse_args(["--host", "127.0.0.1", "--port", "9000", "--data-dir", str(tmp_path)])
    assert args.host == "127.0.0.1"
    assert args.port == 9000
    assert args.data_dir == str(tmp_path)


def test_cli_main_sets_data_dir_env_and_starts_server(tmp_path, monkeypatch, capsys):
    captured: dict[str, object] = {}

    def fake_run(app: str, **kwargs: object) -> None:
        captured["app"] = app
        captured["kwargs"] = kwargs

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", fake_run)
    data_dir = tmp_path / "cli-data"
    cli.main(["--host", "127.0.0.1", "--port", "9001", "--data-dir", str(data_dir)])

    import os

    assert os.environ["SPL_DATA_DIR"] == str(data_dir)
    assert data_dir.is_dir()
    assert captured["app"] == "spl_dashboard.main:app"
    assert captured["kwargs"]["host"] == "127.0.0.1"
    assert captured["kwargs"]["port"] == 9001
    assert captured["kwargs"]["workers"] == 1
    banner = capsys.readouterr().out
    assert "http://localhost:9001/display" in banner
    assert "only view the dashboard" in banner


def test_cli_version(capsys):
    cli.main(["--version"])
    out = capsys.readouterr().out.strip()
    assert out == "0.5.0"


def test_missing_ui_reports_clear_error(tmp_path, monkeypatch):
    # Force the UI resolver to find nothing, then confirm a clear 500 is served.
    from spl_dashboard import main as main_module

    monkeypatch.setattr(main_module, "locate_web_dist", lambda: None)
    with TestClient(create_app(tmp_path)) as client:
        response = client.get("/")
        assert response.status_code == 500
        assert "web UI was not found" in response.json()["detail"]


def test_bundled_ui_is_served_when_present(tmp_path):
    # In a normal dev/test tree the package static or web/dist is available.
    if cli_ui_available():
        with TestClient(create_app(tmp_path)) as client:
            assert client.get("/").status_code == 200


def cli_ui_available() -> bool:
    from spl_dashboard.main import locate_web_dist

    return locate_web_dist() is not None

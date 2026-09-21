import time

import pytest
from fastapi.testclient import TestClient

from spl_dashboard.main import create_app

HEADERS = {"X-SPL-Client": "dashboard"}


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as connection:
        yield connection


def test_service_runs_with_zero_clients_and_shared_telemetry(client):
    initial = client.get("/api/telemetry").json()
    time.sleep(0.4)
    after = client.get("/api/telemetry").json()
    assert after["sequence"] > initial["sequence"]
    assert after["diagnostics"]["framesProcessed"] > 0
    assert after["source"] == "demo"
    assert after["status"]["calibrated"] is False
    with client.websocket_connect("/ws/telemetry") as one:
        with client.websocket_connect("/ws/telemetry") as two:
            a, b = one.receive_json(), two.receive_json()
            assert abs(a["sequence"] - b["sequence"]) <= 1
            assert a["schemaVersion"] == 2
    assert client.get("/api/health").json()["hardwareValidated"] is False


def test_event_lifecycle_logs_without_browser_and_exports(client):
    started = client.post("/api/events", json={"name": "Test event"}, headers=HEADERS)
    assert started.status_code == 200
    identity = started.json()["id"]
    time.sleep(1.2)
    assert client.post("/api/events", json={"name": "Second"}, headers=HEADERS).status_code == 400
    settings = client.get("/api/config").json()
    assert client.put("/api/config", json=settings, headers=HEADERS).status_code == 400
    assert (
        client.post(
            "/api/events/current/annotations", json={"text": "Soundcheck"}, headers=HEADERS
        ).status_code
        == 200
    )
    assert client.post("/api/events/current/reset-peak", headers=HEADERS).status_code == 200
    history = client.get(f"/api/events/{identity}/history").json()
    assert history
    assert all(f["eventId"] == identity for f in history)
    assert client.post("/api/events/current/stop", headers=HEADERS).status_code == 200
    assert client.get("/api/events/current").json() is None
    csv = client.get(f"/api/events/{identity}/export.csv")
    assert csv.status_code == 200
    assert "measured_LAS_dB" in csv.text
    assert "estimated_LAS_dB" in csv.text
    summary = client.get(f"/api/events/{identity}/summary.json").json()
    assert summary["records"] >= 1
    assert summary["annotations"][0]["text"] == "Soundcheck"
    assert summary["config"]["mode"] == "demo"


def test_settings_validation_origin_and_wav_confinement(client):
    config = client.get("/api/config").json()
    assert client.put("/api/config", json=config).status_code == 403
    assert (
        client.put(
            "/api/config", json=config, headers={**HEADERS, "Origin": "http://evil.test"}
        ).status_code
        == 403
    )
    assert (
        client.put("/api/config", json={**config, "sampleRate": 44100}, headers=HEADERS).status_code
        == 422
    )
    assert (
        client.put("/api/config", json={**config, "referenceDb": 94}, headers=HEADERS).status_code
        == 422
    )
    assert (
        client.put(
            "/api/config", json={**config, "calibrationText": "broken"}, headers=HEADERS
        ).status_code
        == 400
    )
    assert (
        client.put(
            "/api/config",
            json={**config, "mode": "wav", "wavPath": "../outside.wav"},
            headers=HEADERS,
        ).status_code
        == 400
    )
    assert client.get("/api/config").json() == config


def test_restart_preserves_event_and_marks_gap(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        identity = client.post("/api/events", json={"name": "Recovery"}, headers=HEADERS).json()[
            "id"
        ]
        time.sleep(1.2)
    with TestClient(create_app(tmp_path)) as client:
        current = client.get("/api/events/current").json()
        assert current["id"] == identity
        assert "Service restarted" in current["annotations"][-1]["text"]
        time.sleep(0.25)
        frame = client.get("/api/telemetry").json()
        assert frame["status"]["gapCount"] >= 1
        assert frame["status"]["warmupSeconds"] > 590
        assert frame["measured"]["lcpeakDb"] is not None


def test_reading_location_shared_persistent_and_does_not_restart_input(tmp_path):
    import json

    app = create_app(tmp_path)
    with TestClient(app) as client:
        assert (
            client.put(
                "/api/reading-location", json={"audience": True}, headers=HEADERS
            ).status_code
            == 400
        )
        settings = client.get("/api/config").json()
        settings.update(
            venueName="Hall",
            audienceOffsetDb=3.6,
            audienceMappingNote=json.dumps({"date": "2026-09-21T06:00:00Z"}),
        )
        # Existing saved maps without an explicit display choice migrate to audience mode.
        assert client.put("/api/config", json=settings, headers=HEADERS).status_code == 200
        with client.websocket_connect("/ws/telemetry") as one:
            with client.websocket_connect("/ws/telemetry") as two:
                a, b = one.receive_json(), two.receive_json()
                assert (
                    a["readingLocation"]
                    == b["readingLocation"]
                    == {
                        "mappingId": a["readingLocation"]["mappingId"],
                        "audience": True,
                        "name": "Hall",
                        "offsetDb": 3.6,
                        "mappedAt": "2026-09-21T06:00:00Z",
                    }
                )
        client.post("/api/events", json={"name": "Show"}, headers=HEADERS)
        time.sleep(0.3)
        before = client.get("/api/telemetry").json()
        assert client.put("/api/reading-location", json={"audience": False}).status_code == 403
        assert (
            client.put(
                "/api/reading-location", json={"audience": False}, headers=HEADERS
            ).status_code
            == 200
        )
        after = client.get("/api/telemetry").json()
        assert after["readingLocation"]["audience"] is False
        assert after["spectrum"]["analysisId"] == before["spectrum"]["analysisId"]
        assert after["eventId"] == before["eventId"]
        assert after["status"]["gapCount"] == before["status"]["gapCount"]
        assert (
            client.get("/api/config").json()["audienceMappingNote"]
            == settings["audienceMappingNote"]
        )
        assert after["estimatedAudience"]["lasDb"] - after["measured"]["lasDb"] == pytest.approx(
            3.6
        )
    with TestClient(create_app(tmp_path)) as client:
        saved = client.get("/api/telemetry").json()["readingLocation"]
        assert saved["audience"] is False
        assert saved["name"] == "Hall"
        assert saved["mappedAt"] == "2026-09-21T06:00:00Z"


def test_mapping_library_retains_versions_activates_and_deletes(tmp_path):
    import json

    with TestClient(create_app(tmp_path)) as client:
        original = client.get("/api/config").json()
        first = {
            **original,
            "venueName": "Home",
            "audienceOffsetDb": 3.6,
            "audienceMappingNote": json.dumps({"date": "2026-09-21T06:00:00Z"}),
        }
        second = {
            **first,
            "audienceOffsetDb": -2,
            "audienceMappingNote": json.dumps({"date": "2026-09-22T06:00:00Z"}),
        }
        assert client.put("/api/config", json=first, headers=HEADERS).status_code == 200
        first_id = client.get("/api/telemetry").json()["readingLocation"]["mappingId"]
        client.put("/api/config", json=second, headers=HEADERS)
        second_id = client.get("/api/telemetry").json()["readingLocation"]["mappingId"]
        assert first_id != second_id
        assert len(client.get("/api/audience-mappings").json()) == 2
        assert (
            client.delete(f"/api/audience-mappings/{second_id}", headers=HEADERS).status_code == 400
        )
        client.post("/api/events", json={"name": "Keep raw records"}, headers=HEADERS)
        assert (
            client.post(f"/api/audience-mappings/{first_id}/activate", headers=HEADERS).status_code
            == 400
        )
        client.post("/api/events/current/stop", headers=HEADERS)
        result = client.post(f"/api/audience-mappings/{first_id}/activate", headers=HEADERS)
        assert result.status_code == 200
        assert result.json()["mappingId"] == first_id
        assert result.json()["audience"] is True
        config = client.get("/api/config").json()
        assert config["audienceMappingNote"] == first["audienceMappingNote"]
        assert config["audienceOffsetDb"] == first["audienceOffsetDb"]
        assert config["device"] == original["device"]
        assert len(client.get("/api/audience-mappings").json()) == 2
        assert client.delete(f"/api/audience-mappings/{second_id}").status_code == 403
        assert (
            client.delete(f"/api/audience-mappings/{second_id}", headers=HEADERS).status_code == 200
        )
        assert len(client.get("/api/events").json()) == 1
        assert (
            client.post("/api/audience-mappings/unknown/activate", headers=HEADERS).status_code
            == 400
        )
    with TestClient(create_app(tmp_path)) as client:
        items = client.get("/api/audience-mappings").json()
        assert len(items) == 1
        assert items[0]["id"] == first_id
        assert client.get("/api/telemetry").json()["readingLocation"]["mappingId"] == first_id


def test_existing_mapping_migrates_to_library(tmp_path):
    import json
    import sqlite3

    from spl_dashboard.models import Settings
    from spl_dashboard.storage import Store

    path = tmp_path / "events.sqlite3"
    settings = Settings(venueName="Existing", audienceOffsetDb=2)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE config (id INTEGER PRIMARY KEY, body TEXT)")
        db.execute("INSERT INTO config VALUES (1, ?)", (json.dumps(settings.model_dump()),))
    store = Store(path)
    assert store.mappings()[0]["name"] == "Existing"
    assert store.mappings()[0]["mappedAt"] is None
    store.save_settings(settings)
    assert len(store.mappings()) == 1
    store.close()


def test_clear_mapping_preserves_library_and_events_then_allows_delete(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        config = client.get("/api/config").json()
        config.update(venueName="Home", audienceOffsetDb=3.6, audienceDisplay=True)
        client.put("/api/config", json=config, headers=HEADERS)
        identity = client.get("/api/telemetry").json()["readingLocation"]["mappingId"]
        event = client.post("/api/events", json={"name": "History"}, headers=HEADERS).json()
        assert client.post("/api/audience-mapping/clear", headers=HEADERS).status_code == 400
        assert client.get("/api/telemetry").json()["readingLocation"]["mappingId"] == identity
        client.post("/api/events/current/stop", headers=HEADERS)
        assert client.post("/api/audience-mapping/clear").status_code == 403
        result = client.post("/api/audience-mapping/clear", headers=HEADERS)
        assert result.status_code == 200
        assert result.json() == {
            "mappingId": None,
            "audience": False,
            "name": "",
            "offsetDb": None,
            "mappedAt": None,
        }
        assert client.get("/api/audience-mappings").json()[0]["id"] == identity
        saved = client.get("/api/config").json()
        for key in ("device", "calibrationText", "fieldTrimDb", "lasThreshold"):
            assert saved[key] == config[key]
        assert saved["audienceOffsetDb"] is None
        assert saved["audienceMappingNote"] == ""
        with client.websocket_connect("/ws/telemetry") as one:
            with client.websocket_connect("/ws/telemetry") as two:
                assert (
                    one.receive_json()["readingLocation"]
                    == two.receive_json()["readingLocation"]
                    == result.json()
                )
        history = client.get(f"/api/events/{event['id']}/summary.json").json()
        assert history["config"]["venueName"] == "Home"
        assert history["config"]["audienceOffsetDb"] == 3.6
        assert (
            client.delete(f"/api/audience-mappings/{identity}", headers=HEADERS).status_code == 200
        )
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/api/audience-mappings").json() == []
        assert client.get("/api/telemetry").json()["readingLocation"]["mappingId"] is None

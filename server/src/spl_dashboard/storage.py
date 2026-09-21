"""Durable telemetry only; never stores audio."""

import hashlib
import json
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import Settings, TelemetryFrame


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def mapping_id(settings: Settings) -> str | None:
    if settings.audienceOffsetDb is None:
        return None
    payload = [settings.venueName, settings.audienceOffsetDb, settings.audienceMappingNote]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=FULL;
            CREATE TABLE IF NOT EXISTS audience_mappings (
                id TEXT PRIMARY KEY, created TEXT NOT NULL, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT);
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY, name TEXT, started TEXT, stopped TEXT, config TEXT);
            CREATE UNIQUE INDEX IF NOT EXISTS one_active ON events((1)) WHERE stopped IS NULL;
            CREATE TABLE IF NOT EXISTS frames (
                id INTEGER PRIMARY KEY, event_id TEXT, timestamp TEXT, body TEXT);
            CREATE INDEX IF NOT EXISTS frames_event ON frames(event_id, id);
            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY, event_id TEXT, timestamp TEXT, text TEXT);
        """)

        # Preserve the existing active profile on first upgrade, idempotently.
        with self.db:
            self._archive_mapping(self.settings())

    def _archive_mapping(self, settings: Settings) -> None:
        identity = mapping_id(settings)
        if identity is None:
            return
        body = {
            "venueName": settings.venueName,
            "audienceOffsetDb": settings.audienceOffsetDb,
            "audienceMappingNote": settings.audienceMappingNote,
        }
        self.db.execute(
            "INSERT OR IGNORE INTO audience_mappings VALUES (?,?,?)",
            (identity, utcnow(), json.dumps(body)),
        )

    def mapping(self, identity: str) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT body FROM audience_mappings WHERE id=?", (identity,)
        ).fetchone()
        if row is None:
            raise ValueError("Saved audience mapping not found")
        return json.loads(row["body"])

    def delete_mapping(self, identity: str) -> None:
        if identity == mapping_id(self.settings()):
            raise ValueError("Clear the loaded mapping before deleting it")
        with self.db:
            cursor = self.db.execute("DELETE FROM audience_mappings WHERE id=?", (identity,))
            if cursor.rowcount == 0:
                raise ValueError("Saved audience mapping not found")

    def mappings(self) -> list[dict[str, Any]]:
        result = []
        for row in self.db.execute("SELECT * FROM audience_mappings ORDER BY created DESC"):
            body = json.loads(row["body"])
            mapped_at = None
            try:
                note = json.loads(body["audienceMappingNote"])
                if isinstance(note, dict) and isinstance(note.get("date"), str):
                    mapped_at = note["date"]
            except (ValueError, TypeError):
                pass
            result.append(
                {
                    "id": row["id"],
                    "name": body["venueName"],
                    "offsetDb": body["audienceOffsetDb"],
                    "mappedAt": mapped_at,
                }
            )
        return result

    def settings(self) -> Settings:
        row = self.db.execute("SELECT body FROM config WHERE id=1").fetchone()
        return Settings.model_validate_json(row["body"]) if row else Settings()

    def save_settings(self, settings: Settings) -> None:
        with self.db:
            self._archive_mapping(self.settings())
            self._archive_mapping(settings)
            self.db.execute(
                "INSERT OR REPLACE INTO config VALUES (1, ?)", (settings.model_dump_json(),)
            )

    def current(self) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM events WHERE stopped IS NULL").fetchone()
        return dict(row) if row else None

    def events(self) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self.db.execute(
                "SELECT id,name,started,stopped FROM events ORDER BY started DESC LIMIT 200"
            )
        ]

    def start(self, name: str, settings: Settings) -> dict[str, Any]:
        if self.current():
            raise ValueError("An event is already running")
        identity = str(uuid.uuid4())
        with self.db:
            self.db.execute(
                "INSERT INTO events VALUES (?,?,?,NULL,?)",
                (identity, name.strip(), utcnow(), settings.model_dump_json()),
            )
        return self.current() or {}

    def stop(self) -> None:
        with self.db:
            self.db.execute("UPDATE events SET stopped=? WHERE stopped IS NULL", (utcnow(),))

    def annotate(self, text: str) -> None:
        event = self.current()
        if not event:
            raise ValueError("No active event")
        with self.db:
            self.db.execute(
                "INSERT INTO annotations(event_id,timestamp,text) VALUES (?,?,?)",
                (event["id"], utcnow(), text),
            )

    def append(self, frame: TelemetryFrame) -> None:
        if frame.eventId:
            with self.db:
                self.db.execute(
                    "INSERT INTO frames(event_id,timestamp,body) VALUES (?,?,?)",
                    (frame.eventId, frame.timestamp, frame.model_dump_json()),
                )

    def history(self, event_id: str, limit: int = 600) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT body FROM frames WHERE event_id=? ORDER BY id DESC LIMIT ?", (event_id, limit)
        ).fetchall()
        return [json.loads(row["body"]) for row in reversed(rows)]

    def chart_history(self, event_id: str) -> list[dict[str, Any]]:
        # A separate read-only connection lets history run outside capture's event loop.
        with closing(
            sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)
        ) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT timestamp, json_extract(body, '$.measured') AS measured, "
                "json_extract(body, '$.status') AS status FROM frames "
                "WHERE event_id=? ORDER BY id DESC LIMIT 600",
                (event_id,),
            ).fetchall()
            return [
                {
                    "timestamp": row["timestamp"],
                    "eventId": event_id,
                    "measured": json.loads(row["measured"]) if row["measured"] else None,
                    "status": json.loads(row["status"]),
                }
                for row in reversed(rows)
            ]

    def detail(self, event_id: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["config"] = json.loads(result["config"])
        result["annotations"] = [
            dict(r)
            for r in self.db.execute(
                "SELECT timestamp,text FROM annotations WHERE event_id=? ORDER BY id", (event_id,)
            )
        ]
        result["records"] = self.db.execute(
            "SELECT count(*) FROM frames WHERE event_id=?", (event_id,)
        ).fetchone()[0]
        return result

    def close(self) -> None:
        self.db.close()

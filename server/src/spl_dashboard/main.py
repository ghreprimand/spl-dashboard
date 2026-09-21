import asyncio
import csv
import fcntl
import io
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .addresses import address_report
from .capture import devices
from .models import AnnotationRequest, EventRequest, ReadingLocationRequest, Settings
from .runtime import Runtime


def _default_data_dir() -> Path:
    override = os.environ.get("SPL_DATA_DIR")
    if override:
        return Path(override)
    from platformdirs import user_data_dir

    return Path(user_data_dir("spl-dashboard", appauthor=False))


def create_app(directory: Path | None = None) -> FastAPI:
    data_dir = directory or _default_data_dir()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        data_dir.mkdir(parents=True, exist_ok=True)
        with (data_dir / "service.lock").open("w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError(
                    "One service worker only: this data directory is in use"
                ) from exc
            runtime = Runtime(data_dir)
            app.state.runtime = runtime
            await runtime.start()
            try:
                yield
            finally:
                await runtime.close()

    app = FastAPI(title="SPL Dashboard", version="0.5.0", lifespan=lifespan)

    @app.middleware("http")
    async def local_mutations(request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.headers.get("x-spl-client") != "dashboard":
                return JSONResponse(
                    {"detail": "Missing X-SPL-Client: dashboard header"}, status_code=403
                )
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.headers.get("host"):
                return JSONResponse(
                    {"detail": "Cross-origin changes are not allowed"}, status_code=403
                )
            length = request.headers.get("content-length")
            if length and int(length) > 300000:
                return JSONResponse({"detail": "Request too large"}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(ValueError)
    async def invalid_request(request: Request, exc: ValueError):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    def runtime() -> Runtime:
        return app.state.runtime

    def request_port(request: Request) -> int:
        host_header = request.headers.get("host", "")
        _, _, port_text = host_header.partition(":")
        if port_text.isdigit():
            return int(port_text)
        return request.url.port or (443 if request.url.scheme == "https" else 80)

    @app.get("/api/health")
    async def health(request: Request):
        frame = runtime().frame
        return {
            "status": "degraded" if frame.status.stale or frame.status.loggingError else "ok",
            "mode": runtime().settings.mode,
            "schemaVersion": 2,
            "hardwareValidated": False,
            "input": frame.status.model_dump(),
            "addresses": address_report(request_port(request)),
        }

    @app.get("/api/addresses")
    async def addresses(request: Request):
        return address_report(request_port(request))

    @app.get("/api/config")
    async def config():
        return runtime().settings

    @app.put("/api/config")
    async def configure(settings: Settings):
        await runtime().configure(settings)
        return runtime().settings

    @app.put("/api/reading-location")
    async def reading_location(request: ReadingLocationRequest):
        await runtime().set_reading_location(request.audience)
        return runtime().frame.readingLocation

    @app.post("/api/audience-mapping/clear")
    async def clear_mapping():
        await runtime().configure(None, clear_mapping=True)
        return runtime().frame.readingLocation

    @app.get("/api/audience-mappings")
    async def audience_mappings():
        return runtime().store.mappings()

    @app.post("/api/audience-mappings/{identity}/activate")
    async def activate_mapping(identity: str):
        await runtime().configure(None, mapping=identity)
        return runtime().frame.readingLocation

    @app.delete("/api/audience-mappings/{identity}")
    async def delete_mapping(identity: str):
        async with runtime().config_lock:
            runtime().store.delete_mapping(identity)
        return {"deleted": identity}

    @app.get("/api/devices")
    async def inputs():
        try:
            return {"devices": await asyncio.to_thread(devices), "error": None}
        except Exception as exc:
            return {"devices": [], "error": str(exc)}

    @app.get("/api/telemetry")
    async def snapshot():
        return runtime().frame

    @app.websocket("/ws/telemetry")
    async def telemetry(websocket: WebSocket):
        origin = websocket.headers.get("origin")
        if origin and urlsplit(origin).netloc != websocket.headers.get("host"):
            await websocket.close(code=1008)
            return
        await websocket.accept()
        try:
            loop = asyncio.get_running_loop()
            deadline = loop.time()
            while True:
                await asyncio.wait_for(
                    websocket.send_text(runtime().frame.model_dump_json()), timeout=2
                )
                deadline = max(deadline + 0.1, loop.time())
                await asyncio.sleep(max(0, deadline - loop.time()))
        except (TimeoutError, WebSocketDisconnect, RuntimeError):
            return

    @app.get("/api/events")
    async def events():
        return runtime().store.events()

    @app.get("/api/events/current")
    async def current():
        event = runtime().store.current()
        return runtime().store.detail(event["id"]) if event else None

    @app.post("/api/events")
    async def start(body: EventRequest):
        if not body.name.strip():
            raise ValueError("Event name cannot be blank")
        async with runtime().config_lock:
            return runtime().start_event(body.name)

    @app.post("/api/events/current/stop")
    async def stop():
        rt = runtime()
        rt.store.append(rt.frame)
        rt.store.stop()
        rt.frame.eventId = None
        rt.frame.peakHold = "since last event/reset"
        return {"stopped": True}

    @app.post("/api/audience-mapping/capture")
    async def capture_mapping():
        return await runtime().capture_mapping_level()

    @app.post("/api/reference/capture")
    async def capture_reference():
        return await runtime().capture_reference_rms()

    @app.post("/api/events/current/reset-maximum")
    async def reset_maximum():
        runtime().reset_maximum()
        return {"reset": True}

    @app.post("/api/events/current/reset-peak")
    async def reset():
        runtime().reset_peak()
        return {"reset": True}

    @app.post("/api/events/current/annotations")
    async def annotate(body: AnnotationRequest):
        if not body.text.strip():
            raise ValueError("Annotation cannot be blank")
        runtime().store.annotate(body.text.strip())
        return {"saved": True}

    @app.get("/api/events/{event_id}/history")
    async def history(event_id: str):
        return JSONResponse(await asyncio.to_thread(runtime().store.chart_history, event_id))

    @app.get("/api/events/{event_id}/summary.json")
    async def summary(event_id: str):
        detail = runtime().store.detail(event_id)
        if not detail:
            raise HTTPException(404, "Event not found")
        return JSONResponse(
            detail, headers={"Content-Disposition": f'attachment; filename="event-{event_id}.json"'}
        )

    @app.get("/api/events/{event_id}/export.csv")
    async def export(event_id: str):
        if not runtime().store.detail(event_id):
            raise HTTPException(404, "Event not found")

        async def rows():
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(
                [
                    "timestamp",
                    "source",
                    "measured_LAS_dB",
                    "measured_LAeq1_dB",
                    "measured_LAeq10_dB",
                    "measured_LCpeak_dB",
                    "measured_LASmax_dB",
                    "estimated_LAS_dB",
                    "estimated_LAeq1_dB",
                    "estimated_LAeq10_dB",
                    "rms_dBFS",
                    "peak_dBFS",
                    "connected",
                    "stale",
                    "clipping",
                    "reference_set",
                    "validation_pending",
                    "gap_count",
                    "overruns",
                    "warmup_seconds",
                    "calibration_hash",
                    "calibration_method",
                    "calibration_model",
                    "applied_offset_dB",
                    "analog_gain_dB",
                    "digital_gain_dB",
                    "device_binding",
                    "alarms",
                ]
            )
            yield buffer.getvalue()
            cursor = runtime().store.db.execute(
                "SELECT body FROM frames WHERE event_id=? ORDER BY id", (event_id,)
            )
            while batch := cursor.fetchmany(100):
                buffer.seek(0)
                buffer.truncate(0)
                for row in batch:
                    frame = json.loads(row["body"])
                    measured = frame["measured"] or {}
                    estimated = frame["estimatedAudience"] or {}
                    status = frame["status"]
                    diag = frame["diagnostics"]
                    writer.writerow(
                        [
                            frame["timestamp"],
                            frame["source"],
                            *[
                                measured.get(k)
                                for k in ("lasDb", "laeq1Db", "laeq10Db", "lcpeakDb", "lasMaxDb")
                            ],
                            *[estimated.get(k) for k in ("lasDb", "laeq1Db", "laeq10Db")],
                            diag["rmsDbfs"],
                            diag["peakDbfs"],
                            *[
                                status[k]
                                for k in (
                                    "connected",
                                    "stale",
                                    "clipping",
                                    "calibrated",
                                    "validationPending",
                                    "gapCount",
                                    "overruns",
                                    "warmupSeconds",
                                )
                            ],
                            diag["calibrationHash"],
                            *[
                                diag.get(k)
                                for k in (
                                    "calibrationMethod",
                                    "calibrationModel",
                                    "referenceOffsetDb",
                                    "analogGainDb",
                                    "digitalGainDb",
                                    "deviceBinding",
                                )
                            ],
                            "; ".join(frame["alarms"]),
                        ]
                    )
                yield buffer.getvalue()
                await asyncio.sleep(0)

        return StreamingResponse(
            rows(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="event-{event_id}.csv"'},
        )

    dist = locate_web_dist()
    if dist is not None:
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        @app.get("/display")
        async def index():
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

        @app.get("/manifest.webmanifest")
        async def manifest():
            return FileResponse(dist / "manifest.webmanifest")

        @app.get("/icon.svg")
        async def icon():
            return FileResponse(dist / "icon.svg")
    else:
        message = (
            "The web UI was not found. This installation is missing its bundled "
            "interface. Reinstall SPL Dashboard from a published wheel, or, when "
            "developing from a source checkout, build it with `npm --prefix web ci && "
            "npm --prefix web run build` and either run `make ui-bundle` or set "
            "SPL_WEB_DIST to the built web/dist directory."
        )

        @app.get("/")
        @app.get("/display")
        async def missing_ui():
            return JSONResponse({"detail": message}, status_code=500)

    return app


def locate_web_dist() -> Path | None:
    """Resolve the built web UI.

    Order: the UI bundled inside the installed package, then the SPL_WEB_DIST
    developer override, then a source-checkout ``web/dist``. Returns ``None`` when
    no built UI is available so the caller can serve a clear error instead.
    """
    candidates = [Path(__file__).resolve().parent / "static"]
    override = os.environ.get("SPL_WEB_DIST")
    if override:
        candidates.append(Path(override))
    candidates.append(Path(__file__).resolve().parents[3] / "web/dist")
    for candidate in candidates:
        if (candidate / "index.html").is_file() and (candidate / "assets").is_dir():
            return candidate
    return None


app = create_app()

import { AudienceMapping } from "./AudienceMapping";
import { FirstRunBanner } from "./FirstRunBanner";
import { SpectrumAnalyzer } from "./SpectrumAnalyzer";
import { DISCLAIMER } from "./disclaimer";
import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
} from "react";
import { api } from "./api";
import { defaultLayout, loadLayout, type Layout } from "./layout";
import { useTelemetry } from "./useTelemetry";
import type {
  Device,
  EventInfo,
  Levels,
  Settings,
  SavedMapping,
  TelemetryFrame,
} from "./types";

const metrics: { key: keyof Levels; label: string; detail: string }[] = [
  { key: "lasDb", label: "Live level", detail: "LAS · A · slow" },
  {
    key: "lasMaxDb",
    label: "Max live level",
    detail: "A · slow · since reset",
  },
  {
    key: "laeq1Db",
    label: "1-minute average",
    detail: "LAeq1 · A · 60 seconds",
  },
  {
    key: "laeq10Db",
    label: "10-minute average",
    detail: "LAeq10 · A · 10 minutes",
  },
  {
    key: "lcpeakDb",
    label: "Peak since reset",
    detail: "LCpeak · C · held peak",
  },
];
const format = (n: number | null | undefined, digits = 1) =>
  n == null ? "—" : n.toFixed(digits);
const remaining = (seconds: number) => {
  const whole = Math.ceil(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
};

export function statusMessages(
  frame: TelemetryFrame | null,
  connection: string,
): string[] {
  const messages: string[] = [];
  if (connection !== "live")
    messages.push(
      connection === "connecting" ? "CONNECTING" : "STALE · LINK LOST",
    );
  if (!frame) return messages;
  if (!frame.status.connected)
    messages.push(
      frame.source === "umik-unverified" ? "MIC LOST" : "INPUT STOPPED",
    );
  if (frame.status.stale) messages.push("STALE INPUT");
  if (frame.status.clipping) messages.push("CLIPPING");
  if (frame.status.loggingError) messages.push("LOG FAILURE");
  if (frame.source === "demo") messages.push("DEMO");
  else if (frame.source === "wav-unverified") messages.push("WAV REPLAY");
  if (!frame.status.calibrated && frame.source !== "demo")
    messages.push("UNCALIBRATED");
  if (frame.status.calibrated) {
    const method = frame.diagnostics.calibrationMethod;
    messages.push(
      method === "umik-file"
        ? "FILE CAL"
        : method === "manual"
          ? "MANUAL CAL"
          : "REFERENCE CAL",
    );
  } else if (frame.status.validationPending && frame.source !== "demo") {
    messages.push("UNVERIFIED");
  }
  if (frame.status.gapCount) messages.push(`GAPS ${frame.status.gapCount}`);
  messages.push(...frame.alarms);
  return messages;
}

function History({ frames }: { frames: TelemetryFrame[] }) {
  const valid = frames.filter(
    (f) => f.measured?.lasDb != null && !f.status.stale,
  );
  if (valid.length < 2)
    return (
      <p className="muted">
        History appears while an event is logging. Uncalibrated input remains in
        the exported diagnostics.
      </p>
    );
  const values = valid.map((f) => f.measured!.lasDb!);
  const low = Math.floor(Math.min(...values) / 10) * 10 - 5;
  const high = Math.ceil(Math.max(...values) / 10) * 10 + 5;
  const paths: string[] = [];
  let path = "";
  frames.forEach((f, i) => {
    const level = f.measured?.lasDb;
    if (level == null || f.status.stale || !f.status.connected) {
      if (path) paths.push(path);
      path = "";
    } else {
      if (
        i > 0 &&
        f.status.gapCount !== frames[i - 1].status.gapCount &&
        path
      ) {
        paths.push(path);
        path = "";
      }
      path += `${path ? " L" : "M"}${(i / Math.max(1, frames.length - 1)) * 1000},${110 - ((level - low) / (high - low)) * 100}`;
    }
  });
  if (path) paths.push(path);
  return (
    <div className="history">
      <div className="section-line">
        <span>Fixed mic · LAS · last {frames.length} records</span>
        <span>
          {low}–{high} dB
        </span>
      </div>
      <svg
        viewBox="0 0 1000 120"
        preserveAspectRatio="none"
        role="img"
        aria-label="LAS history; missing input leaves gaps"
      >
        {[30, 60, 90].map((y) => (
          <line key={y} x1="0" x2="1000" y1={y} y2={y} stroke="#263735" />
        ))}
        {paths.map((d, i) => (
          <path
            key={i}
            d={d}
            fill="none"
            stroke="var(--accent)"
            strokeWidth="2"
          />
        ))}
      </svg>
    </div>
  );
}

function LayoutControls({
  layout,
  setLayout,
}: {
  layout: Layout;
  setLayout: (v: Layout) => void;
}) {
  const ranges: {
    key: keyof Layout;
    label: string;
    min: number;
    max: number;
    unit: string;
  }[] = [
    { key: "width", label: "Width", min: 320, max: 2000, unit: "px" },
    { key: "height", label: "Height", min: 64, max: 200, unit: "px" },
    { key: "fontSize", label: "Digits", min: 20, max: 64, unit: "px" },
    { key: "x", label: "Horizontal position", min: 0, max: 100, unit: "%" },
    { key: "y", label: "Vertical position", min: 0, max: 100, unit: "%" },
    { key: "gap", label: "Spacing", min: 2, max: 24, unit: "px" },
  ];
  return (
    <section className="card">
      <div className="section-line">
        <h2>Your display</h2>
        <span className="tag">SAVED ON THIS DEVICE</span>
      </div>
      <p className="muted">
        Fit the strip inside your browser window. Use iPadOS window controls to
        place the browser beside Mixing Station.
      </p>
      <div className="layout-grid">
        {ranges.map((r) => (
          <label key={r.key}>
            {r.label}
            <span className="range-value">
              {layout[r.key]} {r.unit}
            </span>
            <input
              type="range"
              min={r.min}
              max={r.max}
              value={layout[r.key] as number}
              onChange={(e) =>
                setLayout({ ...layout, [r.key]: Number(e.target.value) })
              }
            />
          </label>
        ))}
      </div>
      <div className="actions">
        <label className="check">
          <input
            type="checkbox"
            checked={layout.spectrum}
            onChange={(e) =>
              setLayout({ ...layout, spectrum: e.target.checked })
            }
          />
          Spectrum
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={layout.details}
            onChange={(e) =>
              setLayout({ ...layout, details: e.target.checked })
            }
          />
          Metric descriptions
        </label>
        <button
          onClick={() =>
            setLayout({
              ...defaultLayout,
              height: 72,
              fontSize: 28,
              gap: 4,
              details: false,
            })
          }
        >
          Compact preset
        </button>
        <button onClick={() => setLayout(defaultLayout)}>Reset layout</button>
        <a className="button primary" href="/display">
          Open strip display ↗
        </a>
      </div>
    </section>
  );
}

function Setup({
  settings,
  devices,
  deviceError,
  busy,
  save,
}: {
  settings: Settings;
  devices: Device[];
  deviceError: string | null;
  busy: boolean;
  save: (settings: Settings) => Promise<void>;
}) {
  const [draft, setDraft] = useState(settings);
  const [fileError, setFileError] = useState("");
  const [capturing, setCapturing] = useState(false);
  const [captureNote, setCaptureNote] = useState("");
  const captureReference = async () => {
    setCapturing(true);
    setCaptureNote("");
    try {
      const result = await api<{ rmsDbfs: number; seconds: number }>(
        "/reference/capture",
        "POST",
      );
      setDraft((current) => ({ ...current, referenceRmsDbfs: result.rmsDbfs }));
      setCaptureNote(
        `Captured ${result.rmsDbfs.toFixed(1)} dBFS over ${result.seconds}s. Enter the known SPL and a note, then apply.`,
      );
    } catch (e) {
      setCaptureNote(e instanceof Error ? e.message : String(e));
    } finally {
      setCapturing(false);
    }
  };
  const fileSerial =
    draft.calibrationText.match(/SERNO\s*:\s*([\w-]+)/i)?.[1] ?? "";
  const selectedDevice = devices.find((d) => d.id === draft.device);
  useEffect(() => setDraft(settings), [settings]);
  const field = (key: keyof Settings, label: string, nullable = true) => (
    <label>
      {label}
      <input
        type="number"
        step="0.1"
        value={(draft[key] as number) ?? ""}
        onChange={(e) =>
          setDraft({
            ...draft,
            [key]:
              e.target.value === "" && nullable ? null : Number(e.target.value),
          })
        }
      />
    </label>
  );
  const changeInput = (updates: Partial<Settings>) =>
    setDraft({
      ...draft,
      ...updates,
      referenceDb: null,
      referenceRmsDbfs: null,
      referenceNote: "",
      confirmedMicSerial: "",
    });
  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        void save(draft);
      }}
    >
      <div className="section-line">
        <h2>Input & calibration</h2>
        <span className="tag">APPLIANCE SETTINGS</span>
      </div>
      <fieldset disabled={busy}>
        <div className="form-grid">
          <label>
            Input source
            <select
              value={draft.mode}
              onChange={(e) =>
                changeInput({ mode: e.target.value as Settings["mode"] })
              }
            >
              <option value="demo">Generated demonstration</option>
              <option value="device">USB microphone</option>
              <option value="wav">Local WAV replay</option>
            </select>
          </label>
          {draft.mode === "device" && (
            <label>
              Microphone
              <select
                value={draft.device}
                onChange={(e) => changeInput({ device: e.target.value })}
              >
                <option value="">Select a device</option>
                {devices.map((d, i) => (
                  <option key={`${d.id}-${i}`} value={d.id}>
                    {d.name}
                    {d.serialBound
                      ? " · USB serial"
                      : d.binding === "usb-port"
                        ? " · USB port"
                        : " · name binding"}
                  </option>
                ))}
                {draft.device &&
                  !devices.some((d) => d.id === draft.device) && (
                    <option value={draft.device}>
                      Saved device · unavailable
                    </option>
                  )}
              </select>
            </label>
          )}
          {draft.mode !== "demo" && (
            <label>
              Input channel (1-based)
              <input
                type="number"
                min="1"
                max="32"
                value={draft.channel + 1}
                onChange={(e) =>
                  changeInput({ channel: Number(e.target.value) - 1 })
                }
              />
            </label>
          )}
          {draft.mode === "wav" && (
            <label>
              WAV filename in appliance fixtures folder
              <input
                value={draft.wavPath}
                onChange={(e) => changeInput({ wavPath: e.target.value })}
                placeholder="reference.wav"
              />
            </label>
          )}
        </div>
        {deviceError && draft.mode === "device" && (
          <p className="notice">Audio device discovery: {deviceError}</p>
        )}
        <p className="muted">
          48 kHz input. No automatic default-microphone fallback. Changing input
          clears the reference.
        </p>
        <div className="form-grid">
          <label>
            UMIK calibration file · use the correct orientation
            <input
              type="file"
              accept=".txt,.cal"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                if (file.size > 200000) {
                  setFileError("Calibration file must be under 200 kB");
                  return;
                }
                try {
                  changeInput({ calibrationText: await file.text() });
                  setFileError("");
                } catch {
                  setFileError("Could not read calibration file");
                }
              }}
            />
          </label>
          <div className="file-state">
            {draft.calibrationText
              ? "Calibration file loaded in form"
              : "No frequency calibration file"}
            {draft.calibrationText && (
              <button
                type="button"
                onClick={() => changeInput({ calibrationText: "" })}
              >
                Clear file
              </button>
            )}
          </div>
        </div>
        {fileError && <p role="alert">{fileError}</p>}
        <div className="form-grid">
          <label>
            Level calibration
            <select
              value={draft.calibrationMode ?? "auto"}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  calibrationMode: e.target
                    .value as Settings["calibrationMode"],
                  referenceDb: null,
                  referenceRmsDbfs: null,
                  referenceNote: "",
                  manualDbfsAt94: null,
                })
              }
            >
              <option value="auto">Automatic UMIK-1 calibration file</option>
              <option value="reference">Known-level acoustic reference</option>
              <option value="manual">Manual sensitivity · dBFS at 94 dB SPL</option>
              <option value="off">Input diagnostics only</option>
            </select>
          </label>
        </div>
        {draft.calibrationMode === "manual" && (
          <div className="manual-cal">
            <p className="muted">
              Enter the raw RMS the microphone produces at 94 dB SPL, in this
              app’s dBFS scale. This is <strong>not</strong> the miniDSP “Sens
              Factor”: for a UMIK-1 on direct input at its normal gain it is
              Sens Factor − 30 dB (see the calibration guide). If unsure,
              measure a calibrator with the value shown under Input health.
            </p>
            <div className="form-grid">
              {field("manualDbfsAt94", "Sensitivity · dBFS at 94 dB SPL")}
              <label>
                Interface & OS input gain note (required)
                <input
                  value={draft.referenceNote}
                  onChange={(e) =>
                    setDraft({ ...draft, referenceNote: e.target.value })
                  }
                  placeholder="e.g. Focusrite Solo, macOS input 75%, no boost"
                />
              </label>
            </div>
            <p className="notice">
              The operating system’s input-volume slider (macOS Sound input,
              Windows microphone level) changes the digital level and makes this
              value wrong. Set the input level, note it here, and do not change
              it afterwards.
            </p>
          </div>
        )}
        {draft.mode === "device" &&
          fileSerial &&
          !selectedDevice?.serialBound && (
            <label className="check">
              <input
                type="checkbox"
                checked={draft.confirmedMicSerial === fileSerial}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    confirmedMicSerial: e.target.checked ? fileSerial : "",
                  })
                }
              />
              File serial {fileSerial} matches the label on this microphone
            </label>
          )}
        <p className="muted">
          A supported UMIK-1 on direct ALSA input uses its sensitivity file
          automatically. Microphones without a unique USB serial are tied to
          their USB port and your serial confirmation.
        </p>
        <details>
          <summary>Optional acoustic reference & field trim</summary>
          <p className="muted">
            For a separate field reference, enter a stable 1 kHz source’s known
            SPL and this app’s raw RMS dBFS at the same input gain. These values
            override automatic file calibration. Leave them blank to use the
            UMIK file. Field trim applies to either calibration method without
            changing the vendor file.
          </p>
          <div className="form-grid">
            {field("referenceDb", "Known reference level · dB SPL")}
            {field("referenceRmsDbfs", "Observed raw RMS · dBFS")}
            {field("fieldTrimDb", "Additional field trim · dB", false)}
            <label>
              Reference equipment, date & input gain
              <input
                value={draft.referenceNote}
                onChange={(e) =>
                  setDraft({ ...draft, referenceNote: e.target.value })
                }
              />
            </label>
          </div>
          <div className="actions">
            <button
              type="button"
              onClick={() => void captureReference()}
              disabled={capturing || draft.mode === "demo"}
            >
              {capturing ? "Capturing…" : "Capture raw RMS now"}
            </button>
            <span className="muted">
              Play a steady reference (a calibrator on the mic, or a known-SPL
              tone) and capture ~5&nbsp;s to fill Observed raw RMS.
            </span>
          </div>
          {captureNote && (
            <p className="notice" role="status">
              {captureNote}
            </p>
          )}
        </details>
        <details>
          <summary>Event thresholds & audience estimate</summary>
          <p className="muted">
            Blank thresholds disable alarms. Thresholds apply to
            fixed-microphone values. Set values appropriate to your event.
          </p>
          <div className="form-grid">
            {field("lasThreshold", "LAS threshold · dB")}
            {field("leqThreshold", "LAeq10 threshold · dB")}
            {field("peakThreshold", "LCpeak threshold · dB")}
            <label>
              Venue profile name
              <input
                value={draft.venueName}
                onChange={(e) =>
                  setDraft({ ...draft, venueName: e.target.value })
                }
              />
            </label>
            {field(
              "audienceOffsetDb",
              "Measured audience mapping · A offset dB",
            )}
          </div>
          <p className="muted">
            Audience estimates remain separate. No C-peak audience estimate is
            inferred. Raw fixed-mic logs are preserved.
          </p>
        </details>
        <button className="primary" type="submit">
          Apply & restart input
        </button>
        <p className="muted">
          Stop the event before applying settings. Applying restarts averaging
          windows.
        </p>
      </fieldset>
    </form>
  );
}

export function App() {
  const { frame, connection } = useTelemetry();
  const [layout, setLayout] = useState(loadLayout);
  const readingLocation = frame?.readingLocation;
  const audience = readingLocation?.audience ?? false;
  const mappingDescription =
    readingLocation?.offsetDb != null
      ? `${readingLocation.name} · ${readingLocation.offsetDb >= 0 ? "+" : ""}${readingLocation.offsetDb.toFixed(1)} dB · ${readingLocation.mappedAt && Number.isFinite(Date.parse(readingLocation.mappedAt)) ? new Date(readingLocation.mappedAt).toLocaleString() : "Capture date unavailable"}`
      : "No audience mapping saved";
  const display = location.pathname === "/display";
  const [panel, setPanel] = useState(!display);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [savedMappings, setSavedMappings] = useState<SavedMapping[]>([]);
  const [chosenMapping, setChosenMapping] = useState("");
  const [mappingSort, setMappingSort] = useState("newest");
  const sortedMappings = [...savedMappings].sort((a, b) => {
    const date = (v: SavedMapping) =>
      v.mappedAt && Number.isFinite(Date.parse(v.mappedAt))
        ? Date.parse(v.mappedAt)
        : 0;
    if (mappingSort === "name")
      return a.name.localeCompare(b.name) || date(b) - date(a);
    if (mappingSort === "oldest") return date(a) - date(b);
    if (mappingSort === "offset") return a.offsetDb - b.offsetDb;
    return date(b) - date(a);
  });
  useEffect(() => {
    let cancelled = false;
    setChosenMapping(readingLocation?.mappingId ?? "");
    void api<SavedMapping[]>("/audience-mappings")
      .then((items) => {
        if (!cancelled) setSavedMappings(items);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e.message));
      });
    return () => {
      cancelled = true;
    };
  }, [readingLocation?.mappingId]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [deviceError, setDeviceError] = useState<string | null>(null);
  const [event, setEvent] = useState<EventInfo | null>(null);
  const [events, setEvents] = useState<EventInfo[]>([]);
  const [history, setHistory] = useState<TelemetryFrame[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [eventName, setEventName] = useState("");
  const [annotation, setAnnotation] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    try {
      localStorage.setItem("spl-layout-v1", JSON.stringify(layout));
    } catch {
      setNotice(
        "Browser storage unavailable; layout applies for this session.",
      );
    }
  }, [layout]);

  useEffect(() => {
    if (!readingLocation) return;
    let cancelled = false;
    void api<Settings>("/config")
      .then((value) => {
        if (!cancelled) setSettings(value);
      })
      .catch(() => {
        /* Connection status remains visible. */
      });
    return () => {
      cancelled = true;
    };
  }, [
    readingLocation?.name,
    readingLocation?.offsetDb,
    readingLocation?.mappedAt,
    readingLocation?.audience,
  ]);

  const refresh = async () => {
    const [configuration, active, all] = await Promise.all([
      api<Settings>("/config"),
      api<EventInfo | null>("/events/current"),
      api<EventInfo[]>("/events"),
    ]);
    setSettings(configuration);
    setEvent(active);
    setEvents(all);
  };
  useEffect(() => {
    void refresh().catch((e) => setError(String(e.message)));
  }, []);
  useEffect(() => {
    let cancelled = false;
    void api<{ devices: Device[]; error: string | null }>("/devices")
      .then((d) => {
        if (cancelled) return;
        setDevices(d.devices);
        setDeviceError(d.error);
      })
      .catch((e) => {
        if (!cancelled) setDeviceError(String(e.message));
      });
    return () => {
      cancelled = true;
    };
  }, [
    frame?.status.connected,
    frame?.diagnostics.analogGainDb,
    frame?.diagnostics.device,
  ]);
  useEffect(() => {
    const update = async () => {
      try {
        const active = await api<EventInfo | null>("/events/current");
        setEvent(active);
        setSavedMappings(await api<SavedMapping[]>("/audience-mappings"));
        if (active)
          setHistory(
            await api<TelemetryFrame[]>(`/events/${active.id}/history`),
          );
      } catch {
        /* WebSocket and action errors carry connection health. */
      }
    };
    const timer = setInterval(() => {
      void update();
    }, 5000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!display) return;
    if (panel) dialog.current?.showModal();
    else dialog.current?.close();
  }, [panel, display]);

  const action = async (work: () => Promise<unknown>, message: string) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await work();
      await refresh();
      setNotice(message);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  const messages = statusMessages(frame, connection);
  const fault =
    connection !== "live" ||
    !frame?.status.connected ||
    frame.status.stale ||
    frame.status.clipping ||
    !!frame.status.loggingError ||
    !!frame.alarms.length;
  const style = {
    "--strip-width": `${layout.width}px`,
    "--strip-height": `${layout.height}px`,
    "--digits": `${Math.min(layout.fontSize, layout.height * 0.43)}px`,
    "--spacing": `${layout.gap}px`,
    left: `${layout.x}%`,
    top: `${layout.y}%`,
    transform: `translate(-${layout.x}%, -${layout.y}%)`,
  } as CSSProperties;

  const controls = (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">LOCAL SOUND MONITOR</p>
          <h1>SPL Dashboard</h1>
        </div>
        {display ? (
          <button
            onClick={() => {
              setPanel(false);
              toggle.current?.focus();
            }}
          >
            Return to strip
          </button>
        ) : (
          <a className="button" href="/display">
            Strip display ↗
          </a>
        )}
      </header>
      {error && (
        <div className="notice danger" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="notice" role="status">
          {notice}
        </div>
      )}
      <FirstRunBanner calibrated={frame?.status.calibrated ?? false} />
      <LayoutControls layout={layout} setLayout={setLayout} />
      <section className="card">
        <label>
          Strip reading location
          <select
            value={audience ? "audience" : "mic"}
            disabled={busy || connection !== "live" || !readingLocation}
            onChange={(e) =>
              void action(
                () =>
                  api("/reading-location", "PUT", {
                    audience: e.target.value === "audience",
                  }),
                "Reading location updated on all connected displays.",
              )
            }
          >
            <option value="mic">Measured at fixed microphone</option>
            <option
              value="audience"
              disabled={readingLocation?.offsetDb == null}
            >
              Estimated audience · requires a venue offset
            </option>
          </select>
        </label>
        <p>
          <strong>
            {audience
              ? "Active audience mapping:"
              : "Loaded mapping (audience display off):"}
          </strong>{" "}
          {mappingDescription}
        </p>
        <label>
          Sort mappings
          <select
            value={mappingSort}
            onChange={(e) => setMappingSort(e.target.value)}
          >
            <option value="newest">Date · newest first</option>
            <option value="oldest">Date · oldest first</option>
            <option value="name">Name · A–Z</option>
            <option value="offset">Correction · lowest first</option>
          </select>
        </label>
        <label>
          Saved audience mappings
          <select
            value={chosenMapping}
            disabled={busy || !!event}
            onChange={(e) => setChosenMapping(e.target.value)}
          >
            <option value="">Select a saved mapping</option>
            {sortedMappings.map((mapping) => (
              <option key={mapping.id} value={mapping.id}>
                {mapping.name} · {mapping.offsetDb >= 0 ? "+" : ""}
                {mapping.offsetDb.toFixed(1)} dB ·{" "}
                {mapping.mappedAt &&
                Number.isFinite(Date.parse(mapping.mappedAt))
                  ? new Date(mapping.mappedAt).toLocaleString()
                  : "Capture date unavailable"}
              </option>
            ))}
          </select>
        </label>
        <div className="actions">
          <button
            disabled={
              busy ||
              !!event ||
              !chosenMapping ||
              (chosenMapping === readingLocation?.mappingId && audience)
            }
            onClick={() =>
              void action(
                () =>
                  api(
                    `/audience-mappings/${encodeURIComponent(chosenMapping)}/activate`,
                    "POST",
                  ),
                "Saved mapping applied to all displays; averages restarted.",
              )
            }
          >
            Use selected mapping on all displays
          </button>
          <button
            disabled={busy || !!event || !readingLocation?.mappingId}
            onClick={() =>
              void action(
                () => api("/audience-mapping/clear", "POST"),
                "Loaded mapping cleared. All displays show measured levels; the saved mapping and past events are retained. Averages restarted.",
              )
            }
          >
            Clear loaded mapping
          </button>
          <button
            disabled={
              busy ||
              !chosenMapping ||
              chosenMapping === readingLocation?.mappingId
            }
            onClick={() => {
              const item = savedMappings.find((m) => m.id === chosenMapping);
              if (
                !item ||
                !window.confirm(
                  `Delete saved mapping "${item.name}" (${item.offsetDb.toFixed(1)} dB, ${item.mappedAt ?? "undated"})? This removes it from the library. Existing event records are retained.`,
                )
              )
                return;
              void action(async () => {
                await api(
                  `/audience-mappings/${encodeURIComponent(item.id)}`,
                  "DELETE",
                );
                setSavedMappings(
                  await api<SavedMapping[]>("/audience-mappings"),
                );
                setChosenMapping(readingLocation?.mappingId ?? "");
              }, "Saved mapping deleted. Existing event records retained.");
            }}
          >
            Delete selected mapping
          </button>
        </div>
        <p className="muted">
          Saved on the appliance. New mappings are added to this list; earlier
          mappings are retained. Reuse only with the same room, speaker setup
          and event mic position. Applying restarts averaging windows.
        </p>
        {event && (
          <p role="status">
            Stop the recording in Event log before switching or clearing
            mappings. Existing records will be retained.
          </p>
        )}
        {chosenMapping && chosenMapping === readingLocation?.mappingId && (
          <p className="muted">
            The loaded mapping is protected from deletion. Clear it first, then
            select it from the saved list to delete it.
          </p>
        )}
        <p className="muted">
          Reading location is shared by all displays. Size and position remain
          local to this browser.
        </p>
        <p>
          Audience mode applies the venue offset to Live level, Maximum live
          level and both averages. C peak, spectrum and alarm thresholds remain
          at the fixed microphone.
        </p>
      </section>
      {settings && (
        <AudienceMapping
          settings={settings}
          disabled={busy || !!event}
          recording={!!event}
          apply={async (s) => {
            await api("/config", "PUT", s);
            await refresh();
          }}
        />
      )}

      <div className="two-columns">
        <section className="card">
          <div className="section-line">
            <h2>Event log</h2>
            <span className="tag">
              {event ? "● RECORDING" : "NOT RECORDING"}
            </span>
          </div>
          {event ? (
            <>
              <h3>{event.name}</h3>
              <p className="muted">
                Started {new Date(event.started).toLocaleString()} · stored on
                the appliance
              </p>
              <div className="actions">
                <button
                  disabled={busy}
                  onClick={() =>
                    void action(
                      () => api("/events/current/reset-peak", "POST"),
                      "Peak hold reset and annotated.",
                    )
                  }
                >
                  Reset peak
                </button>
                <button
                  disabled={busy}
                  onClick={() =>
                    void action(
                      () => api("/events/current/stop", "POST"),
                      "Event stopped; records retained.",
                    )
                  }
                >
                  Stop event
                </button>
                <a
                  className="button"
                  href={`/api/events/${event.id}/export.csv`}
                >
                  Export CSV
                </a>
              </div>
              <form
                className="inline-form"
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  void action(async () => {
                    await api("/events/current/annotations", "POST", {
                      text: annotation,
                    });
                    setAnnotation("");
                  }, "Annotation saved.");
                }}
              >
                <input
                  aria-label="Event annotation"
                  placeholder="Note a complaint, change, or soundcheck…"
                  maxLength={1000}
                  required
                  value={annotation}
                  onChange={(e) => setAnnotation(e.target.value)}
                />
                <button disabled={busy}>Add note</button>
              </form>
              <ul className="annotations">
                {event.annotations?.slice(-5).map((a, i) => (
                  <li key={i}>
                    <time>{new Date(a.timestamp).toLocaleTimeString()}</time>{" "}
                    {a.text}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <form
              className="inline-form"
              onSubmit={(e) => {
                e.preventDefault();
                setHistory([]);
                void action(
                  () => api("/events", "POST", { name: eventName }),
                  "Event started.",
                );
              }}
            >
              <input
                aria-label="Event name"
                required
                maxLength={120}
                placeholder="Event name"
                value={eventName}
                onChange={(e) => setEventName(e.target.value)}
              />
              <button className="primary" disabled={busy}>
                Start event
              </button>
            </form>
          )}
          <History frames={history} />
          <details>
            <summary>Saved events ({events.length})</summary>
            <ul className="event-list">
              {events.map((e) => (
                <li key={e.id}>
                  <span>
                    {e.name}
                    <small>{new Date(e.started).toLocaleString()}</small>
                  </span>
                  <a href={`/api/events/${e.id}/export.csv`}>CSV</a>
                  <a href={`/api/events/${e.id}/summary.json`}>Details</a>
                </li>
              ))}
            </ul>
          </details>
        </section>
        <section className="card">
          <div className="section-line">
            <h2>Input health</h2>
            <span className="tag">
              {frame?.source === "umik-unverified"
                ? "USB MICROPHONE"
                : frame?.source === "wav-unverified"
                  ? "WAV REPLAY"
                  : frame?.source === "demo"
                    ? "DEMO"
                    : "WAITING"}
            </span>
          </div>
          <p className={fault ? "health-fault" : "muted"}>
            {frame?.status.message ?? "Connecting to appliance…"}
          </p>
          <dl className="diagnostics">
            <div>
              <dt>Raw RMS</dt>
              <dd>
                {format(frame?.diagnostics.rmsDbfs)} <small>dBFS</small>
              </dd>
            </div>
            <div>
              <dt>Raw peak</dt>
              <dd>
                {format(frame?.diagnostics.peakDbfs)} <small>dBFS</small>
              </dd>
            </div>
            <div>
              <dt>Input rate</dt>
              <dd>
                {frame?.diagnostics.sampleRate ?? "—"} <small>Hz</small>
              </dd>
            </div>
            <div>
              <dt>Input age</dt>
              <dd>
                {format(frame?.diagnostics.inputAgeSeconds, 2)} <small>s</small>
              </dd>
            </div>
            <div>
              <dt>Gaps / overruns</dt>
              <dd>
                {frame?.status.gapCount ?? 0} / {frame?.status.overruns ?? 0}
              </dd>
            </div>
            <div>
              <dt>Clipped samples</dt>
              <dd>
                {format(frame?.status.clipSeconds, 3)} <small>s total</small>
              </dd>
            </div>
          </dl>
          <p className="muted">
            {!frame?.measured
              ? "SPL readings need absolute calibration; waiting will not fill the meters."
              : frame.status.warmupSeconds
                ? `LAeq10 warming: ${remaining(frame.status.warmupSeconds)} remaining.`
                : "Full averaging windows available."}{" "}
            Peak held {frame?.peakHold ?? "since input start/reset"}.
          </p>
          <p className="muted wrap">
            Calibration serial: {frame?.diagnostics.calibrationSerial ?? "none"}
            <br />
            File hash:{" "}
            {frame?.diagnostics.calibrationHash?.slice(0, 16) ?? "none"}
            <br />
            Calibration: {frame?.diagnostics.calibrationMethod ?? "none"}
            <br />
            Applied SPL offset:{" "}
            {format(frame?.diagnostics.referenceOffsetDb, 3)} dB
            <br />
            Input analog / digital gain:{" "}
            {format(frame?.diagnostics.analogGainDb)} /{" "}
            {format(frame?.diagnostics.digitalGainDb)} dB
            <br />
            {frame?.status.loggingError}
          </p>
          {frame?.estimatedAudience && (
            <div className="estimate">
              <h3>Estimated audience · {settings?.venueName}</h3>
              <p>
                LAS {format(frame.estimatedAudience.lasDb)} · LAeq1{" "}
                {format(frame.estimatedAudience.laeq1Db)} · LAeq10{" "}
                {format(frame.estimatedAudience.laeq10Db)} dB
              </p>
              <small>
                Profile offset {settings?.audienceOffsetDb} dB. The strip can
                show these estimates using Strip reading location.
              </small>
            </div>
          )}
          <p className="notice">
            {frame?.source === "demo"
              ? "Demonstration values are generated."
              : frame?.status.calibrated
                ? "File or reference calibration is applied. Full hardware validation is still pending; this is separate from calibration."
                : (frame?.diagnostics.calibrationReason ??
                  "Load a calibration file or set an acoustic reference.")}
          </p>
        </section>
      </div>
      {settings && (
        <Setup
          settings={settings}
          devices={devices}
          deviceError={deviceError}
          busy={busy || !!event}
          save={(s) =>
            action(
              () => api("/config", "PUT", s),
              "Settings applied; input restarted.",
            )
          }
        />
      )}
      <footer>
        <p>
          Runs on your event LAN · audio stays on this computer · browsers only
          receive numbers
        </p>
        <p className="disclaimer">{DISCLAIMER}</p>
      </footer>
    </>
  );

  return (
    <main className={display ? "app display-mode" : "app"}>
      <div
        className="preview-stage"
        style={
          display ? undefined : { height: Math.max(160, layout.height + 24) }
        }
      >
        <section
          className={`strip ${fault ? "strip--fault" : ""} ${layout.details ? "" : "strip--minimal"}`}
          style={style}
          aria-label="Fixed microphone SPL strip"
        >
          <div
            className={`strip-status ${fault ? "health-fault" : "health-caution"}`}
            role="status"
            aria-live="polite"
          >
            <span className="status-mark">
              {fault ? "!" : frame?.source === "demo" ? "◇" : "△"}
            </span>
            <span>
              {audience && (
                <small
                  className="audience-indicator"
                  title={mappingDescription}
                >
                  {frame?.estimatedAudience
                    ? `EST · ${readingLocation?.name || "AUDIENCE"}`
                    : "NO AUDIENCE MAPPING"}
                </small>
              )}
              {audience && (
                <small className="mapping-stamp" title={mappingDescription}>
                  {readingLocation?.offsetDb != null
                    ? `${readingLocation.offsetDb >= 0 ? "+" : ""}${readingLocation.offsetDb.toFixed(1)} dB`
                    : "NO MAPPING"}
                  {readingLocation?.mappedAt &&
                  Number.isFinite(Date.parse(readingLocation.mappedAt))
                    ? ` · ${new Date(readingLocation.mappedAt).toLocaleDateString(undefined, { month: "short", day: "numeric" })} ${new Date(readingLocation.mappedAt).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`
                    : " · undated"}
                </small>
              )}
              {messages.length ? messages.join(" · ") : "LIVE"}
              <small>{frame?.eventId ? "● LOG" : "NO LOG"}</small>
              {frame && frame.status.warmupSeconds > 0 && (
                <small>WARM {remaining(frame.status.warmupSeconds)}</small>
              )}
            </span>
          </div>
          <div className="meters">
            {metrics.map(({ key, label, detail }) => (
              <div className="meter" key={key}>
                <span className="meter-label">
                  {audience && key === "lcpeakDb" ? "Mic C peak" : label}{" "}
                  {(key === "lcpeakDb" || key === "lasMaxDb") && (
                    <button
                      className="peak-reset"
                      aria-label={
                        key === "lasMaxDb"
                          ? "Reset maximum live level"
                          : "Reset peak"
                      }
                      title={
                        key === "lasMaxDb"
                          ? "Reset maximum live level"
                          : "Reset held peak"
                      }
                      disabled={busy || !frame?.status.connected}
                      onClick={() =>
                        void action(
                          () =>
                            api(
                              key === "lasMaxDb"
                                ? "/events/current/reset-maximum"
                                : "/events/current/reset-peak",
                              "POST",
                            ),
                          "Held value reset. Earlier logs are retained.",
                        )
                      }
                    >
                      ↺
                    </button>
                  )}
                </span>
                <strong>
                  {format(
                    audience && key !== "lcpeakDb"
                      ? frame?.estimatedAudience?.[key]
                      : frame?.measured?.[key],
                  )}
                </strong>
                {layout.details && (
                  <small>
                    {key === "laeq10Db" && frame?.status.warmupSeconds
                      ? `warm ${remaining(frame.status.warmupSeconds)}`
                      : detail}
                  </small>
                )}
              </div>
            ))}
          </div>
          {layout.spectrum && (
            <SpectrumAnalyzer
              clipping={!!frame?.status.clipping}
              spectrum={frame?.spectrum}
              live={
                connection === "live" &&
                !!frame?.status.connected &&
                !frame.status.stale
              }
            />
          )}
          <button
            className="strip-settings"
            ref={toggle}
            aria-label={
              display ? "Open display settings" : "Scroll to display settings"
            }
            onClick={() => {
              if (display) setPanel(true);
              else
                document
                  .querySelector(".page-header")
                  ?.scrollIntoView({ behavior: "smooth" });
            }}
          >
            •••
          </button>
        </section>
      </div>
      {display && error && (
        <div role="alert" className="strip-action-error">
          {error}
        </div>
      )}
      {display ? (
        <dialog
          ref={dialog}
          className="control-dialog"
          onCancel={() => setPanel(false)}
          onClose={() => setPanel(false)}
          aria-label="Display and appliance settings"
        >
          <div className="page">{controls}</div>
        </dialog>
      ) : (
        <div className="page">{controls}</div>
      )}
    </main>
  );
}

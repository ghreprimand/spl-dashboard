import { useEffect, useState } from "react";
import type { Settings } from "./types";

export function mappingOffset(levels: number[]): number {
  if (levels.length !== 5 || !levels.every(Number.isFinite))
    throw Error("Five valid captures are required");
  if (Math.abs(levels[0] - levels[4]) > 2)
    throw Error(
      "Fixed-position checks differ by more than 2 dB. Check playback and placement, then repeat the mapping.",
    );
  const energyMean = (values: number[]) =>
    10 *
    Math.log10(
      values.reduce((sum, v) => sum + 10 ** (v / 10), 0) / values.length,
    );
  return energyMean(levels.slice(1, 4)) - energyMean([levels[0], levels[4]]);
}
const positions = [
  "Event mic position",
  "Audience position 1",
  "Audience position 2",
  "Audience position 3",
  "Return to event mic position",
];
interface Capture {
  levelDb: number;
  seconds: number;
  calibrationHash: string | null;
  offsetDb: number;
  device: string;
}
export function AudienceMapping({
  settings,
  disabled,
  recording,
  apply,
}: {
  settings: Settings;
  disabled: boolean;
  recording?: boolean;
  apply: (settings: Settings) => Promise<void>;
}) {
  const [captures, setCaptures] = useState<Capture[]>([]);
  const [name, setName] = useState(settings.venueName);
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");
  const [applied, setApplied] = useState(false);
  useEffect(() => {
    if (!busy) return;
    const timer = setInterval(() => setElapsed((v) => v + 1), 1000);
    return () => clearInterval(timer);
  }, [busy]);
  const capture = async () => {
    setBusy(true);
    setElapsed(0);
    setError("");
    setApplied(false);
    try {
      const response = await fetch("/api/audience-mapping/capture", {
        method: "POST",
        headers: { "X-SPL-Client": "dashboard" },
        signal: AbortSignal.timeout(45000),
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "Capture failed");
      if (!Number.isFinite(data.levelDb)) throw Error("Invalid capture");
      const first = captures[0];
      if (
        first &&
        (first.device !== data.device ||
          first.offsetDb !== data.offsetDb ||
          first.calibrationHash !== data.calibrationHash)
      )
        throw Error("Input or calibration changed. Start over.");
      setCaptures([...captures, data]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  let offset: number | null = null,
    problem = "";
  if (captures.length === 5) {
    try {
      offset = mappingOffset(captures.map((c) => c.levelDb));
      if (Math.abs(offset) > 30) {
        problem =
          "Mapping exceeds the supported ±30 dB range. Check the positions and repeat.";
        offset = null;
      }
    } catch (e) {
      problem = (e as Error).message;
    }
  }
  return (
    <section className="card audience-mapping">
      <h2>Audience level mapping</h2>
      <p>
        Measure three audience positions and your fixed mic position using the
        same steady pink-noise playback. Keep the playback level, EQ and speaker
        setup unchanged. Start around 75–80 dBA measured at an audience
        position, at least 10 dB above background at every position (preferably
        15 dB). Use measured mic readings to set playback, not an existing
        audience estimate. Measure during a quieter setup period if needed; show
        volume is unnecessary.
      </p>
      <p>
        Move the mic between captures, keep it pointing up at listener ear
        height, and let it settle before pressing Capture. Leave the mic at its
        fixed position after the final check. Stop event recording before
        starting.
      </p>
      <p>
        The event mic position is exactly where you will leave the mic during
        the show, at its final height and orientation.
      </p>
      {disabled && (
        <p role="status">
          {recording
            ? "Stop the recording in Event log to enable mapping capture. Existing records will be retained."
            : "Another operation is in progress. Capture will be available when it finishes."}
        </p>
      )}
      <label>
        Mapping name
        <input
          value={name}
          disabled={busy}
          onChange={(e) => setName(e.target.value)}
          placeholder="Venue · room · speaker setup"
          maxLength={120}
        />
      </label>
      <ol>
        {positions.map((position, i) => (
          <li key={position}>
            {position}:{" "}
            {captures[i]
              ? `${captures[i].levelDb.toFixed(1)} dBA · ${captures[i].seconds.toFixed(1)} s`
              : i === captures.length
                ? "next"
                : "waiting"}
          </li>
        ))}
      </ol>
      <div className="actions">
        {captures.length < 5 && (
          <button disabled={disabled || busy} onClick={() => void capture()}>
            {busy
              ? `Capturing · ${elapsed}/30 seconds`
              : `Capture ${positions[captures.length]} · 30 seconds`}
          </button>
        )}
        <button
          disabled={busy || captures.length === 0}
          onClick={() => {
            setCaptures([]);
            setError("");
            setApplied(false);
          }}
        >
          Start over
        </button>
        {offset !== null && (
          <button
            disabled={disabled || busy || !name.trim()}
            onClick={async () => {
              setBusy(true);
              setError("");
              try {
                await apply({
                  ...settings,
                  venueName: name.trim(),
                  audienceDisplay: true,
                  audienceOffsetDb: offset,
                  audienceMappingNote: JSON.stringify({
                    date: new Date().toISOString(),
                    positions,
                    captures,
                    method:
                      "Equal-energy mean of three audience positions minus two fixed checks",
                  }),
                });
                setApplied(true);
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            Apply {offset >= 0 ? "+" : ""}
            {offset.toFixed(1)} dB & show audience estimates
          </button>
        )}
      </div>
      {(error || problem) && <p role="alert">{error || problem}</p>}
      {applied && (
        <p role="status">
          Audience mapping saved on the appliance. All connected strips now show
          audience estimates for A-weighted levels.
        </p>
      )}
      <p className="muted">
        This estimates the equal-energy average of your three selected
        positions—not every listener or the loudest location. Occupancy and
        system changes can alter the relationship. Mic measurements and logs
        remain unchanged; C peak and the spectrum remain measured at the mic.
      </p>
    </section>
  );
}

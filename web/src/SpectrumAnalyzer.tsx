import { useEffect, useMemo, useRef, useState } from "react";
import type { Spectrum, SpectrumBands } from "./types";
import { loadSpectrumOptions, type SpectrumOptions } from "./spectrumOptions";

const frequency = (hz: number) =>
  hz >= 1000
    ? `${(hz / 1000).toFixed(hz >= 10000 ? 1 : 2)} kHz`
    : `${hz.toFixed(1)} Hz`;
const MIN_HZ = 20,
  MAX_HZ = 20000;
interface PlotProps {
  bands?: SpectrumBands;
  levels: (number | null)[];
  held: (number | null)[];
  options: SpectrumOptions;
  unit: string;
  live: boolean;
  clipping: boolean;
  frozen: boolean;
  large?: boolean;
  identity: string;
}
function Plot(props: PlotProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const latest = useRef(props);
  latest.current = props;
  const [selected, setSelected] = useState<number | null>(null);
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  useEffect(() => {
    const element = canvas.current,
      ctx = element?.getContext("2d");
    if (!element || !ctx) return;
    let animation = 0,
      previous = 0,
      identity = "";
    let values: (number | null)[] = [];
    const reduced = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const draw = (now: number) => {
      const p = latest.current;
      const width = element.clientWidth,
        height = element.clientHeight;
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      if (
        element.width !== Math.round(width * ratio) ||
        element.height !== Math.round(height * ratio)
      ) {
        element.width = Math.round(width * ratio);
        element.height = Math.round(height * ratio);
      }
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.clearRect(0, 0, width, height);
      const left = p.large ? 44 : 2,
        right = width - 5,
        top = p.large ? 26 : 12,
        bottom = height - 19;
      const ceiling = p.unit === "dBFS" ? p.options.top - 140 : p.options.top,
        floor = ceiling - p.options.range;
      const x = (f: number) =>
        left +
        (Math.log(f / MIN_HZ) / Math.log(MAX_HZ / MIN_HZ)) * (right - left);
      const y = (v: number) =>
        bottom -
        Math.max(0, Math.min(1, (v - floor) / p.options.range)) *
          (bottom - top);
      ctx.font = `${p.large ? 11 : 9}px system-ui`;
      const ticks =
        p.large && width > 600
          ? [20, 31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
          : [100, 1000, 10000];
      ticks.forEach((f) => {
        ctx.strokeStyle = "#294039";
        ctx.beginPath();
        ctx.moveTo(x(f), top);
        ctx.lineTo(x(f), bottom);
        ctx.stroke();
        ctx.fillStyle = "#9bb4b4";
        ctx.textAlign = f === 20 ? "left" : f === 20000 ? "right" : "center";
        ctx.fillText(f >= 1000 ? `${f / 1000}k` : `${f}`, x(f), height - 3);
      });
      for (let v = floor; v <= ceiling; v += 10) {
        ctx.strokeStyle = "#22372f";
        ctx.beginPath();
        ctx.moveTo(left, y(v));
        ctx.lineTo(right, y(v));
        ctx.stroke();
        if (p.large) {
          ctx.textAlign = "right";
          ctx.fillStyle = "#9bb4b4";
          ctx.fillText(`${v}`, left - 7, y(v) + 3);
        }
      }
      const key = `${p.identity}:${p.options.fraction}:${p.options.averaging}:${p.unit}`;
      if (key !== identity || values.length !== p.levels.length) {
        values = [...p.levels];
        identity = key;
      }
      const alpha =
        reduced || p.frozen
          ? 1
          : -Math.expm1(-Math.min(now - previous, 100) / 60);
      if (p.live || p.frozen)
        values = values.map((v, i) =>
          p.levels[i] == null
            ? null
            : v == null
              ? p.levels[i]
              : v + (p.levels[i]! - v) * alpha,
        );
      const plot = (data: (number | null)[], color: string, fill: boolean) => {
        if (!p.bands?.ready || !data.length) return;
        ctx.save();
        ctx.beginPath();
        ctx.rect(
          left,
          top,
          Math.max(0, right - left),
          Math.max(0, bottom - top),
        );
        ctx.clip();
        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        ctx.lineWidth = fill ? 1.6 : 1;
        if (!fill) ctx.setLineDash([4, 3]);
        let path = false;
        ctx.beginPath();
        data.forEach((v, i) => {
          if (v === null) {
            if (path) ctx.stroke();
            ctx.beginPath();
            path = false;
            return;
          }
          const a = x(p.bands!.edgesHz[i]),
            b = x(p.bands!.edgesHz[i + 1]),
            centre = x(p.bands!.centresHz[i]);
          if (fill) {
            ctx.save();
            ctx.globalAlpha = 0.1;
            ctx.fillRect(a, y(v), b - a, bottom - y(v));
            ctx.restore();
          }
          if (p.options.style === "steps") {
            if (!path) ctx.moveTo(a, y(v));
            else ctx.lineTo(a, y(v));
            ctx.lineTo(b, y(v));
          } else {
            if (!path) ctx.moveTo(centre, y(v));
            else ctx.lineTo(centre, y(v));
          }
          path = true;
        });
        ctx.stroke();
        ctx.restore();
      };
      plot(values, p.live ? "#b1eb96" : "#82978b", true);
      plot(p.held, "#efc37b", false);
      const selected = selectedRef.current;
      if (
        p.large &&
        selected !== null &&
        p.bands?.ready &&
        p.bands.centresHz[selected]
      ) {
        const at = x(p.bands.centresHz[selected]);
        ctx.strokeStyle = "#e7eee9";
        ctx.beginPath();
        ctx.moveTo(at, top);
        ctx.lineTo(at, bottom);
        ctx.stroke();
      }
      const high = p.levels.some((v) => v !== null && v > ceiling),
        low = p.levels.some((v) => v !== null && v < floor);
      const state = !p.live
        ? "STALE · INPUT UNAVAILABLE"
        : p.clipping
          ? "CLIPPING · VALUES UNRELIABLE"
          : p.frozen
            ? "FROZEN"
            : !p.bands?.ready
              ? "WARMING ANALYZER"
              : high
                ? "↑ ABOVE SCALE"
                : low
                  ? "↓ BELOW SCALE"
                  : "";
      ctx.fillStyle = p.clipping || !p.live ? "#ffc0a8" : "#bad1c2";
      ctx.textAlign = "left";
      ctx.fillText(
        p.large ? `${p.unit} per band · ${state || "LIVE"}` : state,
        left,
        p.large ? 15 : 9,
      );
      previous = now;
      animation = requestAnimationFrame(draw);
    };
    animation = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animation);
  }, []);
  const choose = (clientX: number) => {
    if (!props.bands?.ready || !canvas.current) return;
    const rect = canvas.current.getBoundingClientRect(),
      left = props.large ? 44 : 2;
    const proportion = Math.max(
      0,
      Math.min(1, (clientX - rect.left - left) / (rect.width - left - 5)),
    );
    const hz = MIN_HZ * (MAX_HZ / MIN_HZ) ** proportion;
    const index =
      props.bands.edgesHz.findIndex((edge, i) => i > 0 && hz < edge) - 1;
    setSelected(
      Math.max(
        0,
        Math.min(
          props.bands.centresHz.length - 1,
          index < 0 ? props.bands.centresHz.length - 1 : index,
        ),
      ),
    );
  };
  const band =
    selected !== null &&
    props.bands?.ready &&
    selected < props.bands.centresHz.length
      ? props.bands
      : undefined;
  return (
    <div
      className={
        props.large ? "analyzer-plot analyzer-plot--large" : "analyzer-plot"
      }
    >
      <canvas
        ref={canvas}
        className={
          props.large
            ? "analyzer-canvas analyzer-canvas--large"
            : "analyzer-canvas"
        }
        role="img"
        tabIndex={props.large ? 0 : undefined}
        aria-label={`Unweighted 1/${props.options.fraction}-octave analyzer, ${props.unit}. ${props.large ? "Use arrow keys or tap to inspect bands." : ""}`}
        onPointerMove={props.large ? (e) => choose(e.clientX) : undefined}
        onPointerDown={props.large ? (e) => choose(e.clientX) : undefined}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
            e.preventDefault();
            setSelected((i) =>
              Math.max(
                0,
                Math.min(
                  (props.bands?.centresHz.length ?? 1) - 1,
                  (i ?? 0) + (e.key === "ArrowRight" ? 1 : -1),
                ),
              ),
            );
          }
        }}
      />
      {props.large && (
        <output className="analyzer-readout">
          {band && selected !== null
            ? `${frequency(band.centresHz[selected])} · ${frequency(band.edgesHz[selected])}–${frequency(band.edgesHz[selected + 1])} · ${props.levels[selected]?.toFixed(1) ?? "below numeric floor"} ${props.unit} per band`
            : "Tap the plot or use arrow keys to inspect frequency and level."}
        </output>
      )}
    </div>
  );
}

export function SpectrumAnalyzer({
  spectrum,
  live,
  clipping = false,
}: {
  spectrum?: Spectrum;
  live: boolean;
  clipping?: boolean;
}) {
  const [open, setOpen] = useState(false),
    [options, setOptions] = useState(loadSpectrumOptions);
  const [frozen, setFrozen] = useState<Spectrum | null>(null),
    [hold, setHold] = useState(false),
    [holdReset, setHoldReset] = useState(0);
  const dialog = useRef<HTMLDialogElement>(null);
  const peak = useRef<{ key: string; values: (number | null)[] }>({
    key: "",
    values: [],
  });
  useEffect(() => {
    if (open) dialog.current?.showModal();
    else dialog.current?.close();
  }, [open]);
  useEffect(() => {
    try {
      localStorage.setItem("spl-spectrum-v2", JSON.stringify(options));
    } catch {
      /* Still usable without browser storage. */
    }
  }, [options]);
  useEffect(() => {
    setFrozen(null);
  }, [spectrum?.analysisId]);
  const shown = frozen ?? spectrum;
  const bands = shown?.bands?.find((b) => b.fraction === options.fraction);
  const levels = useMemo(
    () =>
      bands
        ? options.averaging === "stable"
          ? bands.smoothedLevelsDb
          : bands.levelsDb
        : [],
    [bands, options.averaging],
  );
  const key = `${shown?.analysisId}:${options.fraction}:${options.averaging}:${holdReset}:${hold}`;
  if (peak.current.key !== key) peak.current = { key, values: [] };
  if (hold && live && !clipping && bands?.ready)
    peak.current.values = levels.map((v, i) =>
      v === null
        ? (peak.current.values[i] ?? null)
        : Math.max(v, peak.current.values[i] ?? v),
    );
  const unit = shown?.unit ?? "dB SPL";
  const ceiling = unit === "dBFS" ? options.top - 140 : options.top;
  const plotProps = {
    bands,
    levels,
    held: hold ? peak.current.values : [],
    options,
    unit,
    live,
    clipping,
    frozen: !!frozen,
    identity: shown?.analysisId ?? "",
  };
  return (
    <>
      <button
        className="spectrum spectrum-button"
        aria-label="Open frequency analyzer"
        onClick={() => setOpen(true)}
      >
        <Plot {...plotProps} />
      </button>
      {open && (
        <dialog
          ref={dialog}
          className="analyzer-dialog"
          aria-label="Frequency analyzer"
          onCancel={() => setOpen(false)}
          onClose={() => setOpen(false)}
        >
          <header>
            <div>
              <h2>Frequency analyzer</h2>
              <p>Fixed mic · unweighted band levels · nominal 20 Hz–20 kHz</p>
            </div>
            <button onClick={() => setOpen(false)}>Close</button>
          </header>
          <div className="analyzer-controls">
            <label>
              Band detail
              <select
                value={options.fraction}
                onChange={(e) =>
                  setOptions({
                    ...options,
                    fraction: Number(e.target.value) as 3 | 6 | 12,
                  })
                }
              >
                <option value={3}>1/3 octave · broad</option>
                <option value={6}>1/6 octave · balanced</option>
                <option value={12}>1/12 octave · fine</option>
              </select>
            </label>
            <label>
              Averaging
              <select
                value={options.averaging}
                onChange={(e) =>
                  setOptions({
                    ...options,
                    averaging: e.target.value as "live" | "stable",
                  })
                }
              >
                <option value="live">Live window</option>
                <option value="stable">Stable · +1 s energy smoothing</option>
              </select>
            </label>
            <label>
              Drawing
              <select
                value={options.style}
                onChange={(e) =>
                  setOptions({
                    ...options,
                    style: e.target.value as "steps" | "line",
                  })
                }
              >
                <option value="steps">Band steps</option>
                <option value="line">Centre line</option>
              </select>
            </label>
            <label>
              Top · {unit}
              <select
                value={options.top}
                onChange={(e) =>
                  setOptions({ ...options, top: Number(e.target.value) })
                }
              >
                {[40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150].map(
                  (v) => (
                    <option key={v} value={v}>
                      {unit === "dBFS" ? v - 140 : v}
                    </option>
                  ),
                )}
              </select>
            </label>
            <label>
              Range
              <select
                value={options.range}
                onChange={(e) =>
                  setOptions({ ...options, range: Number(e.target.value) })
                }
              >
                {[40, 60, 80, 100].map((v) => (
                  <option key={v} value={v}>
                    {v} dB
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="actions analyzer-actions">
            <button
              disabled={!levels.some((v) => v !== null)}
              onClick={() => {
                const highest = Math.max(
                  ...levels.filter((v): v is number => v !== null),
                );
                const top =
                  Math.ceil((highest + 10 + (unit === "dBFS" ? 140 : 0)) / 10) *
                  10;
                setOptions({
                  ...options,
                  top: Math.max(40, Math.min(150, top)),
                });
              }}
            >
              Fit levels
            </button>
            <button
              disabled={!bands?.ready}
              onClick={() => setFrozen(frozen ? null : (spectrum ?? null))}
            >
              {frozen ? "Resume live" : "Freeze view"}
            </button>
            <label>
              <input
                type="checkbox"
                checked={hold}
                onChange={(e) => setHold(e.target.checked)}
              />
              Hold band maxima
            </label>
            <button disabled={!hold} onClick={() => setHoldReset((v) => v + 1)}>
              Reset band maxima
            </button>
            <span>
              {ceiling - options.range}–{ceiling} {unit} ·{" "}
              {bands?.minWindowSeconds ?? bands?.windowSeconds ?? 1}–
              {bands?.windowSeconds ?? (options.fraction === 12 ? 2 : 1)} s
              windows · {shown?.updateHz ?? 10} updates/s
            </span>
          </div>
          <Plot {...plotProps} large />
          <p>
            Band totals, not total SPL or a speaker-response measurement. Finer
            bands read lower for broadband sound. Dashed maxima are local to
            this display. Changing analysis settings resets them. No audience
            offset is applied.
          </p>
          {!spectrum?.bands && (
            <p role="status">
              Waiting for updated analyzer data from the appliance.
            </p>
          )}
        </dialog>
      )}
    </>
  );
}

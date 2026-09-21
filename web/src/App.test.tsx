import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App, statusMessages } from "./App";
import { validFrame } from "./api";
import { loadLayout, normalizeLayout } from "./layout";
import type { TelemetryFrame } from "./types";

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 1;
  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }
  close() {
    this.readyState = 3;
    this.onclose?.();
  }
}
const frame: TelemetryFrame = {
  schemaVersion: 2,
  timestamp: "2026-09-20T20:00:00Z",
  sequence: 1,
  source: "umik-unverified",
  status: {
    connected: true,
    calibrated: false,
    validationPending: true,
    clipping: false,
    stale: false,
    message: "Input diagnostics only",
    overruns: 0,
    gapCount: 0,
    clipSeconds: 0,
    warmupSeconds: 600,
    loggingError: null,
  },
  diagnostics: {
    rmsDbfs: -30,
    peakDbfs: -20,
    sampleRate: 48000,
    device: "test",
    calibrationHash: null,
    calibrationSerial: null,
    sensitivityFactor: null,
    framesProcessed: 4800,
    inputAgeSeconds: 0,
    referenceOffsetDb: null,
  },
  measured: null,
  estimatedAudience: null,
  spectrum: { centresHz: [], levelsDb: [], unit: "dBFS", method: "FFT" },
  alarms: [],
  eventId: null,
  peakHold: "since input start/reset",
};
const settings = {
  mode: "demo",
  device: "",
  channel: 0,
  sampleRate: 48000,
  wavPath: "",
  calibrationText: "",
  referenceDb: null,
  referenceRmsDbfs: null,
  referenceNote: "",
  fieldTrimDb: 0,
  lasThreshold: null,
  leqThreshold: null,
  peakThreshold: null,
  venueName: "",
  audienceOffsetDb: null,
};

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("WebSocket", MockWebSocket);
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string) => ({
      ok: true,
      json: async () =>
        path.endsWith("/config")
          ? settings
          : path.endsWith("/devices")
            ? { devices: [], error: null }
            : path.endsWith("/current")
              ? null
              : [],
    })),
  );
});
afterEach(() => {
  cleanup();
  MockWebSocket.instances = [];
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

async function mount() {
  await act(async () => {
    render(<App />);
  });
}
function receive(value: unknown) {
  act(() =>
    MockWebSocket.instances
      .at(-1)
      ?.onmessage?.({ data: JSON.stringify(value) }),
  );
}

describe("measurement presentation", () => {
  it("keeps uncalibrated input out of acoustic metrics", async () => {
    await mount();
    receive(frame);
    expect(screen.getByText("Live level")).toBeInTheDocument();
    expect(screen.getByText("UNCALIBRATED · UNVERIFIED")).toBeInTheDocument();
    expect(screen.getByText("-30.0")).toBeInTheDocument();
    expect(document.querySelectorAll(".meter strong")[0].textContent).toBe("—");
    expect(screen.queryByText("MOCK")).not.toBeInTheDocument();
  });
  it("shows disconnected source, stale input, clipping and logging failures together", async () => {
    await mount();
    receive({
      ...frame,
      status: {
        ...frame.status,
        connected: false,
        stale: true,
        clipping: true,
        loggingError: "Disk full",
      },
    });
    const status = document.querySelector(".strip-status")!;
    expect(status.textContent).toContain("MIC LOST");
    expect(status.textContent).toContain("STALE INPUT");
    expect(status.textContent).toContain("CLIPPING");
    expect(status.textContent).toContain("LOG FAILURE");
    expect(document.querySelector(".strip")).toHaveClass("strip--fault");
  });
  it("retains last values but marks a silent connection stale and reconnects", async () => {
    vi.useFakeTimers();
    await mount();
    receive({
      ...frame,
      measured: { lasDb: 94, laeq1Db: 93, laeq10Db: 92, lcpeakDb: 110 },
    });
    act(() => vi.advanceTimersByTime(2500));
    expect(document.querySelector(".strip-status")!.textContent).toContain(
      "STALE · LINK LOST",
    );
    expect(document.querySelector(".meter strong")!.textContent).toBe("94.0");
    act(() => vi.advanceTimersByTime(5000));
    expect(MockWebSocket.instances.length).toBeGreaterThan(1);
  });
  it("rejects malformed or unsupported telemetry", () => {
    expect(validFrame(frame)).toBe(true);
    expect(validFrame({ ...frame, schemaVersion: 1 })).toBe(false);
    expect(validFrame({ ...frame, measured: { lasDb: "100" } })).toBe(false);
    expect(validFrame({ schemaVersion: 2 })).toBe(false);
  });
  it("never conflates demonstration and microphone status", () => {
    expect(statusMessages({ ...frame, source: "demo" }, "live")).toContain(
      "DEMO",
    );
    expect(statusMessages(frame, "live")).not.toContain("DEMO");
  });
  it("labels file, reference and manual calibration distinctly", () => {
    const calibrated = { ...frame, status: { ...frame.status, calibrated: true } };
    const badge = (method: string) =>
      statusMessages(
        {
          ...calibrated,
          diagnostics: { ...frame.diagnostics, calibrationMethod: method as never },
        },
        "live",
      );
    expect(badge("umik-file")).toContain("FILE CAL");
    expect(badge("reference")).toContain("REFERENCE CAL");
    expect(badge("manual")).toContain("MANUAL CAL");
    expect(badge("manual")).not.toContain("REFERENCE CAL");
  });
});

describe("per-browser layout", () => {
  it("saves width and placement changes and supports a compact preset", async () => {
    await mount();
    fireEvent.change(screen.getByLabelText(/Horizontal position/), {
      target: { value: "80" },
    });
    fireEvent.change(screen.getByLabelText(/Height/), {
      target: { value: "80" },
    });
    expect(loadLayout().x).toBe(80);
    expect(loadLayout().height).toBe(80);
    expect(document.querySelector(".strip")).toHaveStyle({ left: "80%" });
    fireEvent.click(screen.getByText("Compact preset"));
    expect(loadLayout().height).toBe(72);
    expect(loadLayout().details).toBe(false);
  });
  it("recovers from corrupt or out-of-range saved settings", () => {
    localStorage.setItem("spl-layout-v1", "{bad");
    expect(loadLayout().height).toBe(100);
    expect(normalizeLayout({ x: 200, height: -1, width: "bad" })).toMatchObject(
      { x: 100, height: 64, width: 1280 },
    );
  });
});

it("does not treat repeated frozen frames as fresh input", async () => {
  vi.useFakeTimers();
  await mount();
  receive(frame);
  for (let i = 0; i < 6; i++) {
    act(() => vi.advanceTimersByTime(500));
    receive(frame);
  }
  expect(document.querySelector(".strip-status")!.textContent).toContain(
    "STALE · LINK LOST",
  );
});

it("shows file-calibrated SPL immediately while keeping field verification distinct", async () => {
  await mount();
  receive({
    ...frame,
    status: { ...frame.status, calibrated: true, warmupSeconds: 599 },
    diagnostics: {
      ...frame.diagnostics,
      calibrationMethod: "umik-file",
      calibrationReason: "Calibrated to supplied file",
    },
    measured: { lasDb: 74.5, laeq1Db: 74.1, laeq10Db: 74.1, lcpeakDb: 88.2 },
  });
  expect(document.querySelector(".strip-status")!.textContent).toContain(
    "FILE CAL",
  );
  expect(document.querySelector(".strip-status")!.textContent).not.toContain(
    "UNCALIBRATED",
  );
  expect(document.querySelector(".meter strong")!.textContent).toBe("74.5");
  expect(
    screen.getByText(/Full hardware validation is still pending/),
  ).toBeInTheDocument();
});

it("validates analyzer band geometry, readiness and finite powers", () => {
  const band = {
    fraction: 6,
    centresHz: [1000],
    edgesHz: [940, 1060],
    levelsDb: [80],
    smoothedLevelsDb: [79],
    windowSeconds: 1,
    ready: true,
  };
  const packet = { ...frame, spectrum: { ...frame.spectrum, bands: [band] } };
  expect(validFrame(packet)).toBe(true);
  expect(
    validFrame({
      ...packet,
      spectrum: { ...packet.spectrum, bands: [{ ...band, levelsDb: [NaN] }] },
    }),
  ).toBe(false);
  expect(
    validFrame({
      ...packet,
      spectrum: {
        ...packet.spectrum,
        bands: [{ ...band, edgesHz: [1060, 940] }],
      },
    }),
  ).toBe(false);
  expect(
    validFrame({
      ...packet,
      spectrum: {
        ...packet.spectrum,
        bands: [{ ...band, ready: false, levelsDb: [], smoothedLevelsDb: [] }],
      },
    }),
  ).toBe(true);
});

it("uses server reading location and mapping identity instead of saved browser preference", async () => {
  localStorage.setItem("spl-layout-v1", JSON.stringify({ audience: false }));
  await mount();
  const live = {
    ...frame,
    status: { ...frame.status, calibrated: true },
    measured: {
      lasDb: 75,
      lasMaxDb: 80,
      laeq1Db: 74,
      laeq10Db: 73,
      lcpeakDb: 90,
    },
    estimatedAudience: {
      lasDb: 78.6,
      lasMaxDb: 83.6,
      laeq1Db: 77.6,
      laeq10Db: 76.6,
      lcpeakDb: null,
    },
    readingLocation: {
      audience: true,
      name: "Home",
      offsetDb: 3.6,
      mappedAt: "2026-09-21T06:00:00Z",
    },
  };
  receive(live);
  expect(document.querySelector(".meter strong")?.textContent).toBe("78.6");
  expect(document.querySelector(".audience-indicator")?.textContent).toBe(
    "EST · Home",
  );
  expect(document.querySelector(".mapping-stamp")?.textContent).toContain(
    "+3.6 dB",
  );
  receive({
    ...live,
    sequence: 2,
    readingLocation: { ...live.readingLocation, audience: false },
  });
  expect(document.querySelector(".meter strong")?.textContent).toBe("75.0");
  receive({ ...live, sequence: 3, estimatedAudience: null });
  expect(document.querySelector(".meter strong")?.textContent).toBe("—");
});

it("sorts saved mappings and confirms deletion of an inactive mapping", async () => {
  const items = [
    { id: "a", name: "Z Hall", offsetDb: 3, mappedAt: "2026-09-21T06:00:00Z" },
    { id: "b", name: "A Room", offsetDb: -2, mappedAt: "2026-09-20T06:00:00Z" },
  ];
  const fallback = globalThis.fetch;
  const requests: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string, options?: RequestInit) => {
      if (path === "/api/audience-mappings")
        return { ok: true, json: async () => items };
      if (options?.method === "DELETE") {
        requests.push(path);
        return { ok: true, json: async () => ({}) };
      }
      return fallback(path, options);
    }),
  );
  await mount();
  receive({
    ...frame,
    readingLocation: {
      mappingId: "a",
      audience: true,
      name: "Z Hall",
      offsetDb: 3,
      mappedAt: items[0].mappedAt,
    },
  });
  await act(async () => {});
  const chooser = screen.getByLabelText(
    "Saved audience mappings",
  ) as HTMLSelectElement;
  expect(chooser.options[1].value).toBe("a");
  fireEvent.change(screen.getByLabelText("Sort mappings"), {
    target: { value: "name" },
  });
  expect(chooser.options[1].value).toBe("b");
  fireEvent.change(screen.getByLabelText("Sort mappings"), {
    target: { value: "oldest" },
  });
  expect(chooser.options[1].value).toBe("b");
  expect(
    screen.getByRole("button", { name: "Delete selected mapping" }),
  ).toBeDisabled();
  fireEvent.change(chooser, { target: { value: "b" } });
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  fireEvent.click(
    screen.getByRole("button", { name: "Delete selected mapping" }),
  );
  expect(requests).toEqual([]);
  confirm.mockReturnValue(true);
  await act(async () => {
    fireEvent.click(
      screen.getByRole("button", { name: "Delete selected mapping" }),
    );
  });
  expect(requests).toEqual(["/api/audience-mappings/b"]);
  confirm.mockRestore();
});

it("clears the loaded mapping through the shared API", async () => {
  await mount();
  receive({
    ...frame,
    readingLocation: {
      mappingId: "home",
      audience: false,
      name: "Home",
      offsetDb: 3.6,
      mappedAt: null,
    },
  });
  await act(async () => {});
  const button = screen.getByRole("button", { name: "Clear loaded mapping" });
  expect(button).toBeEnabled();
  await act(async () => {
    fireEvent.click(button);
  });
  expect(fetch).toHaveBeenCalledWith(
    "/api/audience-mapping/clear",
    expect.objectContaining({ method: "POST" }),
  );
  receive({
    ...frame,
    sequence: 2,
    readingLocation: {
      mappingId: null,
      audience: false,
      name: "",
      offsetDb: null,
      mappedAt: null,
    },
  });
  expect(button).toBeDisabled();
});

import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FirstRunBanner } from "./FirstRunBanner";

const addresses = {
  port: 8000,
  localAdmin: "http://localhost:8000/",
  localDisplay: "http://localhost:8000/display",
  lan: [
    {
      host: "192.168.1.50",
      admin: "http://192.168.1.50:8000/",
      display: "http://192.168.1.50:8000/display",
    },
  ],
  note: "Other devices only view the dashboard.",
};

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => addresses })),
  );
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("first-run banner", () => {
  it("shows the LAN /display URL, a QR code and the disclaimer", async () => {
    await act(async () => {
      render(<FirstRunBanner calibrated={false} />);
    });
    const link = await screen.findByRole("link", {
      name: "http://192.168.1.50:8000/display",
    });
    expect(link).toHaveAttribute("href", "http://192.168.1.50:8000/display");
    expect(
      screen.getByText(/not a compliance meter/i),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(document.querySelector(".first-run-qr svg")).toBeTruthy(),
    );
  });

  it("cannot be dismissed while uncalibrated", async () => {
    await act(async () => {
      render(<FirstRunBanner calibrated={false} />);
    });
    expect(screen.getByRole("button", { name: "Dismiss" })).toBeDisabled();
  });

  it("stays hidden after dismissal once calibrated", async () => {
    const { rerender } = render(<FirstRunBanner calibrated={true} />);
    await act(async () => {});
    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByText(/Open the dashboard on your iPad/)).toBeNull();
    // Persisted dismissal keeps it hidden while calibrated.
    rerender(<FirstRunBanner calibrated={true} />);
    expect(screen.queryByText(/Open the dashboard on your iPad/)).toBeNull();
  });

  it("reappears when the app is not yet calibrated even after dismissal", async () => {
    localStorage.setItem("spl-firstrun-dismissed-v1", "1");
    await act(async () => {
      render(<FirstRunBanner calibrated={false} />);
    });
    expect(
      screen.getByText(/Open the dashboard on your iPad/),
    ).toBeInTheDocument();
  });
});

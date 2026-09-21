import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { api } from "./api";
import { DISCLAIMER } from "./disclaimer";
import type { Addresses } from "./types";

const DISMISS_KEY = "spl-firstrun-dismissed-v1";

// The setup banner helps an operator open the strip on an iPad and reminds them
// what the app is (and is not). It can be dismissed once calibration is applied;
// while the app is uncalibrated it stays visible regardless of dismissal.
export function FirstRunBanner({ calibrated }: { calibrated: boolean }) {
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem(DISMISS_KEY) === "1";
    } catch {
      return false;
    }
  });
  const [addresses, setAddresses] = useState<Addresses | null>(null);
  const [qr, setQr] = useState("");

  useEffect(() => {
    let cancelled = false;
    void api<Addresses>("/addresses")
      .then((value) => {
        if (!cancelled && value && Array.isArray(value.lan)) setAddresses(value);
      })
      .catch(() => {
        /* Connection status is shown elsewhere. */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const displayUrl =
    addresses?.lan?.[0]?.display ?? addresses?.localDisplay ?? "";

  useEffect(() => {
    if (!displayUrl) {
      setQr("");
      return;
    }
    let cancelled = false;
    void QRCode.toString(displayUrl, { type: "svg", margin: 1 })
      .then((svg) => {
        if (!cancelled) setQr(svg);
      })
      .catch(() => {
        if (!cancelled) setQr("");
      });
    return () => {
      cancelled = true;
    };
  }, [displayUrl]);

  if (dismissed && calibrated) return null;

  const dismiss = () => {
    try {
      localStorage.setItem(DISMISS_KEY, "1");
    } catch {
      /* Dismissal is best-effort. */
    }
    setDismissed(true);
  };

  const lan = addresses?.lan ?? [];

  return (
    <section className="card first-run" aria-label="Getting started">
      <div className="section-line">
        <h2>Open the dashboard on your iPad</h2>
        <button
          type="button"
          className="first-run-dismiss"
          onClick={dismiss}
          disabled={!calibrated}
          title={
            calibrated
              ? "Hide this banner"
              : "This stays until a calibration is applied"
          }
        >
          Dismiss
        </button>
      </div>
      <p className="muted">
        This app runs here, on the computer with the microphone. On your iPad,
        phone or laptop, open one of these addresses in a browser — nothing is
        installed on those devices; they only view the dashboard.
      </p>
      <div className="first-run-body">
        <div className="first-run-urls">
          {lan.length ? (
            <ul>
              {lan.map((entry) => (
                <li key={entry.host}>
                  <a href={entry.display}>{entry.display}</a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">
              No network address detected yet. Connect this computer to your
              Wi-Fi, then reload. On this computer you can open{" "}
              <a href={addresses?.localDisplay ?? "/display"}>
                {addresses?.localDisplay ?? "/display"}
              </a>
              .
            </p>
          )}
        </div>
        {qr && (
          <div
            className="first-run-qr"
            aria-label={`QR code for ${displayUrl}`}
            role="img"
            dangerouslySetInnerHTML={{ __html: qr }}
          />
        )}
      </div>
      <p className="disclaimer" role="note">
        {DISCLAIMER}
      </p>
    </section>
  );
}

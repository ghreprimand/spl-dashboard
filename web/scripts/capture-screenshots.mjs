// Regenerate the documentation screenshots with a headless browser.
//
// Spawns the SPL Dashboard service against the freshly built web/dist (using the
// generated demonstration source), captures the key UI at a fixed window size,
// and writes PNGs into docs/screenshots/. Run it via `make screenshots`.
//
// Lives under web/ so it can import Playwright from web/node_modules.
// Requires: a built web/dist (npm run build), the server venv, and Playwright's
// chromium (`npx playwright install chromium`).

import { spawn } from "node:child_process";
import { mkdtempSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as sleep } from "node:timers/promises";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, "..", "..");
const webDist = join(repo, "web", "dist");
const outDir = join(repo, "docs", "screenshots");
const port = Number(process.env.SPL_SHOT_PORT ?? 8010);
const base = `http://127.0.0.1:${port}`;
const python =
  process.env.SPL_PYTHON ?? join(repo, "server", ".venv", "bin", "python");
const viewport = { width: 1180, height: 900 };

mkdirSync(outDir, { recursive: true });
const dataDir = mkdtempSync(join(tmpdir(), "spl-shots-"));

async function waitForHealth(timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`${base}/api/health`);
      if (r.ok) return;
    } catch {
      /* not up yet */
    }
    await sleep(300);
  }
  throw new Error("Server did not become healthy in time");
}

const server = spawn(
  python,
  [
    "-m",
    "uvicorn",
    "spl_dashboard.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    String(port),
  ],
  {
    cwd: repo,
    env: { ...process.env, SPL_WEB_DIST: webDist, SPL_DATA_DIR: dataDir },
    stdio: "inherit",
  },
);

async function shot(page, selector, name) {
  const el = page.locator(selector).first();
  await el.waitFor({ state: "visible", timeout: 10000 });
  await el.screenshot({ path: join(outDir, name) });
  console.log("wrote", join("docs/screenshots", name));
}

let browser;
try {
  await waitForHealth();
  browser = await chromium.launch();
  const context = await browser.newContext({ viewport, deviceScaleFactor: 2 });
  const page = await context.newPage();

  // Admin console: first-run banner, input & calibration, event log.
  await page.goto(`${base}/`, { waitUntil: "networkidle" });
  await sleep(3500); // let demo telemetry populate
  await shot(page, ".first-run", "first-run.png");
  await shot(
    page,
    "form.card:has(h2:text('Input & calibration'))",
    "input-calibration.png",
  );
  await shot(page, "section.card:has(h2:text('Event log'))", "event-log.png");

  // Strip display: the strip and the spectrum analyzer.
  await page.goto(`${base}/display`, { waitUntil: "networkidle" });
  await sleep(3500);
  await shot(page, ".strip", "strip.png");
  await page.locator(".spectrum-button").first().click();
  await sleep(1500);
  await shot(page, ".analyzer-dialog", "spectrum.png");

  console.log("Screenshots complete.");
} finally {
  if (browser) await browser.close();
  server.kill("SIGTERM");
  await sleep(500);
  try {
    rmSync(dataDir, { recursive: true, force: true });
  } catch {
    /* best effort */
  }
}

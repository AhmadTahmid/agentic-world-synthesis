import { spawn } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { chromium } from "playwright-core";

const root = resolve(import.meta.dirname, "..");
const output = resolve(root, "..", "generated", "hybrid-evaluation");
mkdirSync(output, { recursive: true });

const browserCandidates = [
  process.env.WORLDSYNTH_BROWSER,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
].filter(Boolean);
const executablePath = browserCandidates.find((candidate) => existsSync(candidate));
if (!executablePath) throw new Error("No Chrome/Edge executable found. Set WORLDSYNTH_BROWSER to a Chromium-family browser.");

const viteEntry = resolve(root, "node_modules", "vite", "bin", "vite.js");
const server = spawn(process.execPath, [viteEntry, "--host", "127.0.0.1", "--port", "4173", "--strictPort"], { cwd: root, stdio: ["ignore", "pipe", "pipe"] });
let serverLog = "";
server.stdout.on("data", (chunk) => { serverLog += chunk.toString(); });
server.stderr.on("data", (chunk) => { serverLog += chunk.toString(); });

async function waitForServer() {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      const response = await fetch("http://127.0.0.1:4173/");
      if (response.ok) return;
    } catch { /* server is still starting */ }
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 250));
  }
  throw new Error(`Vite did not start.\n${serverLog}`);
}

let browser;
try {
  await waitForServer();
  browser = await chromium.launch({
    executablePath,
    headless: true,
    args: ["--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist", "--disable-gpu-sandbox"],
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));
  const presets = ["forest-arrival", "bridge-reveal", "lodge-meadow", "reactive-grass", "semantic-debug"];
  const metricsByPreset = {};
  let scatter;
  let assetStats;
  for (const preset of presets) {
    await page.goto(`http://127.0.0.1:4173/?preset=${encodeURIComponent(preset)}&capture=1`, { waitUntil: "networkidle" });
    await page.waitForFunction(() => window.__WORLD_READY__ === true, null, { timeout: 30_000 });
    await page.waitForTimeout(1400);
    await page.screenshot({ path: resolve(output, `${preset}.png`) });
    metricsByPreset[preset] = await page.evaluate(() => window.__WORLD_DEBUG__?.getMetrics());
    scatter = await page.evaluate(() => window.__WORLD_DEBUG__?.getScatterManifest());
    assetStats = await page.evaluate(() => window.__WORLD_DEBUG__?.getAssetStats());
  }
  await page.goto("http://127.0.0.1:4173/?preset=forest-arrival&capture=1", { waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__WORLD_READY__ === true, null, { timeout: 30_000 });
  const beforeMove = await page.evaluate(() => window.__WORLD_DEBUG__?.getMetrics().playerPosition);
  await page.keyboard.down("w");
  await page.waitForTimeout(650);
  await page.keyboard.up("w");
  const afterMove = await page.evaluate(() => window.__WORLD_DEBUG__?.getMetrics().playerPosition);
  const movementDistance = Math.hypot(afterMove[0] - beforeMove[0], afterMove[1] - beforeMove[1]);
  const interactionSmoke = { beforeMove, afterMove, movementDistance, passed: movementDistance > 0.1 };
  if (!interactionSmoke.passed) throw new Error("Keyboard smoke failed: the player did not move");
  await page.keyboard.press("b");
  await page.waitForTimeout(600);
  await page.screenshot({ path: resolve(output, "asset-browser.png") });
  writeFileSync(resolve(output, "performance.json"), `${JSON.stringify({ renderer: "Chrome headless SwiftShader", viewport: [1440, 900], presets: metricsByPreset }, null, 2)}\n`);
  writeFileSync(resolve(output, "interaction-smoke.json"), `${JSON.stringify(interactionSmoke, null, 2)}\n`);
  writeFileSync(resolve(output, "scatter-manifest.json"), `${JSON.stringify(scatter, null, 2)}\n`);
  writeFileSync(resolve(output, "asset-inventory.json"), `${JSON.stringify(assetStats, null, 2)}\n`);
  writeFileSync(resolve(output, "browser-console.json"), `${JSON.stringify({ errors }, null, 2)}\n`);
  if (errors.length > 0) throw new Error(`Browser console errors:\n${errors.join("\n")}`);
  console.log(`Captured ${presets.length} deterministic views to ${output}`);
  console.log(JSON.stringify(metricsByPreset["bridge-reveal"]));
} finally {
  if (browser) await browser.close();
  server.kill();
}

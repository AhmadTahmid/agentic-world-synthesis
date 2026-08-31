import "./styles/main.css";
import { Clock } from "three";
import { loadWorldContracts } from "./core/WorldLoader";
import { WebGLRendererAdapter } from "./core/RendererAdapter";
import { WorldRuntime } from "./core/WorldRuntime";
import { PerformanceOverlay } from "./debug/PerformanceOverlay";

async function boot(): Promise<void> {
  const canvas = document.querySelector<HTMLCanvasElement>("#world");
  const performanceElement = document.querySelector<HTMLElement>("#performance");
  const loading = document.querySelector<HTMLElement>("#loading");
  if (!canvas || !performanceElement || !loading) throw new Error("Application shell is incomplete");
  const { world, registry } = await loadWorldContracts();
  const renderer = new WebGLRendererAdapter(canvas, world.lighting.exposure);
  renderer.resize(window.innerWidth, window.innerHeight, devicePixelRatio);
  const runtime = await WorldRuntime.create(world, registry, renderer);
  const performance = new PerformanceOverlay(performanceElement, renderer.renderer, () => {
    const metrics = runtime.metrics();
    return {
      visibleObjects: Number(metrics.visibleObjects),
      instancedObjects: Number(metrics.instancedObjects),
      scatterInstances: Number(metrics.scatterInstances),
      collisionShapes: Number(metrics.collisionShapes),
    };
  });
  window.addEventListener("resize", () => {
    renderer.resize(window.innerWidth, window.innerHeight, devicePixelRatio);
    runtime.resize(window.innerWidth, window.innerHeight);
  });
  const params = new URLSearchParams(window.location.search);
  const preset = params.get("preset");
  if (params.get("capture") === "1" && preset !== "forest-arrival") document.body.classList.add("capture-clean");
  if (preset) runtime.applyCapturePreset(preset);
  const clock = new Clock();
  const frame = (): void => {
    const delta = Math.min(clock.getDelta(), 0.05);
    runtime.update(delta);
    runtime.render();
    performance.update(delta);
    requestAnimationFrame(frame);
  };
  frame();
  loading.classList.add("done");
  window.setTimeout(() => loading.remove(), 700);
  window.__WORLD_DEBUG__ = {
    applyCapturePreset: (name) => runtime.applyCapturePreset(name),
    getMetrics: () => ({ ...runtime.metrics(), ...performance.snapshot() }),
    getScatterManifest: () => runtime.scatterManifest(),
    getAssetStats: () => runtime.assetStats(),
    setInspectorVisible: (visible) => runtime.inspector.setSemanticPreset(visible),
  };
  window.__WORLD_READY__ = true;
}

void boot().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  document.body.innerHTML = `<main class="fatal"><h1>World load failed</h1><pre>${message}</pre><p>Check the WorldSpec and asset registry paths.</p></main>`;
  console.error(error);
});

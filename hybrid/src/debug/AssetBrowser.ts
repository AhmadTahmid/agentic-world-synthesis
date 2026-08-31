import * as THREE from "three";
import type { AssetLoader } from "../core/AssetLoader";
import type { AssetEntry, AssetRegistrySpec } from "../domain/schema";

export class AssetBrowser {
  private readonly renderer: THREE.WebGLRenderer;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(32, 440 / 320, 0.01, 100);
  private current?: THREE.Object3D;
  private visible = false;

  constructor(private readonly element: HTMLElement, private readonly loader: AssetLoader, registry: AssetRegistrySpec) {
    const canvas = element.querySelector<HTMLCanvasElement>("#asset-preview");
    const list = element.querySelector<HTMLElement>("#asset-list");
    if (!canvas || !list) throw new Error("Asset browser DOM is incomplete");
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.setSize(440, 320, false);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.1;
    this.scene.background = new THREE.Color(0x182821);
    this.scene.add(new THREE.HemisphereLight(0xddeee1, 0x3b463c, 2.2));
    const sun = new THREE.DirectionalLight(0xffe0a6, 3);
    sun.position.set(-4, 7, 5);
    this.scene.add(sun);
    this.camera.position.set(5, 4, 7);
    this.camera.lookAt(0, 1, 0);
    list.innerHTML = `<header><div><span class="eyebrow">Registered vocabulary</span><h2>Asset Browser</h2></div><button data-close>×</button></header>${registry.assets.map((asset) => `<button class="asset-row" data-asset="${asset.id}"><span class="asset-type">${asset.type}</span><strong>${asset.id}</strong><small>${asset.tags.slice(0, 3).join(" · ")}</small></button>`).join("")}`;
    list.querySelectorAll<HTMLButtonElement>("[data-asset]").forEach((button) => button.addEventListener("click", () => void this.select(button.dataset.asset ?? "")));
    list.querySelector("[data-close]")?.addEventListener("click", () => this.setVisible(false));
    window.addEventListener("keydown", (event) => {
      if (event.code === "KeyB" && !event.repeat) this.setVisible(!this.visible);
    });
  }

  async select(id: string): Promise<void> {
    const entry = this.loader.getEntry(id);
    const [{ object }, stats] = await Promise.all([this.loader.spawn(id, [0, 0]), this.loader.stats(id)]);
    if (this.current) this.scene.remove(this.current);
    this.current = object;
    this.scene.add(object);
    const bounds = new THREE.Box3().setFromObject(object);
    const size = bounds.getSize(new THREE.Vector3());
    const center = bounds.getCenter(new THREE.Vector3());
    const radius = Math.max(size.x, size.y, size.z);
    this.camera.position.set(center.x + radius * 1.35, center.y + radius * 0.9, center.z + radius * 1.55);
    this.camera.lookAt(center);
    const source = this.loader.registry.sources[entry.source];
    const metadata = this.element.querySelector<HTMLElement>("#asset-metadata");
    if (metadata) metadata.innerHTML = `<h3>${entry.id}</h3><dl><dt>Type</dt><dd>${entry.type}</dd><dt>Tags</dt><dd>${entry.tags.join(", ")}</dd><dt>Measured bounds</dt><dd>${stats.dimensions.map((value) => value.toFixed(2)).join(" × ")}</dd><dt>Meshes / materials</dt><dd>${stats.meshes} / ${stats.materials}</dd><dt>Triangles</dt><dd>${stats.triangles.toLocaleString()}</dd><dt>File</dt><dd>${(stats.bytes / 1024).toFixed(1)} KB</dd><dt>Animation clips</dt><dd>${stats.animations.join(", ") || "none"}</dd><dt>Source</dt><dd><a href="${source?.source ?? "#"}" target="_blank">${source?.creator ?? entry.source}</a></dd><dt>License</dt><dd>${entry.licenseMetadata.license}</dd><dt>Collision</dt><dd>${entry.collision.type}</dd></dl>`;
    this.element.querySelectorAll(".asset-row").forEach((row) => row.classList.toggle("selected", (row as HTMLElement).dataset.asset === id));
  }

  update(delta: number): void {
    if (!this.visible) return;
    if (this.current) this.current.rotation.y += delta * 0.35;
    this.renderer.render(this.scene, this.camera);
  }

  setVisible(visible: boolean): void {
    this.visible = visible;
    this.element.classList.toggle("open", visible);
    if (visible && !this.current) void this.select(this.loader.registry.assets[0]?.id ?? "");
  }
}

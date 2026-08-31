import * as THREE from "three";

export interface RuntimeCounts {
  visibleObjects: number;
  instancedObjects: number;
  scatterInstances: number;
  collisionShapes: number;
}

export class PerformanceOverlay {
  private elapsed = 0;
  private frames = 0;
  private fps = 0;

  constructor(private readonly element: HTMLElement, private readonly renderer: THREE.WebGLRenderer, private readonly counts: () => RuntimeCounts) {}

  update(delta: number): void {
    this.elapsed += delta;
    this.frames += 1;
    if (this.elapsed < 0.4) return;
    this.fps = this.frames / this.elapsed;
    this.elapsed = 0;
    this.frames = 0;
    const info = this.renderer.info;
    const counts = this.counts();
    this.element.innerHTML = `<strong>${this.fps.toFixed(0)} FPS</strong><span>${info.render.calls} draws</span><span>${info.render.triangles.toLocaleString()} tris</span><span>${counts.visibleObjects} visible</span><span>${counts.instancedObjects.toLocaleString()} instanced</span><span>${counts.collisionShapes} collision shapes</span>`;
  }

  snapshot(): Record<string, number> {
    const info = this.renderer.info;
    return { fps: Number(this.fps.toFixed(1)), drawCalls: info.render.calls, triangles: info.render.triangles, ...this.counts() };
  }
}

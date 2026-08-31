import * as THREE from "three";

export interface RendererAdapter {
  readonly renderer: THREE.WebGLRenderer;
  resize(width: number, height: number, pixelRatio: number): void;
  render(scene: THREE.Scene, camera: THREE.Camera): void;
}

export class WebGLRendererAdapter implements RendererAdapter {
  readonly renderer: THREE.WebGLRenderer;

  constructor(canvas: HTMLCanvasElement, exposure: number) {
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance", alpha: false });
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = exposure;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  }

  resize(width: number, height: number, pixelRatio: number): void {
    this.renderer.setPixelRatio(Math.min(pixelRatio, 1.75));
    this.renderer.setSize(width, height, false);
  }

  render(scene: THREE.Scene, camera: THREE.Camera): void {
    this.renderer.render(scene, camera);
  }
}

import * as THREE from "three";
import type { WorldSpec } from "../domain/schema";

export class LightingSystem {
  readonly group = new THREE.Group();
  readonly sun: THREE.DirectionalLight;

  constructor(scene: THREE.Scene, world: WorldSpec) {
    scene.background = new THREE.Color(world.lighting.sky);
    scene.fog = new THREE.FogExp2(world.lighting.sky, world.lighting.fogDensity);
    const hemisphere = new THREE.HemisphereLight(world.lighting.sky, world.lighting.ground, 1.7);
    hemisphere.name = "soft-sky-fill";
    this.group.add(hemisphere);
    this.sun = new THREE.DirectionalLight(world.lighting.sun, world.lighting.sunIntensity);
    this.sun.name = "northwest-sun";
    const radius = 42;
    this.sun.position.set(
      Math.cos(world.lighting.azimuth) * radius,
      Math.sin(world.lighting.elevation) * radius,
      Math.sin(world.lighting.azimuth) * radius,
    );
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.camera.left = -38;
    this.sun.shadow.camera.right = 38;
    this.sun.shadow.camera.top = 42;
    this.sun.shadow.camera.bottom = -42;
    this.sun.shadow.camera.near = 2;
    this.sun.shadow.camera.far = 110;
    this.sun.shadow.bias = -0.00045;
    this.sun.shadow.normalBias = 0.025;
    this.group.add(this.sun, this.sun.target);
    scene.add(this.group);
  }

  setShadows(enabled: boolean): void {
    this.sun.castShadow = enabled;
  }
}

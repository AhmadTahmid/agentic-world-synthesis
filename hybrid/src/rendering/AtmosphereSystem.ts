import * as THREE from "three";
import type { WorldSpec } from "../domain/schema";
import { seededRandom } from "../generation/random";

export class AtmosphereSystem {
  readonly points: THREE.Points;
  private readonly origins: Float32Array;

  constructor(private readonly world: WorldSpec) {
    const count = world.atmosphere.particleCount;
    const positions = new Float32Array(count * 3);
    const random = seededRandom(world.metadata.seed, "atmospheric-pollen");
    for (let index = 0; index < count; index += 1) {
      positions[index * 3] = (random() - 0.5) * world.grid.width;
      positions[index * 3 + 1] = 0.8 + random() * 8;
      positions[index * 3 + 2] = (random() - 0.5) * world.grid.height;
    }
    this.origins = positions.slice();
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const material = new THREE.PointsMaterial({
      color: world.atmosphere.particleColor,
      size: 0.075,
      transparent: true,
      opacity: 0.66,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    this.points = new THREE.Points(geometry, material);
    this.points.name = "floating-pollen";
    this.points.frustumCulled = false;
  }

  update(time: number): void {
    const positions = this.points.geometry.getAttribute("position") as THREE.BufferAttribute;
    for (let index = 0; index < positions.count; index += 1) {
      const x = this.origins[index * 3] ?? 0;
      const y = this.origins[index * 3 + 1] ?? 0;
      const z = this.origins[index * 3 + 2] ?? 0;
      positions.setXYZ(index, x + Math.sin(time * 0.22 + z) * 0.8, y + Math.sin(time * 0.7 + x) * 0.22, z + Math.cos(time * 0.18 + x) * 0.55);
    }
    positions.needsUpdate = true;
  }

  setEnabled(enabled: boolean): void {
    this.points.visible = enabled;
  }
}

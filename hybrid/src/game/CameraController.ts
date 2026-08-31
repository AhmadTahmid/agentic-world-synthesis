import * as THREE from "three";
import type { Vec2, WorldSpec } from "../domain/schema";

export class CameraController {
  readonly camera: THREE.OrthographicCamera;
  private target = new THREE.Vector3();
  private forcedTarget: THREE.Vector3 | undefined;
  private aspect = 1;

  constructor(private readonly world: WorldSpec) {
    this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 180);
    this.camera.name = "jrpg-orthographic-camera";
    this.resize(window.innerWidth, window.innerHeight);
  }

  resize(width: number, height: number): void {
    this.aspect = width / Math.max(1, height);
    const vertical = this.world.camera.zoom;
    this.camera.left = -vertical * this.aspect;
    this.camera.right = vertical * this.aspect;
    this.camera.top = vertical;
    this.camera.bottom = -vertical;
    this.camera.updateProjectionMatrix();
  }

  update(player: THREE.Vector3, delta: number, immediate = false): void {
    const halfWidth = this.world.grid.width / 2;
    const halfHeight = this.world.grid.height / 2;
    const source = this.forcedTarget ?? new THREE.Vector3(player.x, 0, player.z + this.world.camera.lookAhead);
    source.x = THREE.MathUtils.clamp(source.x, -halfWidth + 12, halfWidth - 12);
    source.z = THREE.MathUtils.clamp(source.z, -halfHeight + 12, halfHeight - 12);
    const alpha = immediate ? 1 : 1 - Math.exp(-this.world.camera.followSmoothing * delta);
    this.target.lerp(source, alpha);
    const distance = 31;
    const horizontal = Math.cos(this.world.camera.pitch) * distance;
    const offset = new THREE.Vector3(
      Math.sin(this.world.camera.yaw) * horizontal,
      Math.sin(this.world.camera.pitch) * distance,
      Math.cos(this.world.camera.yaw) * horizontal,
    );
    this.camera.position.copy(this.target).add(offset);
    this.camera.lookAt(this.target);
  }

  setTarget(target?: Vec2): void {
    this.forcedTarget = target ? new THREE.Vector3(target[0], 0, target[1]) : undefined;
  }
}

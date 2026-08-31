import * as THREE from "three";
import type { Vec2, WorldSpec } from "../domain/schema";
import type { AssetLoader } from "../core/AssetLoader";
import type { CollisionSystem } from "./CollisionSystem";

export class PlayerController {
  readonly object: THREE.Group;
  private readonly mixer: THREE.AnimationMixer;
  private readonly actions: THREE.AnimationAction[];
  private activeAction?: THREE.AnimationAction;
  private readonly keys = new Set<string>();
  private moving = false;

  private constructor(object: THREE.Group, clips: THREE.AnimationClip[], private readonly world: WorldSpec, private readonly collision: CollisionSystem) {
    this.object = object;
    this.object.name = "player-wayfarer";
    this.mixer = new THREE.AnimationMixer(object);
    this.actions = clips.map((clip) => this.mixer.clipAction(clip));
    this.playAnimation(false);
    window.addEventListener("keydown", (event) => this.keys.add(event.code));
    window.addEventListener("keyup", (event) => this.keys.delete(event.code));
  }

  static async create(loader: AssetLoader, world: WorldSpec, collision: CollisionSystem): Promise<PlayerController> {
    const spawned = await loader.spawn(world.player.asset, world.player.spawn, 0, 1);
    return new PlayerController(spawned.object, spawned.animations, world, collision);
  }

  update(delta: number): void {
    const x = (this.keys.has("KeyD") || this.keys.has("ArrowRight") ? 1 : 0) - (this.keys.has("KeyA") || this.keys.has("ArrowLeft") ? 1 : 0);
    const z = (this.keys.has("KeyS") || this.keys.has("ArrowDown") ? 1 : 0) - (this.keys.has("KeyW") || this.keys.has("ArrowUp") ? 1 : 0);
    const length = Math.hypot(x, z);
    const isMoving = length > 0;
    if (isMoving) {
      const pace = this.keys.has("ShiftLeft") || this.keys.has("ShiftRight") ? 0.55 : 1;
      const step = this.world.player.speed * pace * delta;
      const dx = x / length * step;
      const dz = z / length * step;
      const radius = this.world.player.radius;
      const xTarget: Vec2 = [this.object.position.x + dx, this.object.position.z];
      if (!this.collision.isBlocked(xTarget, radius)) this.object.position.x = xTarget[0];
      const zTarget: Vec2 = [this.object.position.x, this.object.position.z + dz];
      if (!this.collision.isBlocked(zTarget, radius)) this.object.position.z = zTarget[1];
      const desiredRotation = Math.atan2(x, z);
      this.object.rotation.y = THREE.MathUtils.lerp(this.object.rotation.y, desiredRotation, Math.min(1, delta * 13));
    }
    if (isMoving !== this.moving) {
      this.moving = isMoving;
      this.playAnimation(isMoving);
    }
    this.mixer.update(delta * (isMoving ? 1.25 : 1));
  }

  setPosition(position: Vec2): void {
    this.object.position.x = position[0];
    this.object.position.z = position[1];
  }

  getPosition(): Vec2 {
    return [this.object.position.x, this.object.position.z];
  }

  private playAnimation(moving: boolean): void {
    if (this.actions.length === 0) return;
    const preferred = this.actions.find((action) => {
      const name = action.getClip().name.toLowerCase();
      return moving ? name.includes("walk") || name.includes("run") : name.includes("idle");
    }) ?? this.actions[moving && this.actions.length > 1 ? 1 : 0];
    if (!preferred || preferred === this.activeAction) return;
    preferred.reset().fadeIn(0.18).play();
    this.activeAction?.fadeOut(0.18);
    this.activeAction = preferred;
  }
}

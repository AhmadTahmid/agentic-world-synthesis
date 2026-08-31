import * as THREE from "three";
import type { AssetRegistrySpec, Placement, Vec2, WorldSpec } from "../domain/schema";
import { AssetLoader } from "./AssetLoader";
import { ScatterSystem, type ScatterInstance } from "../generation/ScatterSystem";
import { TerrainRenderer } from "../rendering/TerrainRenderer";
import { LightingSystem } from "../rendering/LightingSystem";
import { AtmosphereSystem } from "../rendering/AtmosphereSystem";
import { CollisionSystem } from "../game/CollisionSystem";
import { PlayerController } from "../game/PlayerController";
import { CameraController } from "../game/CameraController";
import { DebugOverlay } from "../debug/DebugOverlay";
import { WorldInspector, type InspectorState } from "../debug/WorldInspector";
import { AssetBrowser } from "../debug/AssetBrowser";
import type { RendererAdapter } from "./RendererAdapter";

export class WorldRuntime {
  readonly scene = new THREE.Scene();
  readonly assetLoader: AssetLoader;
  readonly terrain: TerrainRenderer;
  readonly lighting: LightingSystem;
  readonly atmosphere: AtmosphereSystem;
  readonly camera: CameraController;
  readonly player: PlayerController;
  readonly collision: CollisionSystem;
  readonly inspector: WorldInspector;
  readonly assetBrowser: AssetBrowser;
  readonly debug: DebugOverlay;
  private scatter: ScatterInstance[];
  private scatterGroup = new THREE.Group();
  private readonly authoredGroup = new THREE.Group();
  private scatterOffset = 0;
  private elapsed = 0;
  private interactionText = "";

  private constructor(readonly world: WorldSpec, readonly registry: AssetRegistrySpec, private readonly renderer: RendererAdapter, assetLoader: AssetLoader, terrain: TerrainRenderer, lighting: LightingSystem, atmosphere: AtmosphereSystem, camera: CameraController, player: PlayerController, collision: CollisionSystem, scatter: ScatterInstance[], debug: DebugOverlay, inspector: WorldInspector, assetBrowser: AssetBrowser) {
    this.assetLoader = assetLoader;
    this.terrain = terrain;
    this.lighting = lighting;
    this.atmosphere = atmosphere;
    this.camera = camera;
    this.player = player;
    this.collision = collision;
    this.scatter = scatter;
    this.debug = debug;
    this.inspector = inspector;
    this.assetBrowser = assetBrowser;
  }

  static async create(world: WorldSpec, registry: AssetRegistrySpec, renderer: RendererAdapter): Promise<WorldRuntime> {
    const scene = new THREE.Scene();
    const loader = new AssetLoader(registry);
    const referenced = [world.player.asset, ...world.landmarks.map((item) => item.asset), ...world.objects.map((item) => item.asset), ...world.scatterRules.flatMap((rule) => rule.assetSet)];
    await loader.preload(referenced);
    const scatter = new ScatterSystem(world, registry).generate();
    const collision = new CollisionSystem(world, registry, scatter);
    const terrain = new TerrainRenderer(world);
    const lighting = new LightingSystem(scene, world);
    const atmosphere = new AtmosphereSystem(world);
    const camera = new CameraController(world);
    const player = await PlayerController.create(loader, world, collision);
    scene.add(terrain.group, atmosphere.points, player.object);
    const debug = new DebugOverlay(world, collision.shapes, scatter);
    scene.add(debug.group);
    const inspectorElement = document.querySelector<HTMLElement>("#inspector");
    const assetBrowserElement = document.querySelector<HTMLElement>("#asset-browser");
    if (!inspectorElement || !assetBrowserElement) throw new Error("Developer UI containers are missing");
    let runtime: WorldRuntime;
    const inspector = new WorldInspector(inspectorElement, (state) => runtime.applyInspector(state), () => void runtime.regenerateScatter());
    const assetBrowser = new AssetBrowser(assetBrowserElement, loader, registry);
    runtime = new WorldRuntime(world, registry, renderer, loader, terrain, lighting, atmosphere, camera, player, collision, scatter, debug, inspector, assetBrowser);
    runtime.scene.copy(scene, false);
    while (scene.children.length > 0) runtime.scene.add(scene.children[0]!);
    runtime.authoredGroup.name = "authored-composition-anchors";
    runtime.scatterGroup.name = "seeded-procedural-decoration";
    runtime.scene.add(runtime.authoredGroup, runtime.scatterGroup);
    await Promise.all([
      runtime.spawnAuthored([...world.landmarks, ...world.objects]),
      runtime.spawnScatter(scatter),
    ]);
    runtime.addLanternLights();
    runtime.camera.update(runtime.player.object.position, 1, true);
    return runtime;
  }

  update(delta: number): void {
    this.elapsed += delta;
    this.player.update(delta);
    this.camera.update(this.player.object.position, delta);
    this.terrain.update(this.elapsed);
    this.atmosphere.update(this.elapsed);
    this.assetLoader.reactiveUniforms.time.value = this.elapsed;
    this.assetLoader.reactiveUniforms.player.value.copy(this.player.object.position);
    this.assetBrowser.update(delta);
    this.updateInteraction();
  }

  render(): void {
    this.renderer.render(this.scene, this.camera.camera);
  }

  resize(width: number, height: number): void {
    this.camera.resize(width, height);
  }

  applyCapturePreset(name: string): void {
    const preset = this.world.capturePresets[name];
    if (!preset) throw new Error(`Unknown capture preset '${name}'`);
    this.player.setPosition(preset.player);
    this.camera.setTarget(preset.cameraTarget);
    this.camera.update(this.player.object.position, 1, true);
    this.inspector.setSemanticPreset(preset.inspector);
  }

  metrics(): Record<string, unknown> {
    let visibleObjects = 0;
    let instancedObjects = 0;
    this.scene.traverseVisible((object) => {
      visibleObjects += 1;
      if (object instanceof THREE.InstancedMesh) instancedObjects += object.count;
    });
    return {
      worldId: this.world.metadata.id,
      seed: this.world.metadata.seed,
      scatterInstances: this.scatter.length,
      collisionShapes: this.collision.shapes.length,
      playerPosition: this.player.getPosition(),
      visibleObjects,
      instancedObjects,
      drawCalls: this.renderer.renderer.info.render.calls,
      triangles: this.renderer.renderer.info.render.triangles,
    };
  }

  scatterManifest(): unknown {
    return { formatVersion: 1, worldId: this.world.metadata.id, seed: this.world.metadata.seed + this.scatterOffset, instances: this.scatter };
  }

  async assetStats(): Promise<Record<string, unknown>> {
    return Object.fromEntries(await Promise.all(this.registry.assets.map(async (asset) => [asset.id, await this.assetLoader.stats(asset.id)])));
  }

  private async spawnAuthored(placements: Placement[]): Promise<void> {
    await Promise.all(placements.map(async (placement) => {
      const spawned = await this.assetLoader.spawn(placement.asset, placement.position, placement.rotation, placement.scale);
      spawned.object.name = placement.id;
      spawned.object.userData.semanticRole = placement.semanticRole;
      spawned.object.userData.interaction = placement.interaction;
      this.authoredGroup.add(spawned.object);
    }));
  }

  private async spawnScatter(scatter: ScatterInstance[]): Promise<void> {
    const byAsset = new Map<string, ScatterInstance[]>();
    scatter.forEach((placement) => byAsset.set(placement.asset, [...(byAsset.get(placement.asset) ?? []), placement]));
    const groups = await Promise.all([...byAsset].map(([id, placements]) => this.assetLoader.createInstances(id, placements, id === "grass.tall.01")));
    groups.forEach((group) => this.scatterGroup.add(group));
  }

  private async regenerateScatter(): Promise<void> {
    if (!this.inspector.state.freezeRandomness) this.scatterOffset += 1;
    const next = new ScatterSystem(this.world, this.registry, this.scatterOffset).generate();
    const replacement = new THREE.Group();
    replacement.name = "seeded-procedural-decoration";
    const previous = this.scatterGroup;
    this.scatterGroup = replacement;
    this.scene.add(replacement);
    await this.spawnScatter(next);
    this.scene.remove(previous);
    previous.traverse((object) => {
      if (object instanceof THREE.InstancedMesh) {
        object.geometry.dispose();
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        materials.forEach((material) => material.dispose());
      }
    });
    this.scatter = next;
    this.collision.rebuild(next);
    this.debug.rebuild(this.collision.shapes, next);
    this.applyInspector(this.inspector.state);
  }

  private applyInspector(state: InspectorState): void {
    const anySemantic = state.logicalGrid || state.collisions || state.zones || state.spawnPoints || state.footprints;
    this.debug.group.visible = anySemantic;
    this.debug.grid.visible = state.logicalGrid;
    this.debug.collisions.visible = state.collisions || state.footprints;
    this.debug.zones.visible = state.zones;
    this.debug.spawnPoints.visible = state.spawnPoints;
    this.scatterGroup.visible = state.vegetation;
    this.renderer.renderer.shadowMap.enabled = state.shadows;
    this.lighting.setShadows(state.shadows);
    this.atmosphere.setEnabled(state.particles);
    document.body.classList.toggle("show-asset-ids", state.assetIds);
  }

  private addLanternLights(): void {
    this.world.objects.filter((placement) => placement.asset === "prop.lantern.01").forEach((placement) => {
      const light = new THREE.PointLight(0xffc56b, 4.2, 8, 2);
      light.position.set(placement.position[0], 2.1, placement.position[1]);
      light.name = `warm-light:${placement.id}`;
      this.scene.add(light);
    });
  }

  private updateInteraction(): void {
    const player = this.player.getPosition();
    let closest: Placement | undefined;
    let closestDistance = 3;
    [...this.world.landmarks, ...this.world.objects].forEach((placement) => {
      if (!placement.interaction) return;
      const distance = Math.hypot(player[0] - placement.position[0], player[1] - placement.position[1]);
      if (distance < closestDistance) { closest = placement; closestDistance = distance; }
    });
    const text = closest?.interaction ? `E · ${closest.interaction}` : "";
    if (text === this.interactionText) return;
    this.interactionText = text;
    const element = document.querySelector<HTMLElement>("#interaction");
    if (element) { element.textContent = text; element.classList.toggle("visible", Boolean(text)); }
  }
}

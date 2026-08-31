import * as THREE from "three";
import { GLTFLoader, type GLTF } from "three/examples/jsm/loaders/GLTFLoader.js";
import { clone as cloneSkeleton } from "three/examples/jsm/utils/SkeletonUtils.js";
import type { AssetEntry, AssetRegistrySpec, Vec2 } from "../domain/schema";
import type { ScatterInstance } from "../generation/ScatterSystem";

export interface AssetStats {
  triangles: number;
  meshes: number;
  materials: number;
  dimensions: [number, number, number];
  bytes: number;
  animations: string[];
}

interface LoadedAsset {
  gltf: GLTF;
  stats: AssetStats;
}

export interface ReactiveUniforms {
  time: { value: number };
  player: { value: THREE.Vector3 };
  wind: { value: THREE.Vector2 };
}

export class AssetLoader {
  private readonly loader = new GLTFLoader();
  private readonly entries: Map<string, AssetEntry>;
  private readonly cache = new Map<string, Promise<LoadedAsset>>();
  readonly reactiveUniforms: ReactiveUniforms = {
    time: { value: 0 },
    player: { value: new THREE.Vector3() },
    wind: { value: new THREE.Vector2(0.7, 0.25) },
  };

  constructor(readonly registry: AssetRegistrySpec) {
    this.entries = new Map(registry.assets.map((entry) => [entry.id, entry]));
  }

  getEntry(id: string): AssetEntry {
    const entry = this.entries.get(id);
    if (!entry) throw new Error(`Asset registry has no entry '${id}'`);
    return entry;
  }

  async preload(ids: Iterable<string>): Promise<void> {
    await Promise.all([...new Set(ids)].map((id) => this.load(id)));
  }

  async load(id: string): Promise<LoadedAsset> {
    const cached = this.cache.get(id);
    if (cached) return cached;
    const entry = this.getEntry(id);
    const promise = (async () => {
      const paths = [entry.path, ...(entry.parts?.map((part) => part.path) ?? [])];
      const bundles = await Promise.all(paths.map(async (path) => {
        const [gltf, bytes] = await Promise.all([
          this.loader.loadAsync(path),
          fetch(path).then(async (response) => {
            if (!response.ok) throw new Error(`Missing asset ${entry.id}: ${path}`);
            return (await response.arrayBuffer()).byteLength;
          }),
        ]);
        return { gltf, bytes };
      }));
      const primary = bundles[0];
      if (!primary) throw new Error(`Asset ${entry.id} has no loadable path`);
      let gltf = primary.gltf;
      if (entry.parts && entry.parts.length > 0) {
        const composite = new THREE.Group();
        composite.name = `${entry.id}:prefab`;
        composite.add(cloneSkeleton(primary.gltf.scene));
        entry.parts.forEach((part, index) => {
          const source = bundles[index + 1];
          if (!source) return;
          const object = cloneSkeleton(source.gltf.scene);
          object.position.set(...part.position);
          object.rotation.set(...part.rotation);
          object.scale.set(...part.scale);
          composite.add(object);
        });
        gltf = { ...primary.gltf, scene: composite, scenes: [composite], animations: bundles.flatMap((bundle) => bundle.gltf.animations) };
      }
      const bytes = bundles.reduce((total, bundle) => total + bundle.bytes, 0);
      gltf.scene.updateMatrixWorld(true);
      const bounds = new THREE.Box3().setFromObject(gltf.scene);
      const size = bounds.getSize(new THREE.Vector3());
      let triangles = 0;
      let meshes = 0;
      const materials = new Set<THREE.Material>();
      gltf.scene.traverse((object) => {
        if (!(object instanceof THREE.Mesh)) return;
        meshes += 1;
        const geometry = object.geometry;
        triangles += geometry.index ? geometry.index.count / 3 : (geometry.getAttribute("position")?.count ?? 0) / 3;
        const meshMaterials = Array.isArray(object.material) ? object.material : [object.material];
        meshMaterials.forEach((material) => materials.add(material));
        object.castShadow = entry.castShadow;
        object.receiveShadow = entry.receiveShadow;
      });
      return {
        gltf,
        stats: {
          triangles: Math.round(triangles),
          meshes,
          materials: materials.size,
          dimensions: [size.x, size.y, size.z] as [number, number, number],
          bytes,
          animations: gltf.animations.map((clip) => clip.name || "unnamed"),
        },
      };
    })();
    this.cache.set(id, promise);
    return promise;
  }

  async spawn(id: string, position: Vec2, rotation = 0, placementScale = 1): Promise<{ object: THREE.Group; animations: THREE.AnimationClip[] }> {
    const entry = this.getEntry(id);
    const loaded = await this.load(id);
    const object = cloneSkeleton(loaded.gltf.scene) as THREE.Group;
    object.name = id;
    const axis = entry.axisScale ?? [1, 1, 1];
    object.scale.set(entry.scale * placementScale * axis[0], entry.scale * placementScale * axis[1], entry.scale * placementScale * axis[2]);
    object.rotation.y = rotation;
    object.position.set(position[0], 0, position[1]);
    object.updateMatrixWorld(true);
    const bounds = new THREE.Box3().setFromObject(object);
    object.position.y -= bounds.min.y;
    object.userData.assetId = id;
    object.userData.assetEntry = entry;
    return { object, animations: loaded.gltf.animations };
  }

  async createInstances(id: string, placements: ScatterInstance[], reactive = false): Promise<THREE.Group> {
    const entry = this.getEntry(id);
    const loaded = await this.load(id);
    const template = loaded.gltf.scene;
    template.updateMatrixWorld(true);
    const meshes: THREE.Mesh[] = [];
    template.traverse((object) => {
      if (object instanceof THREE.Mesh) meshes.push(object);
    });
    const baked = meshes.map((mesh) => {
      const geometry = mesh.geometry.clone();
      geometry.applyMatrix4(mesh.matrixWorld);
      return { geometry, material: mesh.material };
    });
    const combinedBounds = new THREE.Box3();
    baked.forEach(({ geometry }) => {
      geometry.computeBoundingBox();
      if (geometry.boundingBox) combinedBounds.union(geometry.boundingBox);
    });
    const groundOffset = -combinedBounds.min.y;
    const group = new THREE.Group();
    group.name = `instances:${id}`;
    group.userData.assetId = id;
    group.userData.instanceCount = placements.length;
    const dummy = new THREE.Object3D();
    for (const { geometry, material } of baked) {
      geometry.translate(0, groundOffset, 0);
      const sourceMaterial = Array.isArray(material) ? material[0] : material;
      if (!sourceMaterial) continue;
      const renderMaterial = reactive ? this.makeReactiveMaterial(sourceMaterial) : sourceMaterial.clone();
      const instances = new THREE.InstancedMesh(geometry, renderMaterial, placements.length);
      instances.name = `${id}:batch`;
      instances.castShadow = entry.castShadow;
      instances.receiveShadow = entry.receiveShadow;
      placements.forEach((placement, index) => {
        const scale = entry.scale * placement.scale;
        const axis = entry.axisScale ?? [1, 1, 1];
        dummy.position.set(placement.position[0], 0, placement.position[1]);
        dummy.rotation.set(0, placement.rotation, 0);
        dummy.scale.set(scale * axis[0], scale * axis[1], scale * axis[2]);
        dummy.updateMatrix();
        instances.setMatrixAt(index, dummy.matrix);
      });
      instances.instanceMatrix.needsUpdate = true;
      instances.computeBoundingSphere();
      group.add(instances);
    }
    return group;
  }

  private makeReactiveMaterial(source: THREE.Material): THREE.Material {
    const material = source.clone();
    if (material instanceof THREE.MeshStandardMaterial) {
      material.color.set(0x68a84f);
      material.emissive.set(0x173c20);
      material.emissiveIntensity = 0.12;
      material.roughness = 0.92;
      material.side = THREE.DoubleSide;
    }
    material.onBeforeCompile = (shader) => {
      shader.uniforms.uGrassTime = this.reactiveUniforms.time;
      shader.uniforms.uPlayerPosition = this.reactiveUniforms.player;
      shader.uniforms.uWind = this.reactiveUniforms.wind;
      shader.vertexShader = shader.vertexShader
        .replace(
          "#include <common>",
          `#include <common>
uniform float uGrassTime;
uniform vec3 uPlayerPosition;
uniform vec2 uWind;`,
        )
        .replace(
          "#include <begin_vertex>",
          `vec3 transformed = vec3(position);
#ifdef USE_INSTANCING
  vec3 grassRoot = (modelMatrix * instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
#else
  vec3 grassRoot = (modelMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
#endif
float bladeHeight = clamp(position.y / 0.25, 0.0, 1.0);
vec2 away = grassRoot.xz - uPlayerPosition.xz;
float playerDistance = length(away);
float playerBend = smoothstep(2.8, 0.15, playerDistance) * bladeHeight;
vec2 awayDirection = playerDistance > 0.01 ? normalize(away) : vec2(1.0, 0.0);
float windWave = sin(uGrassTime * 1.65 + grassRoot.x * 0.74 + grassRoot.z * 0.51) * 0.11 * bladeHeight;
transformed.xz += awayDirection * playerBend * 0.72 + normalize(uWind + vec2(0.001)) * windWave;`,
        );
    };
    material.customProgramCacheKey = () => "worldsynth-reactive-grass-v1";
    return material;
  }

  async stats(id: string): Promise<AssetStats> {
    return (await this.load(id)).stats;
  }
}

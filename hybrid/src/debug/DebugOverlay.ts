import * as THREE from "three";
import type { Vec2, WorldSpec } from "../domain/schema";
import type { ScatterInstance } from "../generation/ScatterSystem";
import type { CollisionShape } from "../game/CollisionSystem";

function lineFromPolygon(points: Vec2[], color: number, y = 0.32): THREE.Line {
  const positions = points.flatMap((point) => [point[0], y, point[1]]);
  const first = points[0];
  if (first) positions.push(first[0], y, first[1]);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  return new THREE.Line(geometry, new THREE.LineBasicMaterial({ color, depthTest: false, transparent: true, opacity: 0.86 }));
}

export class DebugOverlay {
  readonly group = new THREE.Group();
  readonly grid = new THREE.Group();
  readonly collisions = new THREE.Group();
  readonly zones = new THREE.Group();
  readonly spawnPoints = new THREE.Group();
  readonly assetFootprints = new THREE.Group();

  constructor(private readonly world: WorldSpec, shapes: CollisionShape[], scatter: ScatterInstance[]) {
    this.group.name = "semantic-debug-overlay";
    this.group.renderOrder = 100;
    this.buildGrid();
    this.buildZones();
    this.buildCollisions(shapes);
    this.buildScatterPoints(scatter);
    this.group.add(this.grid, this.collisions, this.zones, this.spawnPoints, this.assetFootprints);
    this.group.visible = false;
  }

  rebuild(shapes: CollisionShape[], scatter: ScatterInstance[]): void {
    this.collisions.clear();
    this.spawnPoints.clear();
    this.buildCollisions(shapes);
    this.buildScatterPoints(scatter);
  }

  private buildGrid(): void {
    const size = Math.max(this.world.grid.width, this.world.grid.height);
    const helper = new THREE.GridHelper(size, size / this.world.grid.cellSize, 0x31566a, 0x4e776e);
    helper.position.y = 0.26;
    (helper.material as THREE.Material).depthTest = false;
    this.grid.add(helper);
  }

  private buildZones(): void {
    this.world.zones.forEach((zone, index) => {
      const palette = [0xf2c94c, 0x6fcf97, 0x56ccf2, 0xbb6bd9, 0xf2994a];
      const line = lineFromPolygon(zone.polygon, palette[index % palette.length] ?? 0xffffff, 0.35);
      line.name = `zone:${zone.id}`;
      this.zones.add(line);
    });
  }

  private buildCollisions(shapes: CollisionShape[]): void {
    const material = new THREE.MeshBasicMaterial({ color: 0xf04452, transparent: true, opacity: 0.3, depthTest: false, side: THREE.DoubleSide });
    shapes.forEach((shape) => {
      let mesh: THREE.Mesh;
      if (shape.type === "circle") {
        mesh = new THREE.Mesh(new THREE.CircleGeometry(shape.radius, 18), material);
      } else {
        mesh = new THREE.Mesh(new THREE.PlaneGeometry(shape.rect.size[0], shape.rect.size[1]), material);
        mesh.rotation.z = -shape.rect.rotation;
      }
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.set(shape.type === "circle" ? shape.center[0] : shape.rect.center[0], 0.3, shape.type === "circle" ? shape.center[1] : shape.rect.center[1]);
      mesh.name = `collision:${shape.source}`;
      this.collisions.add(mesh);
    });
  }

  private buildScatterPoints(scatter: ScatterInstance[]): void {
    const positions = scatter.flatMap((placement) => [placement.position[0], 0.42, placement.position[1]]);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    const material = new THREE.PointsMaterial({ color: 0xff8a3d, size: 0.16, depthTest: false });
    const points = new THREE.Points(geometry, material);
    points.name = "procedural-spawn-points";
    this.spawnPoints.add(points);
  }
}

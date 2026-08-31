import { distance, distanceToPolyline, pointInRotatedRect } from "../domain/geometry";
import type { AssetEntry, AssetRegistrySpec, Rect, Vec2, WorldSpec } from "../domain/schema";
import type { ScatterInstance } from "../generation/ScatterSystem";

export type CollisionShape =
  | { type: "circle"; center: Vec2; radius: number; source: string }
  | { type: "box"; rect: Rect; source: string };

function rotateSize(size: Vec2, rotation: number): Vec2 {
  const quarterTurns = Math.round(Math.abs(rotation) / (Math.PI / 2)) % 2;
  return quarterTurns === 1 ? [size[1], size[0]] : size;
}

export class CollisionSystem {
  readonly shapes: CollisionShape[] = [];
  private readonly assets: Map<string, AssetEntry>;

  constructor(private readonly world: WorldSpec, registry: AssetRegistrySpec, scatter: ScatterInstance[]) {
    this.assets = new Map(registry.assets.map((asset) => [asset.id, asset]));
    this.rebuild(scatter);
  }

  rebuild(scatter: ScatterInstance[]): void {
    this.shapes.length = 0;
    this.world.blockers.forEach((rect, index) => this.shapes.push({ type: "box", rect, source: `world-blocker:${index}` }));
    [...this.world.landmarks, ...this.world.objects].forEach((placement) => this.addAssetCollision(placement.asset, placement.position, placement.rotation, placement.scale, placement.id));
    scatter.forEach((placement) => this.addAssetCollision(placement.asset, placement.position, placement.rotation, placement.scale, placement.id));
  }

  isBlocked(point: Vec2, radius: number): boolean {
    const halfWidth = this.world.grid.width * this.world.grid.cellSize / 2;
    const halfHeight = this.world.grid.height * this.world.grid.cellSize / 2;
    if (Math.abs(point[0]) > halfWidth - radius || Math.abs(point[1]) > halfHeight - radius) return true;
    const inBridge = this.world.bridgeCrossings.some((rect) => pointInRotatedRect(point, rect, radius * 0.3));
    if (!inBridge && this.world.waterBodies.some((water) => water.blocked && distanceToPolyline(point, water.centerline) < water.width / 2 + radius)) return true;
    return this.shapes.some((shape) => {
      if (shape.type === "circle") return distance(point, shape.center) < shape.radius + radius;
      return pointInRotatedRect(point, shape.rect, radius);
    });
  }

  private addAssetCollision(id: string, position: Vec2, rotation: number, placementScale: number, source: string): void {
    const asset = this.assets.get(id);
    if (!asset || asset.collision.type === "none") return;
    const scale = asset.scale * placementScale;
    if (asset.collision.type === "circle") {
      this.shapes.push({ type: "circle", center: position, radius: asset.collision.radius * scale, source });
    } else {
      this.shapes.push({
        type: "box",
        rect: { center: position, size: rotateSize([asset.collision.size[0] * scale, asset.collision.size[1] * scale], rotation), rotation },
        source,
      });
    }
  }
}

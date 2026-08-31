import { distance, distanceToPolyline, distanceToSegment, pointInPolygon, pointInRotatedRect, polygonBounds } from "../domain/geometry";
import type { AssetEntry, AssetRegistrySpec, ScatterRule, Vec2, WorldSpec, Zone } from "../domain/schema";
import { seededRandom } from "./random";

export interface ScatterInstance {
  id: string;
  ruleId: string;
  asset: string;
  position: Vec2;
  rotation: number;
  scale: number;
}

function distanceToPolygonEdge(point: Vec2, polygon: Vec2[]): number {
  let result = Number.POSITIVE_INFINITY;
  for (let index = 0; index < polygon.length; index += 1) {
    const next = (index + 1) % polygon.length;
    const start = polygon[index];
    const end = polygon[next];
    if (start && end) result = Math.min(result, distanceToSegment(point, start, end));
  }
  return result;
}

function randomPoint(zone: Zone, random: () => number): Vec2 {
  const bounds = polygonBounds(zone.polygon);
  return [
    bounds.min[0] + random() * (bounds.max[0] - bounds.min[0]),
    bounds.min[1] + random() * (bounds.max[1] - bounds.min[1]),
  ];
}

function collisionRadius(asset: AssetEntry | undefined): number {
  if (!asset || asset.collision.type === "none") return 0;
  if (asset.collision.type === "circle") return asset.collision.radius;
  return Math.max(asset.collision.size[0], asset.collision.size[1]) / 2;
}

export class ScatterSystem {
  private readonly assets: Map<string, AssetEntry>;

  constructor(private readonly world: WorldSpec, registry: AssetRegistrySpec, private readonly seedOffset = 0) {
    this.assets = new Map(registry.assets.map((asset) => [asset.id, asset]));
  }

  generate(): ScatterInstance[] {
    return this.world.scatterRules.flatMap((rule) => this.generateRule(rule));
  }

  private generateRule(rule: ScatterRule): ScatterInstance[] {
    const zone = this.world.zones.find((candidate) => candidate.id === rule.zone);
    if (!zone) throw new Error(`Scatter rule ${rule.id} references missing zone ${rule.zone}`);
    const random = seededRandom(this.world.metadata.seed + this.seedOffset, rule.id);
    const target = Math.max(0, Math.round(rule.maxInstances * rule.density));
    const instances: ScatterInstance[] = [];
    const clusterCount = Math.max(2, Math.round(2 + rule.clustering * 8));
    const clusterCenters: Vec2[] = [];
    while (clusterCenters.length < clusterCount) {
      const point = randomPoint(zone, random);
      if (pointInPolygon(point, zone.polygon)) clusterCenters.push(point);
    }
    const maxAttempts = Math.max(target * 42, 100);
    for (let attempt = 0; attempt < maxAttempts && instances.length < target; attempt += 1) {
      let point = randomPoint(zone, random);
      if (rule.clustering > 0 && random() < rule.clustering) {
        const center = clusterCenters[Math.floor(random() * clusterCenters.length)];
        if (center) {
          const radius = 1.5 + (1 - rule.clustering) * 8;
          const angle = random() * Math.PI * 2;
          const spread = Math.sqrt(random()) * radius;
          point = [center[0] + Math.cos(angle) * spread, center[1] + Math.sin(angle) * spread];
        }
      }
      if (!pointInPolygon(point, zone.polygon)) continue;
      if (rule.edgeSoftness && rule.edgeSoftness > 0) {
        const edgeDistance = distanceToPolygonEdge(point, zone.polygon);
        const normalized = Math.min(1, edgeDistance / rule.edgeSoftness);
        const featheredAcceptance = normalized * normalized * (3 - 2 * normalized);
        if (random() > featheredAcceptance) continue;
      }
      if (!this.matchesBias(point, zone, rule, random)) continue;
      const asset = rule.assetSet[Math.floor(random() * rule.assetSet.length)];
      if (!asset) continue;
      const radius = Math.max(rule.minSpacing, collisionRadius(this.assets.get(asset)));
      if (instances.some((placed) => distance(point, placed.position) < radius + rule.minSpacing * 0.35)) continue;
      if (this.isAvoided(point, rule, radius)) continue;
      instances.push({
        id: `${rule.id}:${instances.length.toString().padStart(4, "0")}`,
        ruleId: rule.id,
        asset,
        position: [Number(point[0].toFixed(4)), Number(point[1].toFixed(4))],
        rotation: Number((rule.rotationRange[0] + random() * (rule.rotationRange[1] - rule.rotationRange[0])).toFixed(5)),
        scale: Number((rule.scaleRange[0] + random() * (rule.scaleRange[1] - rule.scaleRange[0])).toFixed(5)),
      });
    }
    return instances;
  }

  private matchesBias(point: Vec2, zone: Zone, rule: ScatterRule, random: () => number): boolean {
    if (rule.edgeBias === "none") return true;
    if (rule.edgeBias === "forest") {
      const edgeDistance = distanceToPolygonEdge(point, zone.polygon);
      return random() < Math.max(0.28, 1 - edgeDistance / 13);
    }
    const water = this.world.waterBodies[0];
    if (!water) return false;
    const centerDistance = distanceToPolyline(point, water.centerline);
    const shoreDistance = Math.abs(centerDistance - water.width / 2);
    return shoreDistance <= water.bankWidth + 1.3 && random() < Math.max(0.22, 1 - shoreDistance / (water.bankWidth + 1.3));
  }

  private isAvoided(point: Vec2, rule: ScatterRule, radius: number): boolean {
    const padding = rule.avoidanceRadius + radius;
    if (rule.avoidTags.includes("path") && this.world.paths.some((path) => distanceToPolyline(point, path.points) <= path.width / 2 + padding)) return true;
    if (rule.avoidTags.includes("player-corridor") && this.world.paths.some((path) => distanceToPolyline(point, path.points) <= path.width / 2 + padding + 1.8)) return true;
    if (rule.avoidTags.includes("water") && this.world.waterBodies.some((water) => distanceToPolyline(point, water.centerline) <= water.width / 2 + padding)) return true;
    if (rule.avoidTags.includes("bridge") && this.world.bridgeCrossings.some((rect) => pointInRotatedRect(point, rect, padding))) return true;
    if (rule.avoidTags.includes("building")) {
      for (const placement of this.world.landmarks) {
        const asset = this.assets.get(placement.asset);
        if (!asset || asset.type !== "building" && !asset.tags.includes("building")) continue;
        const buildingRadius = collisionRadius(asset) * placement.scale * asset.scale;
        if (distance(point, placement.position) <= buildingRadius + padding) return true;
      }
    }
    return false;
  }
}

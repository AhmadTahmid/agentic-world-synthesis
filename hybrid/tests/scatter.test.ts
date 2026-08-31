import { describe, expect, it } from "vitest";
import registryPayload from "../public/data/asset-registry.json";
import worldPayload from "../public/data/willowwater-way.world.json";
import { distanceToPolyline, pointInPolygon, pointInRotatedRect } from "../src/domain/geometry";
import { AssetRegistrySchema, WorldSpecSchema } from "../src/domain/schema";
import { ScatterSystem } from "../src/generation/ScatterSystem";

const registry = AssetRegistrySchema.parse(registryPayload);
const world = WorldSpecSchema.parse(worldPayload);

describe("seeded scatter grammar", () => {
  it("is reproducible and seed-offset sensitive", () => {
    const first = new ScatterSystem(world, registry).generate();
    const second = new ScatterSystem(world, registry).generate();
    const revised = new ScatterSystem(world, registry, 1).generate();
    expect(second).toEqual(first);
    expect(revised).not.toEqual(first);
    expect(first.length).toBeGreaterThan(900);
    expect(first.length).toBeLessThan(1600);
  });

  it("keeps every derived placement inside its authored semantic zone", () => {
    const zones = new Map(world.zones.map((zone) => [zone.id, zone]));
    const rules = new Map(world.scatterRules.map((rule) => [rule.id, rule]));
    for (const placement of new ScatterSystem(world, registry).generate()) {
      const rule = rules.get(placement.ruleId)!;
      expect(pointInPolygon(placement.position, zones.get(rule.zone)!.polygon), placement.id).toBe(true);
    }
  });

  it("enforces path, water, and bridge protection declared by rules", () => {
    const rules = new Map(world.scatterRules.map((rule) => [rule.id, rule]));
    for (const placement of new ScatterSystem(world, registry).generate()) {
      const rule = rules.get(placement.ruleId)!;
      if (rule.avoidTags.includes("path")) {
        for (const path of world.paths) {
          expect(distanceToPolyline(placement.position, path.points), `${placement.id} overlaps ${path.id}`).toBeGreaterThan(path.width / 2 + rule.avoidanceRadius);
        }
      }
      if (rule.avoidTags.includes("water")) {
        for (const water of world.waterBodies) {
          expect(distanceToPolyline(placement.position, water.centerline), `${placement.id} overlaps ${water.id}`).toBeGreaterThan(water.width / 2 + rule.avoidanceRadius);
        }
      }
      if (rule.avoidTags.includes("bridge")) {
        for (const bridge of world.bridgeCrossings) expect(pointInRotatedRect(placement.position, bridge, rule.avoidanceRadius)).toBe(false);
      }
    }
  });

  it("feathers the reactive field while preserving a dense readable interior", () => {
    const grass = new ScatterSystem(world, registry).generate().filter((item) => item.ruleId === "reactive_grass");
    expect(grass.length).toBeGreaterThan(250);
    expect(grass.length).toBeLessThanOrEqual(354);
    expect(new Set(grass.map((item) => `${item.position[0]},${item.position[1]}`)).size).toBe(grass.length);
  });
});

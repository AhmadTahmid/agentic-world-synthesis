import { describe, expect, it } from "vitest";
import registryPayload from "../public/data/asset-registry.json";
import worldPayload from "../public/data/willowwater-way.world.json";
import { AssetRegistrySchema, WorldSpecSchema } from "../src/domain/schema";
import { CollisionSystem } from "../src/game/CollisionSystem";
import { ScatterSystem } from "../src/generation/ScatterSystem";

const registry = AssetRegistrySchema.parse(registryPayload);
const world = WorldSpecSchema.parse(worldPayload);
const scatter = new ScatterSystem(world, registry).generate();
const collision = new CollisionSystem(world, registry, scatter);

describe("semantic collision", () => {
  it("blocks river water but opens the declared bridge corridor", () => {
    expect(collision.isBlocked([14, -2.5], world.player.radius)).toBe(true);
    expect(collision.isBlocked([0, 0], world.player.radius)).toBe(false);
  });

  it("blocks the authored lodge footprint independently of its GLB mesh", () => {
    expect(collision.isBlocked([17, 18], world.player.radius)).toBe(true);
    expect(collision.shapes.some((shape) => shape.source === "ranger_lodge")).toBe(true);
  });

  it("does not turn decorative flowers or grass into collision", () => {
    const decorative = scatter.find((item) => item.ruleId === "meadow_flowers")!;
    expect(collision.shapes.some((shape) => shape.source === decorative.id)).toBe(false);
  });
});

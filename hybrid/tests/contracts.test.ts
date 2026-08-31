import { existsSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import registryPayload from "../public/data/asset-registry.json";
import worldPayload from "../public/data/willowwater-way.world.json";
import { AssetRegistrySchema, WorldSpecSchema, validateWorldReferences } from "../src/domain/schema";

describe("hybrid world contracts", () => {
  const registry = AssetRegistrySchema.parse(registryPayload);
  const world = WorldSpecSchema.parse(worldPayload);

  it("accepts the authored WorldSpec and registry with all references resolved", () => {
    expect(validateWorldReferences(world, registry)).toEqual([]);
    expect(world.metadata.id).toBe("willowwater_way");
    expect(registry.assets.length).toBeGreaterThan(20);
  });

  it("rejects unresolved visual vocabulary", () => {
    const broken = structuredClone(world);
    broken.landmarks[0]!.asset = "building.missing.99";
    expect(validateWorldReferences(broken, registry)).toEqual(["missing registered asset: building.missing.99"]);
  });

  it("requires valid provenance and files for every registered asset", () => {
    for (const asset of registry.assets) {
      const source = registry.sources[asset.source];
      expect(source, asset.id).toBeDefined();
      expect(source!.creator.length).toBeGreaterThan(0);
      expect(source!.license.length).toBeGreaterThan(0);
      const visual = resolve(import.meta.dirname, "..", "public", asset.path.slice(1));
      const license = resolve(import.meta.dirname, "..", "public", asset.licenseMetadata.licensePath.slice(1));
      expect(existsSync(visual), visual).toBe(true);
      expect(statSync(visual).size, visual).toBeGreaterThan(0);
      expect(existsSync(license), license).toBe(true);
    }
  });

  it("keeps real visual assets in the registry instead of authored primitive substitutes", () => {
    for (const asset of registry.assets) expect(asset.path.endsWith(".glb"), asset.id).toBe(true);
    expect(registry.assets.find((asset) => asset.id === "building.ranger-lodge.01")?.source).toBe("quaternius.medieval-village");
    expect(registry.assets.find((asset) => asset.id === "bridge.wood.01")?.axisScale).toBeUndefined();
  });
});

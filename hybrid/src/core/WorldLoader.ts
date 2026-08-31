import { AssetRegistrySchema, WorldSpecSchema, validateWorldReferences, type AssetRegistrySpec, type WorldSpec } from "../domain/schema";

async function fetchJson(path: string): Promise<unknown> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Unable to load ${path}: HTTP ${response.status}`);
  return response.json() as Promise<unknown>;
}

export async function loadWorldContracts(): Promise<{ world: WorldSpec; registry: AssetRegistrySpec }> {
  const [worldPayload, registryPayload] = await Promise.all([
    fetchJson("/data/willowwater-way.world.json"),
    fetchJson("/data/asset-registry.json"),
  ]);
  const worldResult = WorldSpecSchema.safeParse(worldPayload);
  if (!worldResult.success) throw new Error(`Malformed WorldSpec:\n${worldResult.error.message}`);
  const registryResult = AssetRegistrySchema.safeParse(registryPayload);
  if (!registryResult.success) throw new Error(`Malformed AssetRegistry:\n${registryResult.error.message}`);
  const referenceErrors = validateWorldReferences(worldResult.data, registryResult.data);
  if (referenceErrors.length > 0) throw new Error(`WorldSpec asset references failed:\n${referenceErrors.join("\n")}`);
  return { world: worldResult.data, registry: registryResult.data };
}

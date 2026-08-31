import { z } from "zod";

export const Vec2Schema = z.tuple([z.number().finite(), z.number().finite()]);
export type Vec2 = z.infer<typeof Vec2Schema>;

export const RectSchema = z.object({
  center: Vec2Schema,
  size: Vec2Schema,
  rotation: z.number().finite().default(0),
});
export type Rect = z.infer<typeof RectSchema>;

const provenanceSchema = z.object({
  creator: z.string().min(1),
  source: z.url(),
  download: z.url(),
  license: z.string().min(1),
});

const collisionSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("none") }),
  z.object({ type: z.literal("circle"), radius: z.number().positive() }),
  z.object({ type: z.literal("box"), size: Vec2Schema }),
]);
export type AssetCollision = z.infer<typeof collisionSchema>;

const prefabPartSchema = z.object({
  path: z.string().startsWith("/assets/").endsWith(".glb"),
  position: z.tuple([z.number(), z.number(), z.number()]),
  rotation: z.tuple([z.number(), z.number(), z.number()]).default([0, 0, 0]),
  scale: z.tuple([z.number().positive(), z.number().positive(), z.number().positive()]).default([1, 1, 1]),
});

export const AssetEntrySchema = z.object({
  id: z.string().regex(/^[a-z0-9]+(?:[._-][a-z0-9]+)*$/),
  type: z.enum(["tree", "vegetation", "rock", "building", "bridge", "prop", "character", "landmark"]),
  path: z.string().startsWith("/assets/").endsWith(".glb"),
  parts: z.array(prefabPartSchema).optional(),
  tags: z.array(z.string()).min(1),
  dimensions: z.tuple([z.number().positive(), z.number().positive(), z.number().positive()]),
  scale: z.number().positive(),
  axisScale: z.tuple([z.number().positive(), z.number().positive(), z.number().positive()]).optional(),
  rotationRules: z.object({
    mode: z.enum(["fixed", "cardinal", "free"]),
    values: z.array(z.number().finite()).optional(),
  }),
  collision: collisionSchema,
  instanced: z.boolean().default(false),
  castShadow: z.boolean().default(true),
  receiveShadow: z.boolean().default(true),
  lodInfo: z.object({ strategy: z.enum(["none", "distance-cull"]), maxDistance: z.number().positive().optional() }),
  source: z.string().min(1),
  licenseMetadata: z.object({ license: z.string().min(1), licensePath: z.string().min(1) }),
  preview: z.string().optional(),
});
export type AssetEntry = z.infer<typeof AssetEntrySchema>;

export const AssetRegistrySchema = z.object({
  formatVersion: z.literal(1),
  family: z.string().min(1),
  sources: z.record(z.string(), provenanceSchema),
  assets: z.array(AssetEntrySchema).min(1).superRefine((assets, ctx) => {
    const ids = new Set<string>();
    for (const asset of assets) {
      if (ids.has(asset.id)) ctx.addIssue({ code: "custom", message: `duplicate asset id: ${asset.id}` });
      ids.add(asset.id);
    }
  }),
}).superRefine((registry, ctx) => {
  for (const asset of registry.assets) {
    if (!registry.sources[asset.source]) ctx.addIssue({ code: "custom", message: `asset ${asset.id} references missing source ${asset.source}` });
  }
});
export type AssetRegistrySpec = z.infer<typeof AssetRegistrySchema>;

const pathSchema = z.object({
  id: z.string().min(1),
  points: z.array(Vec2Schema).min(2),
  width: z.number().positive(),
  material: z.string().min(1),
});

const waterSchema = z.object({
  id: z.string().min(1),
  centerline: z.array(Vec2Schema).min(2),
  width: z.number().positive(),
  blocked: z.boolean(),
  bankWidth: z.number().nonnegative(),
});

export const ZoneSchema = z.object({
  id: z.string().min(1),
  biome: z.string().min(1),
  polygon: z.array(Vec2Schema).min(3),
  tags: z.array(z.string()),
});
export type Zone = z.infer<typeof ZoneSchema>;

export const PlacementSchema = z.object({
  id: z.string().min(1),
  asset: z.string().min(1),
  position: Vec2Schema,
  rotation: z.number().finite().default(0),
  scale: z.number().positive().default(1),
  semanticRole: z.string().min(1),
  interaction: z.string().optional(),
});
export type Placement = z.infer<typeof PlacementSchema>;

export const ScatterRuleSchema = z.object({
  id: z.string().min(1),
  zone: z.string().min(1),
  assetSet: z.array(z.string()).min(1),
  density: z.number().min(0).max(1),
  maxInstances: z.number().int().positive(),
  scaleRange: z.tuple([z.number().positive(), z.number().positive()]),
  rotationRange: z.tuple([z.number().finite(), z.number().finite()]),
  clustering: z.number().min(0).max(1),
  minSpacing: z.number().nonnegative(),
  edgeBias: z.enum(["none", "forest", "water"]),
  edgeSoftness: z.number().nonnegative().optional(),
  avoidTags: z.array(z.enum(["path", "water", "building", "bridge", "player-corridor"])),
  avoidanceRadius: z.number().nonnegative(),
});
export type ScatterRule = z.infer<typeof ScatterRuleSchema>;

export const WorldSpecSchema = z.object({
  formatVersion: z.literal(1),
  metadata: z.object({
    id: z.string().min(1),
    title: z.string().min(1),
    description: z.string().min(1),
    seed: z.number().int(),
    visualIntent: z.array(z.string()).min(1),
  }),
  grid: z.object({ width: z.number().int().positive(), height: z.number().int().positive(), cellSize: z.number().positive() }),
  terrain: z.object({ base: z.string().min(1), detailScale: z.number().positive(), visualElevation: z.number().nonnegative() }),
  paths: z.array(pathSchema).min(1),
  waterBodies: z.array(waterSchema).min(1),
  zones: z.array(ZoneSchema).min(1),
  landmarks: z.array(PlacementSchema).min(1),
  objects: z.array(PlacementSchema),
  scatterRules: z.array(ScatterRuleSchema).min(1),
  blockers: z.array(RectSchema),
  bridgeCrossings: z.array(RectSchema),
  lighting: z.object({
    sky: z.string().regex(/^#[0-9a-fA-F]{6}$/),
    ground: z.string().regex(/^#[0-9a-fA-F]{6}$/),
    sun: z.string().regex(/^#[0-9a-fA-F]{6}$/),
    sunIntensity: z.number().positive(),
    azimuth: z.number().finite(),
    elevation: z.number().finite(),
    exposure: z.number().positive(),
    fogDensity: z.number().nonnegative(),
  }),
  atmosphere: z.object({
    particleCount: z.number().int().nonnegative(),
    particleColor: z.string().regex(/^#[0-9a-fA-F]{6}$/),
    wind: Vec2Schema,
  }),
  camera: z.object({
    mode: z.literal("orthographic"),
    pitch: z.number().finite(),
    yaw: z.number().finite(),
    zoom: z.number().positive(),
    followSmoothing: z.number().positive(),
    lookAhead: z.number().nonnegative(),
  }),
  player: z.object({ asset: z.string().min(1), spawn: Vec2Schema, speed: z.number().positive(), radius: z.number().positive() }),
  capturePresets: z.record(z.string(), z.object({ player: Vec2Schema, cameraTarget: Vec2Schema, inspector: z.boolean().default(false) })),
}).superRefine((world, ctx) => {
  const zoneIds = new Set(world.zones.map((zone) => zone.id));
  for (const rule of world.scatterRules) {
    if (!zoneIds.has(rule.zone)) ctx.addIssue({ code: "custom", message: `scatter ${rule.id} references missing zone ${rule.zone}` });
    if (rule.scaleRange[0] > rule.scaleRange[1]) ctx.addIssue({ code: "custom", message: `scatter ${rule.id} scaleRange is reversed` });
  }
});
export type WorldSpec = z.infer<typeof WorldSpecSchema>;

export function validateWorldReferences(world: WorldSpec, registry: AssetRegistrySpec): string[] {
  const assets = new Set(registry.assets.map((asset) => asset.id));
  const referenced = [
    world.player.asset,
    ...world.landmarks.map((item) => item.asset),
    ...world.objects.map((item) => item.asset),
    ...world.scatterRules.flatMap((rule) => rule.assetSet),
  ];
  return [...new Set(referenced.filter((id) => !assets.has(id)))].map((id) => `missing registered asset: ${id}`);
}

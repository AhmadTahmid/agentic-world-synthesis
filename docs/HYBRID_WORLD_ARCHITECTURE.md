# Hybrid World Architecture

## Why this renderer exists

The deterministic Python/Godot vertical slice proved the specification-first pipeline, but its SVG-driven presentation encouraged the authoring agent to behave like an illustrator. Willowwater Way tests a different division of labor: an agent describes composition, semantics, atmosphere, and asset vocabulary; the renderer and reusable art do the pixel-producing work.

The existing compiler and Godot client remain intact as the compatibility and gameplay-semantics reference. The hybrid prototype is deliberately a separate TypeScript/Three.js runtime until its visual and performance trade-offs are understood.

## Data flow

```text
WorldSpec JSON ─────┐
                    ├─> runtime validation ─> seeded composition ─> Three.js scene
AssetRegistry JSON ─┘          │                       │                 │
                               └─ semantic collision   └─ instances      ├─ gameplay
                                                                          ├─ inspector
                                                                          └─ captures
```

`hybrid/public/data/willowwater-way.world.json` is the meaningful scene design: logical grid, path lines, river, zones, authored landmarks, scatter profiles, blockers, bridge openings, lighting, atmosphere, player, camera, and deterministic capture presets. `hybrid/public/data/asset-registry.json` is the visual vocabulary. The runtime scene is derived and is never hand-authored as a long list of Three.js calls.

## Boundaries

- `domain/schema.ts`: runtime-checked WorldSpec and AssetRegistry contracts.
- `core/WorldLoader.ts`: loads both contracts and rejects unresolved asset IDs.
- `core/AssetLoader.ts`: caches GLB files, clones authored anchors, batches repeated meshes, and reports actual mesh statistics.
- `generation/ScatterSystem.ts`: deterministic zone sampling, clustering, spacing, edge bias/feathering, and semantic exclusions.
- `rendering/`: terrain/material blending, animated water, light, fog, tone mapping, and particles.
- `game/`: semantic collision, animated player, and smooth orthographic camera.
- `debug/`: world inspector, asset browser, semantic overlay, and live performance counters.
- `evaluation/interfaces.ts`: intentionally small future seams for scene interpretation, asset matching, planning, and visual critique.

## Simple logic, rich presentation

Gameplay remains on a flat X/Z plane. Paths and water are polylines with widths; zones are polygons; blockers and bridge crossings are explicit rectangles. A shader samples a deterministic semantic mask to blend grass, path, riverbank, and water edges, while small height variation and real GLB silhouettes create depth. Collision uses WorldSpec and registry footprints, never triangle meshes.

The foundation and water plane are allowed utility geometry. Visible trees, bridge, building, character, rocks, plants, fences, signs, stalls, and lanterns are registered models. This is the enforced distinction between renderer infrastructure and programmer art.

## Deterministic scatter

Each scatter rule is namespaced into the world seed. It specifies a zone, asset family, target density, clustering, spacing, scale/rotation range, optional edge bias/softness, and avoidance tags. Changing a meaningful rule changes derived placements; rebuilding an unchanged spec produces the same manifest. Grass and flowers therefore cost a handful of design tokens rather than one coordinate per instance.

Repeated models use `THREE.InstancedMesh`. The tall-grass material receives player position, time, and wind; vertex displacement bends nearby blades and restores them automatically. Water animation is shader time, not runtime topology.

## Renderer choice and scaling

The current adapter uses `WebGLRenderer` because GLTF loading, shadows, material hooks, and installed-browser capture are stable together. WebGPU is not a WorldSpec concern and can be evaluated behind `RendererAdapter`. The next scaling steps are spatial culling, merged multi-mesh batches, compressed textures/models, and renderer chunk splitting—not more authored coordinates.

## Future reference loop

The placeholder interfaces support a later loop:

```text
reference -> observations -> reviewed WorldSpec -> registered assets -> render
          -> deterministic screenshots -> critique -> WorldSpec revision
```

Those interfaces do not call a model and do not claim image reconstruction. Any future output must still validate through the same WorldSpec contract.

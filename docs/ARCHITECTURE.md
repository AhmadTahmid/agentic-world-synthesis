# Architecture

## Canonical data flow

```text
world_bible.yaml ─┐
world_graph.yaml ─┼─> typed source bundle ─> reference/spatial validation
asset_registry ───┤                              │
map YAML ─────────┘                              v
                                      deterministic layout generator
                                                  │
                                                  v
                                      normalized CompiledMap JSON
                                         │          │          │
                                         v          v          v
                                      validators  previews  Godot loader
```

Only `content/` and the registered assets are canonical. `generated/` is review/build output; `game/generated/` is a synchronized runtime copy. Concept images, if later added to `references/`, are evidence for a planning pass rather than gameplay truth.

## Domain boundaries

`worldsynth.domain` defines strict version-1 Pydantic models:

- `WorldBible` supplies real compiler inputs: tile scale, known terrain, biome path style/decor density, traversal, progression, and quality thresholds.
- `WorldGraph` owns map nodes, transition endpoints, danger progression, story gates, and reachability.
- `EdgeContract` makes outdoor boundary continuations mechanical rather than visual guesses.
- `AssetArchetype` binds replaceable visuals to anchors, dimensions, explicit footprints, sockets, tags, variants, animation metadata, and licensing.
- `MapSpec` keeps authored terrain rectangles, polylines, anchors, doors, zones, spawns, landmarks, constraints, and narrative readable.
- `CompiledMap` is the normalized Godot contract: raster terrain, objects, explicit collision cells, walkability rows, interactions, transitions, zones, assets, deterministic metadata, and diagnostics.

Unknown input fields are rejected. This prevents misspellings from becoming ignored author intent.

## Deterministic generation

The generator first lays authored terrain rectangles, then rasterizes Bresenham path segments and their widths. A seed may add small edge variation. It compiles explicit object footprints, protects paths/transitions/spawns/interactions/landmarks/reserved rectangles, and shuffles decoration candidates with a PRNG seeded by generator version, map ID, and effective seed. Candidates that violate bounds, spacing, blocked terrain, or protected areas are skipped.

There is no hidden topology synthesis. A new seed never moves authored transitions, structures, interactions, landmarks, or narrative anchors. Stable sorting and canonical JSON eliminate set/dictionary ordering differences. No timestamps or absolute paths enter normalized output.

Automatic constraint avoidance during optional decoration placement is generation behavior, not repair. If future code alters required authored content to repair a failure, it must append a `repair` diagnostic describing the original issue, action, and outcome.

## Validation

Validation has three layers:

1. Source/reference: schema versions, IDs, files, tile scale, graph/map parity, transition targets, edge pairs, world reachability, danger jumps, bounds, terrain/biomes, and unique landmarks.
2. Compiled spatial/playability: visual/collision bounds, collision overlap, doors/transitions/spawns in collision, object interaction references, and BFS reachability for required spawns, transitions, landmarks, interactions, and NPCs.
3. Quality warnings: open/prop density, empty space, long path segments, visual-family variety, safe/encounter overlap, landmark proximity, and building-door distance from authored routes.

Errors make the report fail and the CLI exit nonzero. Warnings require review but do not prevent a build. Reports are emitted as typed JSON and concise text.

## Godot integration

The Godot 4 runtime reads only `game/generated/world_manifest.json` and normalized map JSON. `WorldSynthMapRuntime` validates required fields, renders terrain, creates one collision shape per explicit blocked cell, loads registered SVG assets, creates transition/encounter `Area2D`s, and exposes nearest interactions. It emits helpful loader errors for absent JSON, malformed dimensions, unsupported formats, or missing textures.

Objects and the player share a `y_sort_enabled` actor layer and use ground anchors as their sort origin. A `CharacterBody2D` supplies movement/collision and owns the smooth bounded camera. The main node handles transitions, prompts, encounter notices, save state, and overlay input. Runtime code never imports Python, calls a network service, or regenerates a map.

## Provider and concept-image seams

`PlannerProvider`, `ConceptAnalyzer`, `PaletteAnalyzer`, `SegmentationProvider`, `InpaintingProvider`, `AssetGenerator`, and `MapRepairProvider` are protocols. `RuleBasedPlanner` is an offline typed test double that proves orchestration can return a `MapSpec`; its placeholder references deliberately need normal world integration before compilation. Any future LLM result is untrusted data and must pass the exact same Pydantic and semantic validators as authored YAML. Providers never write Godot code.

No reference image existed during this milestone. The future image-assisted pathway is:

1. analyze composition and palette;
2. propose terrain regions and landmarks;
3. map elements to known archetypes;
4. request human corrections;
5. compile the corrected symbolic spec;
6. optionally generate and approve new licensed assets;
7. run normal validation.

Segmentation, inpainting, palette analysis, and generation remain replaceable service interfaces. No heavyweight model dependency or checkpoint is installed.

A future planner command is intentionally reserved as:

```powershell
worldsynth plan --brief content/briefs/new_village.md --provider <provider>
```

It should write a reviewable candidate spec to a staging path, never directly to `game/`, and require normal validation/build before becoming canonical. That command is not registered in the current CLI because no live planner workflow is implemented.

## Source versus generated content

Never merge a fix made only in generated JSON. Apply it to YAML, the registry, or compiler logic and rebuild. Previews are intentionally diagnostic rather than final art. Provisional SVGs exercise replaceable asset loading while keeping gameplay semantics independent from them.

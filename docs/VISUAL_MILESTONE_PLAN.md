# Visual World Grammar and Production Renderer Plan

## Scope and baseline

This milestone changes the visual treatment of **Lanternmarket only**. Existing maps, topology, interactions, transitions, encounter semantics, walkability, and authored anchors remain intact. No LLM, generative-image service, segmentation, diffusion, battle, quest, streaming, or new-map work is in scope.

Baseline verification on 2026-08-30:

- two consecutive builds were byte-identical;
- `worldsynth build` passed with 0 errors and 0 warnings;
- 24 pytest tests, Ruff, and strict Mypy passed;
- Godot 4.7.2 smoke loaded Lanternmarket with 103 blocked cells represented by 103 shapes and 5 transitions;
- normal headless startup passed;
- live-client inspection confirmed flat-color terrain, single-layer SVG objects, a geometric player, hard terrain boundaries, and sparse uniform decoration;
- live transition inspection exposed map replacement during physics-query flushing, to be corrected with deferred loading while the runtime is being reworked.

## Contract strategy

Keep `CompiledMap.format_version` at 1 and add defaulted fields so existing v1 payloads remain loadable. Bump the generator version because canonical output changes. The semantic terrain grid, blocked cells, walkability, interactions, and transitions remain authoritative; visual tiles and merged collision rectangles are derived data.

The cardinal adjacency mask convention is `N=1`, `E=2`, `S=4`, `W=8`. A bit is set only when the in-bounds cardinal neighbor belongs to the same terrain set. Out-of-bounds neighbors are absent. Thus an isolated cell is `0`, an interior cell is `15`, and a top-left corner connected east and south is `6`.

## Implementation sequence

### 1. Semantic bug and compatibility guard

- Remove destination `transition.target_spawn` coordinates from source-map decoration protection.
- Expose derived protected visual cells for inspection.
- Add a regression test using a destination coordinate that is otherwise unprotected.
- Add a compatibility test proving a pre-visual v1 compiled payload loads with defaults.

Acceptance: destination coordinates never affect source decoration eligibility; existing required clearances still do.

### 2. Typed visual grammar

- Add terrain visual definitions with tile family/base tile, dimensions, legal neighbors, cardinal-set metadata, variants, decals, optional animation, movement/collision semantics, and license provenance.
- Add layered object visuals for shadow, base/trunk, main, and foreground/overhang roles.
- Add a data-driven directional player animation contract.
- Validate all paths, licenses, references, scales, mask coverage, and layer roles.

Acceptance: malformed masks/layers/licenses fail before compilation; all registered assets are original project CC0 work.

### 3. Deterministic visual compilation

- Compile per-cell adjacency masks and stable visual variants.
- Emit inspectable render-layer cells, protected cells, composition decisions, object variant/grammar metadata, merged collision rectangles, and render statistics.
- Replace Lanternmarket's uniform scatter with seeded vegetation clusters, edge density, roadside accents, landmark clearings, building setbacks, sightlines, and low-clutter door/intersection zones.
- Leave authored landmarks, objects, transitions, and path topology fixed.

Acceptance: repeated seeds are identical; changed seeds alter only bounded visual decisions; generated placements respect every protected cell.

### 4. Cohesive original visual pack

- Create a hand-authored CC0 SVG tile atlas for grass, cobble, dirt, water, and fallback terrain families.
- Create layered building, beacon, and tree assets with consistent northwest lighting and warm Lumenfold palette.
- Create an original four-direction idle/walk scout sheet.
- Keep existing SVGs as compatibility fallbacks.

Acceptance: provenance is recorded; no external or franchise art is introduced. Assets are polished provisional art, not claimed final production art.

### 5. Godot renderer and performance

- Make `TileMapLayer` the normal terrain path with base, transition, path, decal, and water layers.
- Keep the flat-color canvas behind an explicit diagnostic toggle only.
- Render shadows below Y-sorted structures/entities/props and overhangs above them.
- Replace per-cell physics with deterministic maximal horizontal-run rectangle merging.
- Show blocked cells, merged shape count, reduction ratio, and rendered layer/tile counts in diagnostics.
- Defer transition-driven map loads outside physics-query callbacks.

Acceptance: walkability is unchanged; Lanternmarket uses fewer collision shapes; player/tree/building depth behavior is visually demonstrable.

### 6. Showcase and review

- Add a deterministic Godot capture script that ignores saves, loads Lanternmarket near the beacon, disables overlays, and emits central-market, building-door, tree-depth, terrain-boundary, and semantic-debug screenshots.
- Add selected captures to the README.
- Inspect every capture and the Python preview for seams, missing assets, bad anchors, collision drift, and depth errors.

Acceptance: normal screenshots read as a cohesive game environment; the paired debug capture exposes the unchanged semantic system.

### 7. Verification

Run full build twice, pytest, Ruff, Mypy, Godot smoke, normal headless startup, and showcase capture. Verify canonical byte stability and inspect generated diagnostics/screenshots manually.

## Definition of done

Lanternmarket's normal renderer uses actual tile layers and cohesive original art; transitions are softened by deterministic masks; composition decisions and variants are inspectable; collision shapes are reduced without changing blocked cells; the animated player and layered tree/building depth behavior work; five reproducible captures exist; documentation is honest; and every previous and new automated check passes.

## Completion record

Completed on 2026-08-30. Lanternmarket compiles 1,120 base cells plus transition, path, decal, and water layers; 26 generated decorations are attributed to explicit grammar families. Its 105 authoritative blocked cells merge into 25 equivalent physics rectangles (4.2x reduction). The canonical hash is `b1f23826ad2906342a5b95d1c5cef520f21e9ad83ac73e95668357f7a7d214c8`.

Verification passed: byte-identical consecutive full builds, 33 pytest tests, Ruff, strict Mypy, `git diff --check`, Godot 4.7.2 editor import, dedicated headless smoke (including production tile layers, animated player, merged collision, five exterior transitions, and a deferred tavern-interior load), normal headless startup, and graphics-backed five-shot showcase capture. All five captures and the regenerated static preview were manually inspected. No missing tiles/assets, source-vs-merged collision mismatch, blocked doors, or Godot parser/runtime errors remain.

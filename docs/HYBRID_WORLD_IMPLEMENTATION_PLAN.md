# Hybrid World Visual Proof — Implementation Plan

Status: complete
Scope: one explorable route/town-edge showcase; no new open-world breadth

## Baseline and architectural decision

The Python specification-first compiler, validators, deterministic build, and Godot vertical slice remain useful and pass their existing checks. They are preserved as the semantic/compiler reference implementation. The new visual experiment is a separate Three.js/TypeScript runtime that consumes a compact, declarative `WorldSpec` plus an asset registry. This avoids destabilizing the proven compiler while testing the new renderer hypothesis directly.

The Godot SVG/TileMap renderer is now considered the legacy diagnostic presentation. It will remain runnable for compatibility, but new visible environmental art in the hybrid runtime must come from registered external models or sprites. Primitive geometry is limited to terrain foundations, water, effects, invisible collision, and debug overlays.

WebGL2 is the initial backend because its shadow, custom shader, GLTF, instancing, and headless-browser paths are mature together. Renderer construction is isolated so WebGPU can be evaluated later without making world specifications backend-specific.

## Milestones and acceptance checks

1. **Asset vocabulary**
   - Acquire one visually coherent environmental family and a compatible character asset.
   - Keep only the models used by the showcase in the runtime tree.
   - Record source URL, creator, apparent license, file size, dimensions, tags, and triangle counts.
   - Generate registry previews through the renderer; do not author replacement SVG scenery.

   Status: complete. The registered runtime vocabulary uses Kenney and Quaternius CC0 models; live previews and measured mesh metadata are available in the asset browser and capture inventory.

2. **Declarative world contract**
   - Define runtime-validated `WorldSpec` and `AssetRegistry` schemas.
   - Describe topology, landmarks, zones, scatter profiles, lighting, atmosphere, camera, and collision in data.
   - Keep authored placements limited to composition anchors; derive small decoration instances from seeded rules.

   Status: complete. Zod rejects malformed contracts and unresolved visual IDs.

3. **Rich renderer**
   - Render blended grass/path/riverbank terrain over a simple logical X/Z grid.
   - Load GLTF/GLB models through the registry; instance repeated foliage and props.
   - Add animated water, wind and player-reactive tall grass, soft shadows, fog, tone mapping, and restrained particles.
   - Compose the route around leading path lines, a bridge, cottage, meadow, river, forest framing, and two landmarks.

   Status: complete for the prototype quality bar. Terrain and water use utility shader geometry; all scenery and characters are registered GLBs.

4. **Playable systems**
   - Add deterministic player spawn, keyboard movement, semantic collision, and smooth bounded camera following.
   - Keep collision independent from visible model geometry.
   - Maintain a stable showcase camera preset for evaluation.

   Status: complete. Browser capture also performs a keyboard movement smoke check.

5. **Developer tools**
   - Add inspector toggles for terrain grid, collision, zones, footprints, spawn points, labels, vegetation, shadows, particles, and deterministic scatter regeneration.
   - Add an asset browser with live thumbnails and registry/mesh statistics.
   - Add a performance overlay for FPS, draw calls, triangles, visible objects, and instanced objects.

   Status: complete.

6. **Visual evaluation loop**
   - Provide deterministic capture presets and a command that writes multiple screenshots to `generated/hybrid-evaluation/`.
   - Inspect each capture for composition, scale, clipping, repetition, lighting, seams, and readability; revise the data or systems and recapture.
   - Keep visual screenshots out of gameplay inputs.

   Status: complete. Five scene views plus an asset-browser view are reproducible; captures are outputs only.

7. **Verification and handoff**
   - Add schema, registry, seeded scatter, exclusion, collision, and world-load tests.
   - Run TypeScript checking, tests, production build, headless browser smoke/captures, legacy Python checks, deterministic compiler build, and Godot smoke.
   - Document architecture, asset pipeline, exact commands, performance results, visual shortcomings, and next improvements.

   Status: complete. Eleven hybrid tests, TypeScript checking, production build, deterministic Chrome capture, keyboard smoke, the 33-test Python suite, Ruff, Mypy, deterministic compiler rebuild, and both Godot smoke paths pass.

## Definition of done

- The showcase is controlled by `WorldSpec`, not a placement-heavy scene script.
- It contains the requested route, river, bridge, cottage, vegetation, props, player, collision, camera, landmarks, motion, and atmosphere.
- Repeated decoration is deterministic and instanced.
- Tall grass visibly bends around the player and water visibly animates.
- The asset browser and world inspector are usable without changing source.
- Reproducible screenshots demonstrate the visual result and debug semantics.
- Both the new hybrid checks and the preserved Python/Godot checks pass.
- Documentation states plainly which visuals are provisional and what remains below the desired quality bar.

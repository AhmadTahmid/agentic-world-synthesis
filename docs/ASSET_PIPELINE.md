# Hybrid Asset Pipeline

## Storage and naming

Downloaded runtime assets live under `hybrid/public/assets/<creator>/<pack>/`. The registry uses stable semantic IDs such as `tree.oak.01`, `bridge.wood.01`, and `building.ranger-lodge.01`; scene specifications never depend on vendor filenames.

Every registry entry records type, tags, expected dimensions, presentation scale, rotation policy, semantic collision, instancing/LOD intent, source key, and license record. Source records include creator, public page, download URL, and apparent license. Actual byte size, dimensions, triangle count, material count, and animations are measured at load and written to `generated/hybrid-evaluation/asset-inventory.json`.

## Current sources

- Kenney Nature Kit: trees, grass, flowers, shrubs, rocks, fences, signs, and a waterfall. Source: <https://kenney.nl/assets/nature-kit>; CC0 1.0.
- Kenney Fantasy Town Kit: lantern, market stall, cart, and distant windmill. Source: <https://kenney.nl/assets/fantasy-town-kit>; CC0 1.0.
- Kenney Mini Characters: animated player. Source: <https://kenney.nl/assets/mini-characters>; CC0 1.0.
- Quaternius Fantasy House / Medieval Village family: ranger lodge. Source: <https://poly.pizza/m/BH2XHWUNmF>; CC0 1.0.
- Quaternius Small Bridge: river crossing. Source: <https://poly.pizza/m/j4KsIuJYnq>; CC0 1.0.

Only a small runtime subset is registered. Local `LICENSE.txt` files preserve the retrieved source information. These packs are cohesive enough for feasibility work, but the art direction is still provisional and should receive a deliberate production-art pass before release.

## Add an asset

1. Prefer GLB/GLTF with embedded materials and a consistent stylized scale. Use sprites only where billboarding is a better fit.
2. Save the original under a creator/pack directory; never rename away provenance.
3. Add a source record and semantic registry entry. Define collision manually from gameplay intent.
4. Run `npm.cmd run test`; the contract suite verifies every registered model and license path exists.
5. Run `npm.cmd run capture`, open the asset browser with `B`, and verify orientation, bounds, shadows, palette, and scale.
6. Adjust registry presentation metadata, not model vertices, where possible. Avoid non-uniform scaling of recognizable authored objects.

## Conversion and optimization

Prefer automated, reproducible conversion to manual edits. A future optimization step may use `gltf-transform` or Blender in batch mode for Draco/Meshopt compression, texture conversion, LODs, and consistent origins. Preserve the original file or its immutable source URL, record the transform command, and verify the result visually.

Tiny repeated assets should be instanced. Large landmarks may remain individual scene nodes. Model meshes never become collision truth. Preview thumbnails are renderer outputs and may be regenerated; they are not source assets.

## Visible-art guardrail

Do not substitute agent-drawn SVGs, Canvas/CSS art, or primitive mesh assemblies for registered scenery. Geometry code is reserved for terrain/water foundations, effects, particles, collision, and debug visualization. If no coherent asset exists, the correct response is to find, convert, or commission one—not quietly normalize programmer art.

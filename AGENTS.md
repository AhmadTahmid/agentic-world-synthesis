# Repository Guidance

## Layout and ownership

- `content/` is hand-authored and canonical. Edit world lore, topology, maps, interiors, and the asset registry here.
- `src/worldsynth/` contains the deterministic compiler, generators, validators, preview renderer, and provider interfaces.
- `generated/` and `game/generated/` are build products. Never hand-edit them.
- `assets/` contains project-owned or explicitly licensed visual assets. Every third-party asset must have a matching license record.
- `game/` is the lightweight Godot 4 runtime. It consumes compiled JSON and never calls Python or an AI provider.
- `tests/` contains behavior tests; fixtures belong in `tests/fixtures/`.
- `hybrid/` is the Three.js visual proof. Its canonical inputs are `hybrid/public/data/*.json`; models live under `hybrid/public/assets/`, and all placement logic must remain declarative or seeded.
- `generated/hybrid-evaluation/` contains reproducible browser captures and measurement reports. It is output, not an input to either runtime.

## Commands

PowerShell setup and verification:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\worldsynth build
.venv\Scripts\pytest
.venv\Scripts\ruff check .
.venv\Scripts\mypy src
```

Hybrid renderer setup and verification:

```powershell
cd hybrid
npm.cmd install
npm.cmd run verify
```

Run the game after installing Godot 4.x:

```powershell
godot --path game --editor
godot --path game
godot_console --headless --path game --script res://scripts/smoke_test.gd
godot_console --path game --script res://scripts/showcase_capture.gd
```

## Determinism

The same source specifications, registered asset bytes, asset registry, generator version, configuration, and seed must produce the same logical compiled maps and canonical hashes. Do not put wall-clock timestamps, absolute paths, or platform-dependent ordering into canonical output. Sort sets and mappings before serialization. Record automatic repairs as diagnostics; never silently mutate authored intent.

## Adding content safely

1. Add or update a typed YAML specification under `content/`.
2. Register every referenced archetype in `content/asset_registry.yaml`.
3. Pair every transition in `content/world_graph.yaml` and in both maps.
4. Run `worldsynth validate`, `worldsynth build`, and the test suite.
5. Inspect `generated/reports/validation.txt` and the previews.
6. Treat generated JSON and images as review artifacts, not authoring sources.

## Licensing

Never add ripped or ambiguously licensed assets. Use original project-owned work, CC0, or similarly commercial-safe assets. Record creator, source URL, license, and attribution requirements in the registry and `assets/licenses/`.

## Hybrid visual-art rule

New visible environmental objects in `hybrid/` must normally be selected from registered GLB/GLTF or sprite assets. Do not create final houses, trees, rocks, fences, or scenery as agent-authored SVG, CSS/canvas drawings, hand-coded polygons, or Box/Sphere primitive assemblies. Primitive geometry remains appropriate for terrain foundations, water planes, particles, effects, invisible collision, and semantic debug views. If a placeholder is unavoidable, label it explicitly and remove it before a visual milestone is considered done.

LLM-authored data should scale with meaningful composition decisions. Repeated grass, flowers, rocks, and shrubs belong in deterministic scatter rules, not thousands of authored coordinates. Gameplay collision and topology remain semantic data; never derive them from a visible model mesh.

## Definition of done

A change is done only when authored input validates; a deterministic build succeeds; blocking errors exit nonzero; tests cover changed semantics; previews/reports are regenerated when relevant; Godot data contracts remain compatible; documentation states limitations honestly; and no secret, copyrighted asset, or hand-edited generated file is introduced.

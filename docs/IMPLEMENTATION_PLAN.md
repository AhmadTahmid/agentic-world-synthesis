# Vertical Slice Implementation Plan

## Environment findings

- Workspace was blank except for an empty `Intiital seed].txt`; no existing architecture or user work was overwritten.
- The directory is not a Git repository.
- Windows/PowerShell and Python 3.12.10 are available.
- Godot, Pydantic, Typer, Pillow, pytest, Ruff, and Mypy were initially absent.
- Godot was installed after the initial implementation. Godot 4.7.2 stable subsequently passed the dedicated smoke test and normal headless project startup.

## Decisions and milestones

### M1 — Repository and typed authoring foundation

Create packaging, repository guidance, versioned Pydantic schemas, YAML loaders, reference resolution, and a real offline planner fixture.

Acceptance: malformed schemas, missing references, bad assets, and invalid coordinates produce actionable errors.

### M2 — Deterministic compiler

Rasterize authored terrain and paths, place seed-driven decorations around protected narrative anchors, derive explicit collision/walkability, normalize runtime JSON, and compute canonical hashes without timestamps.

Acceptance: identical inputs and seed produce byte-identical canonical map JSON; seed overrides affect bounded decoration without moving authored topology.

### M3 — Validation and inspection

Validate bounds, overlaps, doors, spawns, transitions, edge contracts, world reachability, progression, critical-path connectivity, and quality heuristics. Emit JSON/text reports plus layered PNG previews and CLI inspection.

Acceptance: blocking failures return nonzero; every sample map has a preview and both report forms.

### M4 — Authored sample world

Create Lumenfold: Lanternmarket town, Mosswood and Sunmeadow routes, Echo Cave, and tavern/alchemist/research-lodge interiors. Use original geometric provisional assets with explicit project-owned licensing.

Acceptance: all seven maps compile; town links to both routes and three interiors; Mosswood links to the cave; all returns are paired and reachable.

### M5 — Godot runtime

Implement a generic JSON map loader, procedural provisional rendering, CharacterBody2D player, collision, Y sorting, bounded camera, transitions, interactions, encounter placeholder, save state, and F3 debug overlays.

Acceptance: compiled contracts are checked in Python; if Godot becomes available, run the headless loader smoke script and launch the initial map.

### M6 — Verification and documentation

Add schema, references, determinism/hash, edge, collision, bounds/overlap, pathfinding, doorway, transition pairing, integration, CLI, malformed-runtime, and registry tests. Run Ruff, Mypy, pytest, two-build hash comparison, and review docs/generated outputs for misleading claims.

Acceptance: all available checks pass; README includes exact setup/build/test/run commands and an honest Godot status.

## Deliberate limits

This milestone does not implement battle gameplay, live LLM calls, image segmentation, diffusion/inpainting, an editor GUI, runtime world generation, or large-world streaming. Provider and concept-analysis protocols define those seams without claiming implementations.

## Progress

- [x] Environment and repository audit
- [x] Plan and repository rules
- [x] Schemas/loaders/providers
- [x] Compiler/generation/validation/previews
- [x] Sample content/assets
- [x] Godot runtime and headless smoke verification on Godot 4.7.2 stable
- [x] Tests/tooling
- [x] Documentation
- [x] Final regenerated-output and implementation audit

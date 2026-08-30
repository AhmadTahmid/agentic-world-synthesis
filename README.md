# Agentic World Synthesis — Lumenfold vertical slice

This repository is a working deterministic world-authoring pipeline for a 2D top-down RPG. Human-readable YAML is the source of truth. The `worldsynth` compiler validates it, adds bounded seed-driven detail, derives collision and walkability, emits normalized JSON, renders diagnostic previews, and synchronizes the results into a lightweight Godot 4 project.

The included original setting contains seven playable map definitions:

- Lanternmarket, a compact hub with a central beacon and optional secret grove;
- Mosswood Way and Sunmeadow Road, two distinct outdoor routes;
- Echo Cave, a small looped dungeon;
- the Wayfarer's Wick tavern, Violet Alembic, and Field Scholar Lodge interiors.

The runtime supports movement, collision, smooth bounded camera tracking, Y-sorted objects, paired map transitions, interaction prompts, visible encounter placeholders, save/load, and semantic debug overlays.

## Deliberate limits

This milestone does not include monster battles, live LLM calls, diffusion or segmentation, automatic image-to-map conversion, a graphical editor, runtime procedural generation, quests, or chunk streaming. The provider protocols are real integration seams, and the offline rule-based planner is tested, but there is no CLI command pretending to provide an AI workflow.

## Prerequisites and setup

- Python 3.11 or newer (tested here with Python 3.12.10)
- Godot 4.x to run the game (headless runtime tested with Godot 4.7.2 stable)

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev]"
```

Bash equivalents use `.venv/bin/python`, `.venv/bin/worldsynth`, and `.venv/bin/pytest`.

## Build, inspect, and test

```powershell
.venv\Scripts\worldsynth list-maps
.venv\Scripts\worldsynth validate
.venv\Scripts\worldsynth build
.venv\Scripts\worldsynth inspect lanternmarket
.venv\Scripts\worldsynth preview echo_cave --overlays objects,collision,walkability,zones,spawns,transitions,landmarks,edges
.venv\Scripts\pytest
.venv\Scripts\ruff check .
.venv\Scripts\mypy src
```

`build` exits nonzero for blocking content, spatial, topology, or world-consistency failures. It writes:

- canonical runtime maps to `generated/maps/` and `game/generated/maps/`;
- a reproducible manifest to both generated trees;
- PNGs to `generated/previews/`;
- JSON and text validation reports to `generated/reports/`;
- only referenced registered SVGs to `game/assets/`.

The build contains no wall-clock value. `source_content_hash` covers source inputs and generator version; `canonical_hash` covers normalized logical output with its own hash field blanked. Rebuilding identical inputs is byte-stable.

Generate a review variant without changing authored YAML:

```powershell
.venv\Scripts\worldsynth generate mosswood_route --seed 12345
```

This command changes bounded path-edge/decorative variation while preserving authored structures, landmarks, transitions, and narrative topology. It writes review output under `generated/` only and deliberately does not replace the canonical Godot manifest/runtime copy. A subsequent full build restores the canonical authored seed in `generated/` too.

Safely remove rebuildable outputs only:

```powershell
.venv\Scripts\worldsynth clean-generated --yes
```

## Run in Godot

First run `worldsynth build`, then:

```powershell
godot --path game --editor
godot --path game
godot_console --headless --path game --script res://scripts/smoke_test.gd
```

Godot 4.7.2 is installed under `%LOCALAPPDATA%\Programs\Godot` and that folder is on the user `PATH`. Restart terminals that were already open when PATH was updated.

Controls:

- WASD or arrows: move in eight directions
- E or Space: interact
- F5: save current map and position
- F3: toggle every debug overlay
- 1-6: collision, walkability, encounter zones, transitions, object anchors, neighbor edge contracts

Entering an encounter zone shows the exact compiled encounter-table ID in a visible placeholder notification. Saves use `user://worldsynth_save.json` and are updated on transitions.

Godot 4.7.2 stable passed both the dedicated engine smoke test and a normal headless project startup. The smoke test confirmed the initial map, player, 103 collision shapes, and 5 Lanternmarket transitions. Interactive keyboard traversal was not manually exercised by automation.

## Edit a map

1. Edit a YAML file in `content/maps/` or `content/interiors/`.
2. Keep authored anchors explicit: paths are polylines; transitions and zones are rectangles; object positions are ground anchors.
3. Run `worldsynth validate-map <map-id>`.
4. Run `worldsynth build` and inspect the preview/report.
5. Launch or reload the Godot project.

Do not edit generated JSON. See [CONTENT_AUTHORING.md](docs/CONTENT_AUTHORING.md) for complete examples and error guidance.

## Add or replace an asset

1. Put original, CC0, or equivalently commercial-safe art under `assets/`.
2. Add a versioned archetype to `content/asset_registry.yaml`, including pixel/tile dimensions, ground anchor, explicit collision, sockets, tags, color fallback, and full license metadata.
3. Add the license text or source record under `assets/licenses/`.
4. Reference the archetype from a map and rebuild.

Collision is never guessed from sprite pixels. A doorway socket subtracts its exact tile from an archetype footprint; instances cannot silently invent a different collision convention.

## Troubleshooting

- **`Schema validation failed`**: the message includes the file and exact Pydantic field path. Fix canonical YAML.
- **Missing generated manifest/map in Godot**: run `worldsynth build` from the repository root.
- **Godot missing asset error**: confirm the archetype path exists, then rebuild so it is synchronized under `game/assets/`.
- **Unreachable critical point**: use `worldsynth preview <id> --overlays collision,walkability,transitions,landmarks` and inspect the reported coordinate.
- **Hash changed unexpectedly**: inspect source diffs, seed, registry, and `GENERATOR_VERSION`; timestamps are not part of the output.
- **Preview command rejects an overlay**: use one of `objects`, `collision`, `walkability`, `zones`, `spawns`, `transitions`, `landmarks`, or `edges`; use `none` for terrain-only.

Architecture, authoring, and future milestones are documented under `docs/`. Repository invariants and future change criteria are in `AGENTS.md`.

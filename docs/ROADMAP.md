# Roadmap

Completed work is limited to milestone 1. Later items describe intended sequencing, not shipped capability.

## 1. Deterministic world compiler — current vertical slice

Versioned schemas, YAML sources, authored anchors, bounded seeded filling, normalized JSON, hashes, topology/spatial/world validators, previews, CLI, seven-map Lumenfold sample, provisional asset registry, and a data-driven Godot runtime.

Remaining hardening within this milestone: add CI across supported operating systems and automated movement/input simulation beyond the passing Godot 4.7.2 loader smoke test.

## 2. Stronger procedural layouts

Add constrained road rerouting, region polygons, elevation bands, rivers, authored grammars for settlement blocks, richer density fields, and explicit repair plans. Preserve anchors and deterministic snapshots.

## 3. Graphical review/editor

Build a semantic map review tool that edits source specs, compares seeds, visualizes validation paths, approves repairs, and round-trips YAML without treating rendered pixels as truth.

## 4. LLM specification planner

Add an official-SDK adapter behind `PlannerProvider`, schema-constrained output, prompt/version manifests, budget controls, offline fixtures, and adversarial validation. It proposes specs only.

## 5. Reference-image composition analyzer

Extract palette and coarse composition suggestions, map them onto existing terrain/landmark semantics, expose confidence, and require human correction before compilation.

## 6. Controlled asset generation

Generate isolated candidate sprites against registry contracts, require commercial-use license/provenance and human approval, then register selected versions. Gameplay remains stable when art changes.

## 7. Semantic layer decomposition

Introduce optional segmentation/inpainting services for approved references, with explicit uncertainty and no direct conversion from pixels to collision or topology.

## 8. Narrative and quest agents

Add typed quest/story graphs that reference stable world IDs, progression validators, dialogue provenance, and continuity tests.

## 9. Monster ecology and population simulation

Turn ecology rules and encounter tables into validated populations, seasonal constraints, migration, rarity budgets, and battle-ready encounter payloads.

## 10. Large-world chunk streaming

Compile chunk manifests, stable cross-chunk sockets, background loading, save migrations, and runtime performance budgets after authoring semantics are mature.

## 11. Production art and commercial release hardening

Replace provisional art, complete accessibility/localization/input support, profile platforms, audit licenses, sign releases, add migration/version policy, and conduct full gameplay/content QA.

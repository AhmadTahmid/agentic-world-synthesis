# ADR 0006: Derived visual layers do not own gameplay semantics

Status: accepted

## Context

Production-looking terrain needs atlas variants, transition masks, decals, shadows, and foreground overhangs. Encoding collision or transitions inside those tiles would make art replacement change gameplay and would undermine the specification-first pipeline.

## Decision

The compiler derives inspectable render-layer cells from the authoritative terrain grid and asset registry. Godot consumes those cells with `TileMapLayer`, but continues to construct collision, interactions, transitions, and zones from normalized semantic fields. Object layers share an explicit ground anchor while collision footprints and sockets remain separate contracts. A format-1 payload without derived visual fields remains loadable through the diagnostic color fallback.

## Consequences

Art can be replaced without repainting gameplay metadata. Visual compilation adds output size and must be deterministic. Validators and tests compare merged collision rectangles against authoritative blocked cells and check all registered visual paths and provenance.

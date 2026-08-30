# ADR 0007: Four-bit cardinal terrain adjacency masks

Status: accepted

## Context

Hard rectangular terrain boundaries make a symbolic map look like a debug diagram. A small, portable convention is needed without coupling the domain model to Godot terrain-set coordinates.

## Decision

Use a four-bit mask with `N=1`, `E=2`, `S=4`, and `W=8`. A bit is set only for an in-bounds cardinal neighbor with the same semantic terrain ID. Atlas columns 0 through 15 correspond directly to masks. Out-of-bounds neighbors are unset. Diagonal corner treatment belongs to the art family and may be revised later without changing the semantic grid.

## Consequences

The convention is deterministic, testable, and engine-neutral. It provides readable transitions with a compact 16-cell family. More sophisticated eight-neighbor or Godot terrain-set adapters can be introduced as new visual families while retaining the compiled semantic map.

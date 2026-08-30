# ADR 0003: Normalized compiled maps

Status: Accepted

Godot consumes a small versioned JSON contract containing raster terrain, normalized objects, explicit collision/walkability, interactions, transitions, zones, spawns, and asset references.

This avoids fragile generated scene text, supports a generic loader, and makes malformed runtime data independently testable.

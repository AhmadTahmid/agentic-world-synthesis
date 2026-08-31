# ADR 0008: Asset composition instead of code-authored scenery

Status: accepted for the hybrid visual prototype

## Context

The Godot vertical slice proved deterministic semantic compilation, but agent-authored SVG scenery limited visual quality and made token use scale with visible detail.

## Decision

Preserve the existing compiler and Godot runtime, and add a separate declarative Three.js proof. Visible environmental objects come from a registry of authored GLB/GLTF or sprite assets. A compact WorldSpec contains meaningful anchors and composition rules. Seeded systems derive repeated decoration and the renderer supplies materials, motion, light, water, and atmosphere.

Primitive geometry is permitted only for terrain foundations, water, effects, particles, invisible collision, and debug views. Semantic collision remains independent from model geometry. WebGL2 is the initial backend behind a renderer adapter; WebGPU is not required by the contract.

## Consequences

Visual quality becomes mostly a function of asset cohesion, composition, materials, camera, and lighting rather than code-drawing skill. The project gains asset acquisition and optimization work, but meaningful authoring remains compact and deterministic. The old runtime stays available while the new hypothesis is evaluated instead of forcing an immediate engine migration.

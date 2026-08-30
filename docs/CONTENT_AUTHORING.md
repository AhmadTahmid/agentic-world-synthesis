# Content authoring

All coordinates are integer tile coordinates with `(0, 0)` at the top-left. Object `position` is its ground anchor, not its sprite top-left. Rectangles use `x`, `y`, `width`, and `height`, with exclusive right/bottom bounds.

## Create a world node and map

Add the node to `content/world_graph.yaml`:

```yaml
- id: willow_crossing
  kind: route
  region: hearth_vale
  danger_level: 2
  tags: [wetland]
```

Then create `content/maps/willow_crossing.yaml` with the same ID and kind. Select a biome declared in the bible, dimensions of at least 6×6, a fixed seed, known base terrain, at least one player spawn, and narrative metadata. A graph node without a spec—or a spec without a graph node—is an error.

## Define terrain and paths

```yaml
base_terrain: meadow
terrain_regions:
  - {terrain_id: water, rect: {x: 4, y: 2, width: 6, height: 3}}
paths:
  - id: crossing_road
    points: [{x: 0, y: 8}, {x: 10, y: 8}, {x: 18, y: 5}]
    width: 3
    terrain_id: dirt_path
    variation: 1
```

Regions are applied in order, so a later passable rectangle can intentionally cut a doorway through an earlier wall. Paths preserve authored endpoints; the seed affects only small edge variation.

Every semantic terrain ID in the world bible must also have a `terrains` entry in `content/asset_registry.yaml`. Terrain visuals declare a 32-pixel tile family, base/variant atlas cells, legal neighbors, optional decals/animation, movement and collision semantics, and complete license provenance. Edge families use the documented cardinal mask convention `N=1`, `E=2`, `S=4`, `W=8`, with atlas columns 0 through 15. Gameplay collision still comes from compiled semantics, never from painted pixels.

Layered object archetypes may declare `shadow`, `base` or `main`, and `foreground` asset roles. Layer assets share the archetype's visual rectangle and may add a pixel offset. The ground anchor continues to control Y sorting; visual layers do not redefine collision or door sockets.

## Add an edge contract

Both maps must declare compatible contracts on opposite sides:

```yaml
edge_contracts:
  - side: east
    feature: road
    position: 7
    width: 3
    elevation: 0
    biome: sunmeadow
    transition_type: edge
    traversable: true
    neighbor_map: willow_crossing
```

The reverse map uses `side: west` and the same feature, position, width, elevation, boundary biome, transition type, and traversability. Each map also needs a paired `TransitionSpec`, and the pair needs a `WorldConnection`.

## Place a landmark or secret

```yaml
props:
  - id: old_cache
    archetype_id: reward_chest
    position: {x: 12, y: 4}
    interaction_id: old_cache_text
    landmark_id: willow_secret
interactions:
  - id: old_cache_text
    position: {x: 12, y: 5}
    prompt: Open
    text: "A rain-silver token rests inside."
landmarks:
  - id: willow_secret
    position: {x: 12, y: 5}
    unique_key: rain_silver_token
    required: false
zones:
  - {id: cache_nook, kind: secret, rect: {x: 10, y: 2, width: 5, height: 5}, tags: [reward]}
```

Use `unique_key` for narrative landmarks that must occur only once in the whole world. Put the interaction/critical landmark on a reachable adjacent tile when the prop itself has collision.

## Define an enterable building and interior

Register a building archetype with a collision footprint and doorway socket. Place it in the exterior and align the transition rect with the socket:

```yaml
structures:
  - id: willow_inn
    archetype_id: tavern_house
    position: {x: 14, y: 8}
    transition_id: inn_door
    required: true
transitions:
  - id: inn_door
    rect: {x: 14, y: 8, width: 1, height: 1}
    target_map: willow_inn_interior
    target_transition: exit_to_crossing
    target_spawn: {x: 7, y: 7}
    kind: door
```

Create the interior under `content/interiors/`, add its graph node, reverse transition, and graph connection. Its exit targets a walkable exterior tile just outside the door—not the exterior trigger itself. The compiler removes only registered doorway socket cells from archetype collision; it never guesses.

## Add an encounter zone

```yaml
encounter_zones:
  - id: reed_pool
    kind: encounter
    rect: {x: 2, y: 11, width: 10, height: 6}
    encounter_table: wetland_common
    rate: 0.08
    tags: [wetland]
```

The battle table is currently an opaque semantic ID shown by the runtime placeholder. Encounter zones must not overlap a safe zone; that currently produces a warning for human review.

## Constraint-aware decoration

```yaml
generation:
  decoration_families: [broadleaf_tree, mossy_stone]
  decoration_density: 0.04
  protected_path_radius: 1
  min_object_spacing: 1
  reserve:
    - {x: 12, y: 5, width: 5, height: 5}
```

Families are archetype IDs, not semantic tags. Generated instances avoid blocked terrain, map boundaries, occupied collision, authored critical points, paths, and reserve rectangles. If fewer legal candidates exist than requested, the compiled info diagnostic records the actual count.

## Interpret errors

- `bad_transition_target` / `contradictory_transition`: map-local target fields and graph connection disagree.
- `edge_contract_mismatch`: compare both opposite contracts field by field.
- `object_out_of_bounds` / `visual_out_of_bounds`: remember the ground anchor can put a multi-tile sprite left or above its instance coordinate.
- `forbidden_overlap`: explicit collision footprints share a tile.
- `blocked_doorway` / `transition_in_collision`: align the transition to a registered socket and ensure terrain is passable.
- `unreachable_critical`: render collision+walkability overlays and inspect the reported coordinate; decorative unreachable background is allowed.
- `asset_scale_mismatch`: `pixel_size` must equal `tile_size × registry.tile_size`.

Run:

```powershell
.venv\Scripts\worldsynth validate-map willow_crossing
.venv\Scripts\worldsynth preview willow_crossing --overlays collision,walkability,transitions,landmarks
.venv\Scripts\worldsynth build
```

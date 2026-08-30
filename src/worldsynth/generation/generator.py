from __future__ import annotations

import math
import random
from collections.abc import Iterable
from hashlib import sha256
from typing import Protocol

from worldsynth import GENERATOR_VERSION
from worldsynth.domain.models import (
    AssetArchetype,
    CollisionKind,
    CompiledMap,
    CompiledObject,
    CompiledTerrainTile,
    CompositionDecision,
    Diagnostic,
    MapSpec,
    Point,
    Rect,
    RenderStats,
    TerrainTileRef,
    TerrainVisualDefinition,
)
from worldsynth.schemas.loader import ContentBundle
from worldsynth.util import content_hash


def _line(a: Point, b: Point) -> list[tuple[int, int]]:
    """Integer Bresenham line including both endpoints."""
    x0, y0, x1, y1 = a.x, a.y, b.x, b.y
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    error = dx + dy
    cells: list[tuple[int, int]] = []
    while True:
        cells.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return cells
        twice = 2 * error
        if twice >= dy:
            error += dy
            x0 += sx
        if twice <= dx:
            error += dx
            y0 += sy


def rasterize_path(spec: MapSpec, path_index: int, seed: int) -> set[tuple[int, int]]:
    path = spec.paths[path_index]
    center: set[tuple[int, int]] = set()
    for index in range(len(path.points) - 1):
        center.update(_line(path.points[index], path.points[index + 1]))
    radius_low = (path.width - 1) // 2
    radius_high = path.width // 2
    result: set[tuple[int, int]] = set()
    for x, y in center:
        for oy in range(-radius_low, radius_high + 1):
            for ox in range(-radius_low, radius_high + 1):
                result.add((x + ox, y + oy))
    if path.variation:
        rng = random.Random(f"{seed}:{path.id}:edge")
        edge = list(result)
        edge.sort()
        for x, y in edge:
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if rng.random() < 0.025 * path.variation:
                    result.add((x + ox, y + oy))
    return {
        (x, y)
        for x, y in result
        if 0 <= x < spec.dimensions.width and 0 <= y < spec.dimensions.height
    }


def _polygon_contains(x: float, y: float, vertices: list[Point]) -> bool:
    inside = False
    j = len(vertices) - 1
    for i, vertex in enumerate(vertices):
        previous = vertices[j]
        if (vertex.y > y) != (previous.y > y):
            cross = (previous.x - vertex.x) * (y - vertex.y) / (previous.y - vertex.y) + vertex.x
            if x < cross:
                inside = not inside
        j = i
    return inside


def footprint_cells(archetype: AssetArchetype, position: Point) -> set[tuple[int, int]]:
    collision = archetype.collision
    cells: set[tuple[int, int]] = set()
    if collision.kind == CollisionKind.RECT and collision.rect:
        for cell in collision.rect.cells():
            cells.add((position.x + cell.x, position.y + cell.y))
    elif collision.kind == CollisionKind.MASK:
        cells.update((position.x + cell.x, position.y + cell.y) for cell in collision.cells)
    elif collision.kind == CollisionKind.POLYGON:
        xs = [point.x for point in collision.polygon]
        ys = [point.y for point in collision.polygon]
        for y in range(min(ys), max(ys) + 1):
            for x in range(min(xs), max(xs) + 1):
                if _polygon_contains(x + 0.5, y + 0.5, collision.polygon):
                    cells.add((position.x + x, position.y + y))
    for socket in archetype.doorway_sockets:
        cells.discard((position.x + socket.offset.x, position.y + socket.offset.y))
    return cells


def _visual_rect(archetype: AssetArchetype, position: Point) -> Rect:
    return Rect(
        x=position.x - archetype.ground_anchor.x,
        y=position.y - archetype.ground_anchor.y,
        width=archetype.tile_size.width,
        height=archetype.tile_size.height,
    )


class _PlacementLike(Protocol):
    id: str
    position: Point
    interaction_id: str | None
    transition_id: str | None
    landmark_id: str | None


def _compile_object(
    placement: _PlacementLike,
    archetype: AssetArchetype,
    *,
    generated: bool = False,
    variant_id: str | None = None,
    grammar_id: str | None = None,
) -> CompiledObject:
    # ObjectPlacement and the private generated placement share these fields.
    position = placement.position
    return CompiledObject(
        id=placement.id,
        archetype_id=archetype.id,
        position=position,
        visual_rect=_visual_rect(archetype, position),
        collision_cells=[Point(x=x, y=y) for x, y in sorted(footprint_cells(archetype, position))],
        asset_path=archetype.asset_path,
        color=archetype.color,
        tags=archetype.tags,
        interaction_id=placement.interaction_id,
        transition_id=placement.transition_id,
        landmark_id=placement.landmark_id,
        generated=generated,
        variant_id=variant_id,
        grammar_id=grammar_id,
        visual_layers=archetype.visual_layers,
    )


class _GeneratedPlacement:
    def __init__(self, item_id: str, archetype_id: str, position: Point) -> None:
        self.id = item_id
        self.archetype_id = archetype_id
        self.position = position
        self.interaction_id: str | None = None
        self.transition_id: str | None = None
        self.landmark_id: str | None = None


def _near(cells: Iterable[tuple[int, int]], x: int, y: int, radius: int) -> bool:
    return any(abs(cx - x) <= radius and abs(cy - y) <= radius for cx, cy in cells)


def protected_decoration_cells(
    spec: MapSpec, path_cells: Iterable[tuple[int, int]]
) -> set[tuple[int, int]]:
    """Return source-map cells that optional decoration must not occupy."""
    protected = set(path_cells)
    protected.update((spawn.position.x, spawn.position.y) for spawn in spec.spawns)
    protected.update((landmark.position.x, landmark.position.y) for landmark in spec.landmarks)
    protected.update(
        (interaction.position.x, interaction.position.y) for interaction in spec.interactions
    )
    for transition in spec.transitions:
        protected.update((point.x, point.y) for point in transition.rect.cells())
    for reserved in spec.generation.reserve:
        protected.update((point.x, point.y) for point in reserved.cells())
    return protected


def adjacency_mask(terrain: list[list[str]], x: int, y: int, terrain_id: str) -> int:
    """Return a cardinal N=1, E=2, S=4, W=8 same-terrain mask.

    Coordinates outside the map are deliberately considered different terrain,
    so map-edge cells receive an edge tile instead of an implicit continuation.
    """
    height = len(terrain)
    width = len(terrain[0]) if height else 0
    mask = 0
    for bit, dx, dy in ((1, 0, -1), (2, 1, 0), (4, 0, 1), (8, -1, 0)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height and terrain[ny][nx] == terrain_id:
            mask |= bit
    return mask


def merge_blocked_cells(blocked: Iterable[tuple[int, int]], width: int, height: int) -> list[Rect]:
    """Greedily merge identical horizontal runs across consecutive rows."""
    cells = {(x, y) for x, y in blocked if 0 <= x < width and 0 <= y < height}
    active: dict[tuple[int, int], Rect] = {}
    result: list[Rect] = []
    for y in range(height):
        runs: list[tuple[int, int]] = []
        x = 0
        while x < width:
            if (x, y) not in cells:
                x += 1
                continue
            start = x
            while x < width and (x, y) in cells:
                x += 1
            runs.append((start, x - start))
        current: dict[tuple[int, int], Rect] = {}
        for key in runs:
            previous = active.pop(key, None)
            current[key] = (
                Rect(x=previous.x, y=previous.y, width=previous.width, height=previous.height + 1)
                if previous is not None
                else Rect(x=key[0], y=y, width=key[1], height=1)
            )
        result.extend(active.values())
        active = current
    result.extend(active.values())
    return sorted(result, key=lambda item: (item.y, item.x, item.height, item.width))


def _stable_roll(*parts: object) -> int:
    value = ":".join(str(part) for part in parts).encode()
    return int.from_bytes(sha256(value).digest()[:8], "big")


def asset_content_hashes(bundle: ContentBundle) -> dict[str, str]:
    """Hash registered source art so visual changes invalidate build provenance."""
    paths: set[str] = set()
    for archetype in bundle.assets.archetypes:
        paths.add(archetype.asset_path)
        paths.update(layer.asset_path for layer in archetype.visual_layers)
    for terrain in bundle.assets.terrains:
        paths.add(terrain.base_tile.asset_path)
        paths.update(item.asset_path for item in terrain.variants)
        paths.update(item.asset_path for item in terrain.decals)
        if terrain.adjacency_set:
            paths.add(terrain.adjacency_set.asset_path)
    return {
        path: sha256((bundle.root / path).read_bytes()).hexdigest()
        for path in sorted(paths)
        if (bundle.root / path).is_file()
    }


def _choose_tile(
    visual: TerrainVisualDefinition, map_id: str, seed: int, x: int, y: int
) -> TerrainTileRef:
    choices = [visual.base_tile, *visual.variants]
    total = sum(item.weight for item in choices)
    roll = _stable_roll(GENERATOR_VERSION, map_id, seed, visual.terrain_id, x, y) % total
    for item in choices:
        if roll < item.weight:
            return item
        roll -= item.weight
    return choices[-1]


def compile_terrain_layers(
    bundle: ContentBundle, spec: MapSpec, terrain: list[list[str]], seed: int
) -> dict[str, list[CompiledTerrainTile]]:
    """Compile semantic terrain into deterministic, inspectable render tiles."""
    visuals = bundle.assets.terrain_by_id()
    layers: dict[str, list[CompiledTerrainTile]] = {
        "base": [],
        "terrain_transitions": [],
        "paths": [],
        "ground_decals": [],
        "water": [],
        "walls": [],
    }

    def append_tile(layer: str, visual: TerrainVisualDefinition, x: int, y: int) -> None:
        mask = adjacency_mask(terrain, x, y, visual.terrain_id)
        if visual.adjacency_set is not None:
            atlas = Point(
                x=visual.adjacency_set.first_cell.x + mask,
                y=visual.adjacency_set.first_cell.y,
            )
            ref = TerrainTileRef(
                id=f"{visual.terrain_id}_mask_{mask}",
                asset_path=visual.adjacency_set.asset_path,
                atlas_cell=atlas,
            )
        else:
            ref = _choose_tile(visual, spec.map_id, seed, x, y)
        layers[layer].append(
            CompiledTerrainTile(
                position=Point(x=x, y=y),
                terrain_id=visual.terrain_id,
                asset_path=ref.asset_path,
                atlas_cell=ref.atlas_cell,
                mask=mask,
                variant_id=ref.id,
            )
        )

    for y, row in enumerate(terrain):
        for x, terrain_id in enumerate(row):
            visual = visuals.get(terrain_id)
            if visual is None:
                continue
            if visual.underlay_terrain_id and visual.underlay_terrain_id in visuals:
                underlay = visuals[visual.underlay_terrain_id]
                append_tile("base", underlay, x, y)
            target_layer = {
                "base": "base",
                "path": "paths"
                if adjacency_mask(terrain, x, y, terrain_id) == 15
                else "terrain_transitions",
                "water": "water",
                "wall": "walls",
            }[visual.render_layer]
            append_tile(target_layer, visual, x, y)
            if (
                visual.decals
                and _stable_roll(spec.map_id, seed, terrain_id, x, y, "decal") % 100 < 8
            ):
                decal = visual.decals[
                    _stable_roll(spec.map_id, seed, x, y, "decal_choice") % len(visual.decals)
                ]
                layers["ground_decals"].append(
                    CompiledTerrainTile(
                        position=Point(x=x, y=y),
                        terrain_id=terrain_id,
                        asset_path=decal.asset_path,
                        atlas_cell=decal.atlas_cell,
                        mask=15,
                        variant_id=decal.id,
                    )
                )
    return {name: tiles for name, tiles in layers.items() if tiles}


def _expanded(
    cells: Iterable[tuple[int, int]], radius: int, width: int, height: int
) -> set[tuple[int, int]]:
    return {
        (x + dx, y + dy)
        for x, y in cells
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if 0 <= x + dx < width and 0 <= y + dy < height
    }


def _visual_grammar(
    spec: MapSpec,
    path_cells: set[tuple[int, int]],
    base_protected: set[tuple[int, int]],
) -> tuple[set[tuple[int, int]], list[CompositionDecision], dict[tuple[int, int], str]]:
    """Build explicit town composition constraints without moving authored anchors."""
    width, height = spec.dimensions.width, spec.dimensions.height
    protected = set(base_protected)
    decisions: list[CompositionDecision] = []
    grammar_cells: dict[tuple[int, int], str] = {}

    def add_decision(grammar: str, cells: set[tuple[int, int]], rationale: str) -> None:
        if not cells:
            return
        decisions.append(
            CompositionDecision(
                id=f"{grammar}_{len(decisions):02d}",
                grammar=grammar,  # type: ignore[arg-type]
                cells=[Point(x=x, y=y) for x, y in sorted(cells, key=lambda p: (p[1], p[0]))],
                rationale=rationale,
            )
        )

    landmark_cells = {(item.position.x, item.position.y) for item in spec.landmarks}
    clearing = _expanded(landmark_cells, 3, width, height)
    protected.update(clearing)
    add_decision(
        "landmark_clearing", clearing, "Preserve readable space around authored landmarks."
    )

    setbacks: set[tuple[int, int]] = set()
    door_cells: set[tuple[int, int]] = set()
    for structure in spec.structures:
        setbacks.update(_expanded({(structure.position.x, structure.position.y)}, 2, width, height))
    for transition in spec.transitions:
        if transition.kind == "door":
            door_cells.update(
                _expanded({(p.x, p.y) for p in transition.rect.cells()}, 2, width, height)
            )
    protected.update(setbacks | door_cells)
    add_decision(
        "building_setback", setbacks, "Keep building silhouettes and approaches uncluttered."
    )
    add_decision("door_clearance", door_cells, "Reserve approach cells around enterable doors.")

    intersections = {
        (x, y)
        for x, y in path_cells
        if sum((x + dx, y + dy) in path_cells for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) >= 3
    }
    intersection_clearance = _expanded(intersections, 2, width, height)
    protected.update(intersection_clearance)
    add_decision(
        "intersection_clearance", intersection_clearance, "Keep junctions legible and navigable."
    )

    if spec.spawns and spec.landmarks:
        sightline = set(_line(spec.spawns[0].position, spec.landmarks[0].position))
        sightline = _expanded(sightline, 1, width, height)
        protected.update(sightline)
        add_decision(
            "sightline", sightline, "Frame the central beacon from the player arrival route."
        )

    roadside = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if (x, y) not in protected and _near(path_cells, x, y, 2) and not _near(path_cells, x, y, 1)
    }
    for cell in roadside:
        grammar_cells[cell] = "roadside"
    add_decision("roadside", roadside, "Use low vegetation to frame roads without narrowing them.")

    vegetation = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if (x, y) not in protected and (x, y) not in roadside
    }
    for cell in vegetation:
        grammar_cells[cell] = "vegetation_cluster"
    add_decision(
        "vegetation_cluster", vegetation, "Concentrate vegetation away from civic sightlines."
    )
    return protected, decisions, grammar_cells


def compile_layout(bundle: ContentBundle, spec: MapSpec, seed: int | None = None) -> CompiledMap:
    effective_seed = spec.seed if seed is None else seed
    width, height = spec.dimensions.width, spec.dimensions.height
    terrain = [[spec.base_terrain for _ in range(width)] for _ in range(height)]
    for region in spec.terrain_regions:
        for point in region.rect.cells():
            if 0 <= point.x < width and 0 <= point.y < height:
                terrain[point.y][point.x] = region.terrain_id

    path_cells: set[tuple[int, int]] = set()
    for index, path in enumerate(spec.paths):
        cells = rasterize_path(spec, index, effective_seed)
        path_cells.update(cells)
        terrain_id = path.terrain_id or bundle.bible.biome_by_id()[spec.biome].path_terrain
        for x, y in cells:
            terrain[y][x] = terrain_id

    archetypes = bundle.assets.by_id()
    objects: list[CompiledObject] = []
    occupied: set[tuple[int, int]] = set()
    for placement in spec.structures + spec.props:
        archetype = archetypes.get(placement.archetype_id)
        if archetype is None:
            continue
        compiled = _compile_object(placement, archetype)
        objects.append(compiled)
        occupied.update((cell.x, cell.y) for cell in compiled.collision_cells)

    protected = protected_decoration_cells(spec, path_cells)
    composition_decisions: list[CompositionDecision] = []
    grammar_cells: dict[tuple[int, int], str] = {}
    if spec.map_id == "lanternmarket":
        protected, composition_decisions, grammar_cells = _visual_grammar(
            spec, path_cells, protected
        )
    else:
        composition_decisions.append(
            CompositionDecision(
                id="uniform_fallback_00",
                grammar="uniform_fallback",
                cells=[],
                rationale="Legacy seeded decoration distribution retained outside the visual milestone map.",
            )
        )

    biome = bundle.bible.biome_by_id()[spec.biome]
    density = (
        biome.decoration_density
        if spec.generation.decoration_density is None
        else spec.generation.decoration_density
    )
    target = math.floor(width * height * density)
    families = [
        archetypes[item] for item in spec.generation.decoration_families if item in archetypes
    ]
    candidates = [(x, y) for y in range(height) for x in range(width)]
    rng = random.Random(f"{GENERATOR_VERSION}:{spec.map_id}:{effective_seed}")
    rng.shuffle(candidates)
    if spec.map_id == "lanternmarket":
        # Prefer clustered vegetation, then sparse roadside accents. The stable
        # shuffled order supplies variation inside each explicit grammar family.
        candidates.sort(
            key=lambda cell: (
                0 if grammar_cells.get(cell) == "vegetation_cluster" else 1,
                _stable_roll(spec.map_id, effective_seed, cell[0] // 4, cell[1] // 4, "cluster"),
            )
        )
    decorations: list[CompiledObject] = []
    blocked_terrain = set(bundle.bible.traversal.blocked_terrain)
    for x, y in candidates:
        if len(decorations) >= target or not families:
            break
        if terrain[y][x] in blocked_terrain:
            continue
        if _near(protected, x, y, spec.generation.protected_path_radius):
            continue
        if _near(occupied, x, y, spec.generation.min_object_spacing):
            continue
        grammar_id = grammar_cells.get((x, y), "uniform_fallback")
        if grammar_id == "roadside":
            low_families = [item for item in families if "tree" not in item.tags]
            archetype = rng.choice(low_families or families)
        else:
            archetype = rng.choice(families)
        variant_id = (
            archetype.variants[
                _stable_roll(spec.map_id, effective_seed, archetype.id, x, y)
                % len(archetype.variants)
            ]
            if archetype.variants
            else None
        )
        generated_placement = _GeneratedPlacement(
            f"generated_{archetype.id}_{len(decorations):04d}", archetype.id, Point(x=x, y=y)
        )
        compiled = _compile_object(
            generated_placement,
            archetype,
            generated=True,
            variant_id=variant_id,
            grammar_id=grammar_id,
        )
        collision = {(cell.x, cell.y) for cell in compiled.collision_cells}
        visual = compiled.visual_rect
        if (
            visual.x < 0
            or visual.y < 0
            or visual.x + visual.width > width
            or visual.y + visual.height > height
            or any(not (0 <= cx < width and 0 <= cy < height) for cx, cy in collision)
            or collision & occupied
        ):
            continue
        decorations.append(compiled)
        occupied.update(collision)

    terrain_blocked = {
        (x, y)
        for y, row in enumerate(terrain)
        for x, terrain_id in enumerate(row)
        if terrain_id in blocked_terrain
    }
    blocked = terrain_blocked | occupied
    collision_rects = merge_blocked_cells(blocked, width, height)
    render_layers = compile_terrain_layers(bundle, spec, terrain, effective_seed)
    object_layer_counts: dict[str, int] = {}
    for item in [*objects, *decorations]:
        if item.visual_layers:
            for visual_layer in item.visual_layers:
                object_layer_counts[visual_layer.role] = (
                    object_layer_counts.get(visual_layer.role, 0) + 1
                )
        else:
            object_layer_counts["main"] = object_layer_counts.get("main", 0) + 1
    static_structures = sum("building" in item.tags for item in objects)
    object_layer_counts["static_structures"] = static_structures
    object_layer_counts["y_sorted_entities_props"] = (
        len(objects) + len(decorations) - static_structures
    )
    walkability = [
        "".join("#" if (x, y) in blocked else "." for x in range(width)) for y in range(height)
    ]
    source_material = {
        "generator_version": GENERATOR_VERSION,
        "world": bundle.bible,
        "assets": bundle.assets,
        "asset_content_hashes": asset_content_hashes(bundle),
        "map": spec,
        "seed": effective_seed,
    }
    compiled_map = CompiledMap(
        format_version=1,
        map_id=spec.map_id,
        display_name=spec.display_name,
        map_type=spec.map_type,
        biome=spec.biome,
        source_content_hash=content_hash(source_material),
        seed=effective_seed,
        tile_size=bundle.bible.tile_size,
        width=width,
        height=height,
        terrain=terrain,
        decorative_layers=decorations,
        objects=objects,
        blocked_cells=[Point(x=x, y=y) for x, y in sorted(blocked, key=lambda p: (p[1], p[0]))],
        walkability=walkability,
        interactions=spec.interactions,
        transitions=spec.transitions,
        zones=spec.encounter_zones + spec.zones,
        spawns=spec.spawns,
        landmarks=spec.landmarks,
        edge_contracts=spec.edge_contracts,
        asset_references=sorted(
            {item.archetype_id for item in spec.structures + spec.props}
            | set(spec.generation.decoration_families)
        ),
        build_metadata={
            "generator_version": GENERATOR_VERSION,
            "reproducible": True,
            "source_schema_version": spec.schema_version,
        },
        diagnostics=[
            Diagnostic(
                severity="info",
                code="generated_decorations",
                map_id=spec.map_id,
                message=f"Placed {len(decorations)} of {target} requested decorations using seed {effective_seed}.",
            )
        ],
        render_layers=render_layers,
        protected_visual_cells=[
            Point(x=x, y=y) for x, y in sorted(protected, key=lambda p: (p[1], p[0]))
        ],
        composition_decisions=composition_decisions,
        collision_rects=collision_rects,
        render_stats=RenderStats(
            blocked_cell_count=len(blocked),
            collision_shape_count=len(collision_rects),
            collision_reduction_ratio=(len(blocked) / len(collision_rects))
            if collision_rects
            else 0,
            tile_layer_counts={name: len(tiles) for name, tiles in render_layers.items()},
            object_layer_counts=object_layer_counts,
        ),
    )
    hash_payload = compiled_map.model_dump(mode="json")
    hash_payload["canonical_hash"] = ""
    compiled_map.canonical_hash = content_hash(hash_payload)
    return compiled_map

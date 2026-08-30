from __future__ import annotations

import math
import random
from collections.abc import Iterable
from typing import Protocol

from worldsynth import GENERATOR_VERSION
from worldsynth.domain.models import (
    AssetArchetype,
    CollisionKind,
    CompiledMap,
    CompiledObject,
    Diagnostic,
    MapSpec,
    Point,
    Rect,
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
    placement: _PlacementLike, archetype: AssetArchetype, *, generated: bool = False
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

    protected = set(path_cells)
    protected.update((spawn.position.x, spawn.position.y) for spawn in spec.spawns)
    protected.update((landmark.position.x, landmark.position.y) for landmark in spec.landmarks)
    protected.update((interaction.position.x, interaction.position.y) for interaction in spec.interactions)
    for transition in spec.transitions:
        protected.update((point.x, point.y) for point in transition.rect.cells())
        protected.add((transition.target_spawn.x, transition.target_spawn.y))
    for reserved in spec.generation.reserve:
        protected.update((point.x, point.y) for point in reserved.cells())

    biome = bundle.bible.biome_by_id()[spec.biome]
    density = (
        biome.decoration_density
        if spec.generation.decoration_density is None
        else spec.generation.decoration_density
    )
    target = math.floor(width * height * density)
    families = [archetypes[item] for item in spec.generation.decoration_families if item in archetypes]
    candidates = [(x, y) for y in range(height) for x in range(width)]
    rng = random.Random(f"{GENERATOR_VERSION}:{spec.map_id}:{effective_seed}")
    rng.shuffle(candidates)
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
        archetype = rng.choice(families)
        generated_placement = _GeneratedPlacement(
            f"generated_{archetype.id}_{len(decorations):04d}", archetype.id, Point(x=x, y=y)
        )
        compiled = _compile_object(generated_placement, archetype, generated=True)
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
    walkability = [
        "".join("#" if (x, y) in blocked else "." for x in range(width)) for y in range(height)
    ]
    source_material = {
        "generator_version": GENERATOR_VERSION,
        "world": bundle.bible,
        "assets": bundle.assets,
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
    )
    hash_payload = compiled_map.model_dump(mode="json")
    hash_payload["canonical_hash"] = ""
    compiled_map.canonical_hash = content_hash(hash_payload)
    return compiled_map

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Iterable
from pathlib import Path

from worldsynth.domain.models import (
    CompiledMap,
    Diagnostic,
    MapSpec,
    Point,
    Rect,
    TransitionSpec,
    ValidationReport,
)
from worldsynth.schemas.loader import ContentBundle


def _issue(
    severity: str,
    code: str,
    message: str,
    map_id: str | None = None,
    location: Point | None = None,
) -> Diagnostic:
    return Diagnostic(
        severity=severity,  # type: ignore[arg-type]
        code=code,
        message=message,
        map_id=map_id,
        location=location,
    )


def _point_in_bounds(point: Point, spec: MapSpec) -> bool:
    return 0 <= point.x < spec.dimensions.width and 0 <= point.y < spec.dimensions.height


def _rect_in_bounds(rect: Rect, spec: MapSpec) -> bool:
    return (
        rect.x >= 0
        and rect.y >= 0
        and rect.x + rect.width <= spec.dimensions.width
        and rect.y + rect.height <= spec.dimensions.height
    )


def _transition_lookup(
    bundle: ContentBundle, map_id: str, transition_id: str
) -> TransitionSpec | None:
    spec = bundle.maps.get(map_id)
    if spec is None:
        return None
    return next((item for item in spec.transitions if item.id == transition_id), None)


def _opposite(side: str) -> str:
    return {"north": "south", "south": "north", "east": "west", "west": "east"}[side]


def validate_sources(bundle: ContentBundle, only_map: str | None = None) -> list[Diagnostic]:
    issues: list[Diagnostic] = []
    maps = bundle.maps
    graph_nodes = {node.id: node for node in bundle.graph.nodes}
    archetypes = bundle.assets.by_id()
    biome_ids = set(bundle.bible.biome_by_id())
    terrain_ids = set(bundle.bible.traversal.passable_terrain) | set(
        bundle.bible.traversal.blocked_terrain
    )

    if bundle.bible.world_id != bundle.graph.world_id:
        issues.append(_issue("error", "world_id_mismatch", "World bible and graph IDs differ."))
    if bundle.graph.start_map not in maps:
        issues.append(
            _issue("error", "missing_start_map", f"Start map {bundle.graph.start_map!r} is missing.")
        )
    for node_id in sorted(set(graph_nodes) - set(maps)):
        issues.append(_issue("error", "missing_map_spec", f"World node {node_id!r} has no map spec."))
    for map_id in sorted(set(maps) - set(graph_nodes)):
        issues.append(_issue("error", "missing_world_node", f"Map {map_id!r} has no world graph node."))

    endpoint_use: Counter[tuple[str, str]] = Counter()
    graph_adjacency: dict[str, set[str]] = {node_id: set() for node_id in graph_nodes}
    for connection in bundle.graph.connections:
        endpoint_use[(connection.from_map, connection.from_transition)] += 1
        endpoint_use[(connection.to_map, connection.to_transition)] += 1
        for map_id in (connection.from_map, connection.to_map):
            if map_id not in graph_nodes:
                issues.append(
                    _issue(
                        "error",
                        "bad_connection_reference",
                        f"Connection {connection.id!r} references missing node {map_id!r}.",
                    )
                )
        if connection.from_map in graph_adjacency and connection.to_map in graph_adjacency:
            graph_adjacency[connection.from_map].add(connection.to_map)
            if connection.bidirectional:
                graph_adjacency[connection.to_map].add(connection.from_map)
        left = _transition_lookup(bundle, connection.from_map, connection.from_transition)
        right = _transition_lookup(bundle, connection.to_map, connection.to_transition)
        if left is None or right is None:
            issues.append(
                _issue(
                    "error",
                    "missing_transition_reference",
                    f"Connection {connection.id!r} references an absent transition endpoint.",
                )
            )
        elif (
            left.target_map != connection.to_map
            or left.target_transition != connection.to_transition
            or right.target_map != connection.from_map
            or right.target_transition != connection.from_transition
        ):
            issues.append(
                _issue(
                    "error",
                    "contradictory_transition",
                    f"Connection {connection.id!r} and its map transitions disagree.",
                )
            )
    for endpoint, count in sorted(endpoint_use.items()):
        if count > 1:
            issues.append(
                _issue(
                    "error",
                    "duplicate_connection_endpoint",
                    f"Transition {endpoint[0]}.{endpoint[1]} occurs in {count} world connections.",
                )
            )

    if bundle.graph.start_map in graph_adjacency:
        reached = _reachable_graph(bundle.graph.start_map, graph_adjacency)
        for node in bundle.graph.nodes:
            if node.required and node.id not in reached:
                issues.append(
                    _issue("error", "unreachable_world_node", f"Required node {node.id!r} is unreachable.")
                )

    for connection in bundle.graph.connections:
        left_node = graph_nodes.get(connection.from_map)
        right_node = graph_nodes.get(connection.to_map)
        if left_node and right_node:
            jump = abs(left_node.danger_level - right_node.danger_level)
            if jump > bundle.bible.traversal.max_danger_step and connection.story_gate is None:
                issues.append(
                    _issue(
                        "error",
                        "danger_jump",
                        f"Connection {connection.id!r} jumps {jump} danger levels without a gate.",
                    )
                )

    unique_landmarks: dict[str, str] = {}
    for map_id, spec in sorted(maps.items()):
        if only_map is not None and map_id != only_map:
            continue
        current_node = graph_nodes.get(map_id)
        if current_node and current_node.kind != spec.map_type:
            issues.append(
                _issue(
                    "error",
                    "map_type_mismatch",
                    f"Graph calls {map_id!r} {current_node.kind}, spec calls it {spec.map_type}.",
                    map_id,
                )
            )
        if spec.biome not in biome_ids:
            issues.append(_issue("error", "unknown_biome", f"Unknown biome {spec.biome!r}.", map_id))
        for terrain_id in [spec.base_terrain] + [r.terrain_id for r in spec.terrain_regions]:
            if terrain_id not in terrain_ids:
                issues.append(
                    _issue("error", "unknown_terrain", f"Unknown terrain {terrain_id!r}.", map_id)
                )
        for path in spec.paths:
            if path.terrain_id and path.terrain_id not in terrain_ids:
                issues.append(
                    _issue(
                        "error", "unknown_terrain", f"Path {path.id!r} uses unknown terrain.", map_id
                    )
                )
            for point in path.points:
                if not _point_in_bounds(point, spec):
                    issues.append(
                        _issue("error", "point_out_of_bounds", f"Path {path.id!r} point is outside map.", map_id, point)
                    )
        for region in spec.terrain_regions:
            if not _rect_in_bounds(region.rect, spec):
                issues.append(_issue("error", "rect_out_of_bounds", "Terrain region is outside map.", map_id))
        for placement in spec.structures + spec.props:
            if placement.archetype_id not in archetypes:
                issues.append(
                    _issue(
                        "error",
                        "missing_archetype",
                        f"Object {placement.id!r} references {placement.archetype_id!r}.",
                        map_id,
                        placement.position,
                    )
                )
            if not _point_in_bounds(placement.position, spec):
                issues.append(_issue("error", "object_out_of_bounds", f"Object {placement.id!r} is outside map.", map_id, placement.position))
        for family in spec.generation.decoration_families:
            if family not in archetypes:
                issues.append(_issue("error", "missing_archetype", f"Decoration family {family!r} is missing.", map_id))
        for transition in spec.transitions:
            if not _rect_in_bounds(transition.rect, spec):
                issues.append(_issue("error", "transition_out_of_bounds", f"Transition {transition.id!r} is outside map.", map_id))
            if not _point_in_bounds(transition.target_spawn, maps.get(transition.target_map, spec)):
                issues.append(_issue("error", "target_spawn_out_of_bounds", f"Transition {transition.id!r} target spawn is outside target map.", map_id))
            if transition.target_map not in maps:
                issues.append(_issue("error", "bad_transition_target", f"Transition {transition.id!r} targets missing map.", map_id))
            elif _transition_lookup(bundle, transition.target_map, transition.target_transition) is None:
                issues.append(_issue("error", "bad_transition_target", f"Transition {transition.id!r} targets missing endpoint.", map_id))
        for spawn in spec.spawns:
            if not _point_in_bounds(spawn.position, spec):
                issues.append(_issue("error", "spawn_out_of_bounds", f"Spawn {spawn.id!r} is outside map.", map_id, spawn.position))
        for interaction in spec.interactions:
            if not _point_in_bounds(interaction.position, spec):
                issues.append(_issue("error", "interaction_out_of_bounds", f"Interaction {interaction.id!r} is outside map.", map_id, interaction.position))
        for zone in spec.encounter_zones + spec.zones:
            if not _rect_in_bounds(zone.rect, spec):
                issues.append(_issue("error", "invalid_zone_geometry", f"Zone {zone.id!r} is outside map.", map_id))
        for landmark in spec.landmarks:
            if not _point_in_bounds(landmark.position, spec):
                issues.append(_issue("error", "landmark_out_of_bounds", f"Landmark {landmark.id!r} is outside map.", map_id, landmark.position))
            if landmark.unique_key:
                previous = unique_landmarks.get(landmark.unique_key)
                if previous:
                    issues.append(_issue("error", "duplicate_unique_landmark", f"Landmark key {landmark.unique_key!r} appears in {previous!r} and {map_id!r}."))
                unique_landmarks[landmark.unique_key] = map_id
        for edge in spec.edge_contracts:
            axis_size = spec.dimensions.width if edge.side in ("north", "south") else spec.dimensions.height
            if edge.position + edge.width > axis_size:
                issues.append(_issue("error", "edge_out_of_bounds", f"{edge.side} edge contract exceeds boundary.", map_id))
            neighbor = maps.get(edge.neighbor_map)
            if neighbor is None:
                issues.append(_issue("error", "missing_edge_neighbor", f"Edge references missing {edge.neighbor_map!r}.", map_id))
                continue
            reverse = next(
                (
                    item
                    for item in neighbor.edge_contracts
                    if item.neighbor_map == map_id and item.side == _opposite(edge.side)
                ),
                None,
            )
            if reverse is None:
                issues.append(_issue("error", "unpaired_edge_contract", f"No reverse edge contract in {neighbor.map_id!r}.", map_id))
            elif (
                edge.feature,
                edge.position,
                edge.width,
                edge.elevation,
                edge.biome,
                edge.transition_type,
                edge.traversable,
            ) != (
                reverse.feature,
                reverse.position,
                reverse.width,
                reverse.elevation,
                reverse.biome,
                reverse.transition_type,
                reverse.traversable,
            ):
                issues.append(_issue("error", "edge_contract_mismatch", f"Edge contract with {neighbor.map_id!r} is incompatible.", map_id))

    for archetype in bundle.assets.archetypes:
        asset_path = bundle.root / Path(archetype.asset_path)
        if not asset_path.is_file():
            issues.append(_issue("error", "missing_asset_file", f"Archetype {archetype.id!r} asset does not exist: {archetype.asset_path}"))
        expected_width = archetype.tile_size.width * bundle.assets.tile_size
        expected_height = archetype.tile_size.height * bundle.assets.tile_size
        if archetype.pixel_size.width != expected_width or archetype.pixel_size.height != expected_height:
            issues.append(_issue("error", "asset_scale_mismatch", f"Archetype {archetype.id!r} pixel and tile sizes disagree with registry tile scale."))
    return issues


def _reachable_graph(start: str, graph: dict[str, set[str]]) -> set[str]:
    reached = {start}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for neighbor in graph.get(current, set()):
            if neighbor not in reached:
                reached.add(neighbor)
                queue.append(neighbor)
    return reached


def _rect_cells(rect: Rect) -> set[tuple[int, int]]:
    return {(point.x, point.y) for point in rect.cells()}


def _bfs(compiled: CompiledMap, start: tuple[int, int]) -> set[tuple[int, int]]:
    if not (0 <= start[0] < compiled.width and 0 <= start[1] < compiled.height):
        return set()
    if compiled.walkability[start[1]][start[0]] == "#":
        return set()
    reached = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = (x + dx, y + dy)
            if (
                neighbor not in reached
                and 0 <= neighbor[0] < compiled.width
                and 0 <= neighbor[1] < compiled.height
                and compiled.walkability[neighbor[1]][neighbor[0]] == "."
            ):
                reached.add(neighbor)
                queue.append(neighbor)
    return reached


def _center(rect: Rect) -> tuple[int, int]:
    return (rect.x + rect.width // 2, rect.y + rect.height // 2)


def validate_compiled_map(compiled: CompiledMap, bundle: ContentBundle) -> list[Diagnostic]:
    issues: list[Diagnostic] = []
    blocked = {(point.x, point.y) for point in compiled.blocked_cells}
    collision_owner: dict[tuple[int, int], str] = {}
    for item in compiled.objects + compiled.decorative_layers:
        if (
            item.visual_rect.x < 0
            or item.visual_rect.y < 0
            or item.visual_rect.x + item.visual_rect.width > compiled.width
            or item.visual_rect.y + item.visual_rect.height > compiled.height
        ):
            issues.append(_issue("error", "visual_out_of_bounds", f"Object {item.id!r} visual bounds leave the map.", compiled.map_id, item.position))
        for point in item.collision_cells:
            cell = (point.x, point.y)
            previous = collision_owner.get(cell)
            if previous:
                issues.append(_issue("error", "forbidden_overlap", f"Objects {previous!r} and {item.id!r} overlap collision at {cell}.", compiled.map_id, point))
            collision_owner[cell] = item.id
            if not (0 <= point.x < compiled.width and 0 <= point.y < compiled.height):
                issues.append(_issue("error", "collision_out_of_bounds", f"Object {item.id!r} collision leaves map.", compiled.map_id, point))
    for spawn in compiled.spawns:
        cell = (spawn.position.x, spawn.position.y)
        if cell in blocked:
            issues.append(_issue("error", "spawn_in_collision", f"Spawn {spawn.id!r} is blocked.", compiled.map_id, spawn.position))
    for transition in compiled.transitions:
        overlap = _rect_cells(transition.rect) & blocked
        if overlap:
            point = Point(x=min(overlap)[0], y=min(overlap)[1])
            issues.append(_issue("error", "transition_in_collision", f"Transition {transition.id!r} is blocked.", compiled.map_id, point))
    for item in compiled.objects:
        if item.transition_id:
            linked_transition = next(
                (entry for entry in compiled.transitions if entry.id == item.transition_id), None
            )
            if linked_transition is None:
                issues.append(_issue("error", "missing_object_transition", f"Object {item.id!r} refers to absent transition.", compiled.map_id, item.position))
            elif _rect_cells(linked_transition.rect) & blocked:
                issues.append(_issue("error", "blocked_doorway", f"Doorway for {item.id!r} is blocked.", compiled.map_id, item.position))
        if item.interaction_id and not any(entry.id == item.interaction_id for entry in compiled.interactions):
            issues.append(_issue("error", "missing_object_interaction", f"Object {item.id!r} refers to absent interaction.", compiled.map_id, item.position))

    critical: list[tuple[str, tuple[int, int]]] = []
    critical.extend((f"spawn {item.id}", (item.position.x, item.position.y)) for item in compiled.spawns if item.required)
    critical.extend((f"transition {item.id}", _center(item.rect)) for item in compiled.transitions if item.mandatory)
    critical.extend((f"landmark {item.id}", (item.position.x, item.position.y)) for item in compiled.landmarks if item.required)
    critical.extend((f"interaction {item.id}", (item.position.x, item.position.y)) for item in compiled.interactions)
    if critical:
        reachable = _bfs(compiled, critical[0][1])
        for label, cell in critical:
            if cell not in reachable:
                issues.append(_issue("error", "unreachable_critical", f"{label.capitalize()} cannot reach the critical path.", compiled.map_id, Point(x=cell[0], y=cell[1])))
        for spawn in compiled.spawns:
            if spawn.kind == "npc" and spawn.required and (spawn.position.x, spawn.position.y) not in reachable:
                issues.append(_issue("error", "unreachable_npc", f"Mandatory NPC {spawn.id!r} is unreachable.", compiled.map_id, spawn.position))

    total = compiled.width * compiled.height
    object_fraction = len(collision_owner) / total
    open_fraction = sum(row.count(".") for row in compiled.walkability) / total
    density = bundle.bible.density
    if object_fraction > density.max_prop_fraction:
        issues.append(_issue("warning", "excessive_prop_density", f"Collision props cover {object_fraction:.1%} of the map.", compiled.map_id))
    if open_fraction < density.min_open_fraction:
        issues.append(_issue("warning", "insufficient_open_space", f"Only {open_fraction:.1%} of the map is walkable.", compiled.map_id))
    authored_and_generated = len(compiled.objects) + len(compiled.decorative_layers)
    if compiled.map_type != "interior" and authored_and_generated < total * 0.01:
        issues.append(_issue("warning", "excessive_empty_space", "Map has very little visual punctuation.", compiled.map_id))

    safe_cells: set[tuple[int, int]] = set()
    encounter_cells: set[tuple[int, int]] = set()
    for zone in compiled.zones:
        if zone.kind == "safe":
            safe_cells.update(_rect_cells(zone.rect))
        elif zone.kind == "encounter":
            encounter_cells.update(_rect_cells(zone.rect))
    if safe_cells & encounter_cells:
        issues.append(_issue("warning", "encounter_over_safe_zone", "An encounter zone overlaps a safe zone.", compiled.map_id))

    source_spec = bundle.maps[compiled.map_id]
    for path in source_spec.paths:
        for path_left, path_right in zip(path.points, path.points[1:], strict=False):
            segment_length = abs(path_left.x - path_right.x) + abs(path_left.y - path_right.y)
            if segment_length > density.max_featureless_path:
                issues.append(
                    _issue(
                        "warning",
                        "long_featureless_path",
                        f"Path {path.id!r} has a {segment_length}-tile segment without an authored bend.",
                        compiled.map_id,
                        path_left,
                    )
                )
    if compiled.map_type != "interior" and authored_and_generated >= 8:
        visual_families = {
            item.archetype_id for item in compiled.objects + compiled.decorative_layers
        }
        if len(visual_families) < 2:
            issues.append(
                _issue(
                    "warning",
                    "insufficient_visual_variation",
                    "Outdoor map uses fewer than two object archetypes.",
                    compiled.map_id,
                )
            )
    path_terrain_ids = {
        path.terrain_id or bundle.bible.biome_by_id()[compiled.biome].path_terrain
        for path in source_spec.paths
    }
    path_cells = {
        (x, y)
        for y, row in enumerate(compiled.terrain)
        for x, terrain_id in enumerate(row)
        if terrain_id in path_terrain_ids
    }
    if path_cells:
        for item in compiled.objects:
            if item.transition_id and "building" in item.tags:
                distance = min(
                    abs(item.position.x - x) + abs(item.position.y - y)
                    for x, y in path_cells
                )
                if distance > 6:
                    issues.append(
                        _issue(
                            "warning",
                            "door_far_from_route",
                            f"Door {item.id!r} is {distance} tiles from the authored route.",
                            compiled.map_id,
                            item.position,
                        )
                    )

    required_landmarks = [item for item in compiled.landmarks if item.required]
    for index, left in enumerate(required_landmarks):
        for right in required_landmarks[index + 1 :]:
            distance = abs(left.position.x - right.position.x) + abs(left.position.y - right.position.y)
            if distance < density.landmark_min_distance:
                issues.append(_issue("warning", "landmarks_too_close", f"Landmarks {left.id!r} and {right.id!r} are only {distance} tiles apart.", compiled.map_id))
    return issues


def build_report(issues: Iterable[Diagnostic], maps: Iterable[CompiledMap] = ()) -> ValidationReport:
    issue_list = list(issues)
    errors = sum(item.severity == "error" for item in issue_list)
    warnings = sum(item.severity == "warning" for item in issue_list)
    return ValidationReport(
        success=errors == 0,
        errors=errors,
        warnings=warnings,
        issues=issue_list,
        map_hashes={item.map_id: item.canonical_hash for item in sorted(maps, key=lambda m: m.map_id)},
    )


def report_text(report: ValidationReport) -> str:
    status = "PASS" if report.success else "FAIL"
    lines = [f"WorldSynth validation: {status}", f"Errors: {report.errors}  Warnings: {report.warnings}"]
    for issue in report.issues:
        location = f" ({issue.location.x},{issue.location.y})" if issue.location else ""
        scope = f"[{issue.map_id}] " if issue.map_id else ""
        lines.append(f"{issue.severity.upper():7} {issue.code}: {scope}{issue.message}{location}")
    if not report.issues:
        lines.append("No issues.")
    if report.map_hashes:
        lines.append("Map hashes:")
        lines.extend(f"  {map_id}: {hash_value}" for map_id, hash_value in report.map_hashes.items())
    return "\n".join(lines) + "\n"

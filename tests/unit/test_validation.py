from __future__ import annotations

from dataclasses import replace

from worldsynth.domain.models import CompiledObject, Point
from worldsynth.generation.generator import compile_layout
from worldsynth.schemas.loader import ContentBundle
from worldsynth.validation.validators import validate_compiled_map, validate_sources


def _codes(issues: list[object]) -> set[str]:
    return {issue.code for issue in issues}  # type: ignore[attr-defined]


def test_edge_contract_mismatch_is_detected(bundle: ContentBundle) -> None:
    maps = {key: value.model_copy(deep=True) for key, value in bundle.maps.items()}
    maps["mosswood_route"].edge_contracts[0].width = 2
    changed = replace(bundle, maps=maps)
    assert "edge_contract_mismatch" in _codes(validate_sources(changed))


def test_invalid_transition_reference_is_detected(bundle: ContentBundle) -> None:
    maps = {key: value.model_copy(deep=True) for key, value in bundle.maps.items()}
    maps["tavern_interior"].transitions[0].target_transition = "missing_door"
    changed = replace(bundle, maps=maps)
    codes = _codes(validate_sources(changed))
    assert "bad_transition_target" in codes
    assert "contradictory_transition" in codes


def test_out_of_bounds_object_is_detected(bundle: ContentBundle) -> None:
    maps = {key: value.model_copy(deep=True) for key, value in bundle.maps.items()}
    maps["lanternmarket"].props[0].position = Point(x=99, y=99)
    changed = replace(bundle, maps=maps)
    assert "object_out_of_bounds" in _codes(validate_sources(changed))


def test_forbidden_collision_overlap_is_detected(bundle: ContentBundle) -> None:
    compiled = compile_layout(bundle, bundle.maps["lanternmarket"])
    original = compiled.objects[0]
    duplicate = CompiledObject.model_validate(
        {**original.model_dump(mode="json"), "id": "overlapping_clone"}
    )
    compiled.objects.append(duplicate)
    assert "forbidden_overlap" in _codes(validate_compiled_map(compiled, bundle))


def test_spawn_and_door_collision_are_detected(bundle: ContentBundle) -> None:
    compiled = compile_layout(bundle, bundle.maps["tavern_interior"])
    spawn = compiled.spawns[0].position
    compiled.blocked_cells.append(spawn)
    row = list(compiled.walkability[spawn.y])
    row[spawn.x] = "#"
    compiled.walkability[spawn.y] = "".join(row)
    assert "spawn_in_collision" in _codes(validate_compiled_map(compiled, bundle))

    town = compile_layout(bundle, bundle.maps["lanternmarket"])
    door = town.transitions[2].rect.cells()[0]
    town.blocked_cells.append(door)
    door_row = list(town.walkability[door.y])
    door_row[door.x] = "#"
    town.walkability[door.y] = "".join(door_row)
    codes = _codes(validate_compiled_map(town, bundle))
    assert "transition_in_collision" in codes
    assert "blocked_doorway" in codes


def test_connectivity_validator_finds_partition(bundle: ContentBundle) -> None:
    compiled = compile_layout(bundle, bundle.maps["sunmeadow_route"])
    wall_x = 3
    for y in range(compiled.height):
        point = Point(x=wall_x, y=y)
        compiled.blocked_cells.append(point)
        row = list(compiled.walkability[y])
        row[wall_x] = "#"
        compiled.walkability[y] = "".join(row)
    assert "unreachable_critical" in _codes(validate_compiled_map(compiled, bundle))


def test_sample_world_all_critical_points_reachable(bundle: ContentBundle) -> None:
    for spec in bundle.maps.values():
        compiled = compile_layout(bundle, spec)
        assert "unreachable_critical" not in _codes(validate_compiled_map(compiled, bundle))

from __future__ import annotations

from worldsynth.domain.models import Point
from worldsynth.generation.generator import (
    compile_layout,
    footprint_cells,
    protected_decoration_cells,
    rasterize_path,
)
from worldsynth.schemas.loader import ContentBundle


def test_generation_is_deterministic(bundle: ContentBundle) -> None:
    spec = bundle.maps["mosswood_route"]
    first = compile_layout(bundle, spec)
    second = compile_layout(bundle, spec)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.canonical_hash == second.canonical_hash


def test_seed_changes_bounded_filling_not_authored_topology(bundle: ContentBundle) -> None:
    spec = bundle.maps["mosswood_route"]
    first = compile_layout(bundle, spec, seed=10)
    second = compile_layout(bundle, spec, seed=11)
    assert first.canonical_hash != second.canonical_hash
    assert first.transitions == second.transitions
    assert first.objects == second.objects
    assert [item.position for item in first.decorative_layers] != [
        item.position for item in second.decorative_layers
    ]


def test_path_rasterization_keeps_authored_endpoints(bundle: ContentBundle) -> None:
    spec = bundle.maps["lanternmarket"]
    cells = rasterize_path(spec, 0, spec.seed)
    path = spec.paths[0]
    assert (path.points[0].x, path.points[0].y) in cells
    assert (path.points[-1].x, path.points[-1].y) in cells


def test_doorway_socket_is_removed_from_collision(bundle: ContentBundle) -> None:
    archetype = bundle.assets.by_id()["tavern_house"]
    placement = bundle.maps["lanternmarket"].structures[0]
    collision = footprint_cells(archetype, placement.position)
    assert (placement.position.x, placement.position.y) not in collision
    assert (placement.position.x - 1, placement.position.y) in collision


def test_destination_spawn_does_not_protect_source_map_cell(bundle: ContentBundle) -> None:
    spec = bundle.maps["lanternmarket"].model_copy(deep=True)
    destination_only = Point(x=37, y=26)
    spec.transitions[0].target_spawn = destination_only
    protected = protected_decoration_cells(spec, path_cells=set())
    assert (destination_only.x, destination_only.y) not in protected
    transition_cell = spec.transitions[0].rect.cells()[0]
    assert (transition_cell.x, transition_cell.y) in protected


def test_canonical_hash_snapshot(bundle: ContentBundle) -> None:
    expected = {
        "alchemist_interior": "96829bf1f600cfc2d922f031faae6b33f2190b9c19df0b1c3395e51c229ff524",
        "echo_cave": "0828a38280960ae80e8a6758128f90d958912e34983b25b4af15e69adedc6844",
        "lanternmarket": "b1f23826ad2906342a5b95d1c5cef520f21e9ad83ac73e95668357f7a7d214c8",
        "mosswood_route": "643004b93b22a9296f8ebc044dfe0a42fd630880f9f4479ff6e16b6afc03fc81",
        "research_lodge_interior": "1c56a778d40306f6056f550de653c10aa1eaa3f746e52220fcf94008c2e40258",
        "sunmeadow_route": "b97f6229450c8137e972d78c4c449ceea6ac166e55967614a55670914d9a646d",
        "tavern_interior": "e8ddcbee03ee7c1aa72062d36b09b92c6edb822b403b7c7f84b2abd3769a89b4",
    }
    actual = {
        map_id: compile_layout(bundle, spec).canonical_hash for map_id, spec in bundle.maps.items()
    }
    assert actual == expected

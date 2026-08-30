from __future__ import annotations

from worldsynth.generation.generator import compile_layout, footprint_cells, rasterize_path
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


def test_canonical_hash_snapshot(bundle: ContentBundle) -> None:
    expected = {
        "alchemist_interior": "2043bb5af6953b02b54192ac8e661923849f6057493ac4e54a277084a969b902",
        "echo_cave": "52ee569d7657e3a605ee540433a8144812e9e2c3345cae492733b82a42d3e813",
        "lanternmarket": "0830f501c5287dc5c71bf25f508c17116e17255a29e09b3d057c9869a4729be5",
        "mosswood_route": "e9a7daac6670c07081e3d76f2095b904a48f836b0dedcd8ab2b06d5ba83eacc2",
        "research_lodge_interior": "a8fee66b65a3ca57df32b6d7dba2b368fe93388f990eb5dcc39dade352a74af2",
        "sunmeadow_route": "d223764b83dfb9fb94cf6964e84357a602e911c65ac6979332fb491042ca38e4",
        "tavern_interior": "0474d34df0f4047dc508c8e41c90c2c7f7c81b759674af7e57d3aa6e6077eb23",
    }
    actual = {
        map_id: compile_layout(bundle, spec).canonical_hash
        for map_id, spec in bundle.maps.items()
    }
    assert actual == expected

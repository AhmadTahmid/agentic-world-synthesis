from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldsynth.domain.models import AssetArchetype
from worldsynth.generation.generator import (
    adjacency_mask,
    compile_layout,
    merge_blocked_cells,
)
from worldsynth.schemas.loader import ContentBundle
from worldsynth.validation.validators import validate_sources


def test_cardinal_adjacency_mask_convention() -> None:
    isolated = [["grass"]]
    assert adjacency_mask(isolated, 0, 0, "grass") == 0

    block = [["grass"] * 3 for _ in range(3)]
    assert adjacency_mask(block, 1, 1, "grass") == 15
    assert adjacency_mask(block, 0, 0, "grass") == 6  # east + south

    corner = [
        ["grass", "grass", "water"],
        ["water", "grass", "water"],
        ["water", "water", "water"],
    ]
    assert adjacency_mask(corner, 1, 1, "grass") == 1  # north only


def test_visual_variants_and_grammar_are_deterministic(bundle: ContentBundle) -> None:
    spec = bundle.maps["lanternmarket"]
    first = compile_layout(bundle, spec)
    second = compile_layout(bundle, spec)
    assert first.render_layers == second.render_layers
    assert first.composition_decisions == second.composition_decisions
    assert [item.variant_id for item in first.decorative_layers] == [
        item.variant_id for item in second.decorative_layers
    ]
    assert {item.grammar_id for item in first.decorative_layers} <= {
        "vegetation_cluster",
        "roadside",
    }


def test_visual_grammar_enforces_protected_areas(bundle: ContentBundle) -> None:
    compiled = compile_layout(bundle, bundle.maps["lanternmarket"])
    protected = {(point.x, point.y) for point in compiled.protected_visual_cells}
    generated_collision = {
        (cell.x, cell.y) for item in compiled.decorative_layers for cell in item.collision_cells
    }
    assert protected.isdisjoint(generated_collision)
    assert {item.grammar for item in compiled.composition_decisions} >= {
        "landmark_clearing",
        "building_setback",
        "sightline",
        "door_clearance",
        "intersection_clearance",
        "roadside",
        "vegetation_cluster",
    }


def test_layered_archetype_requires_unique_functional_layers(
    bundle: ContentBundle,
) -> None:
    tree = bundle.assets.by_id()["broadleaf_tree"]
    assert [layer.role for layer in tree.visual_layers] == ["shadow", "base", "foreground"]
    invalid = tree.model_dump(mode="json")
    invalid["visual_layers"] = [
        {
            "role": "shadow",
            "asset_path": "assets/objects/layers/tree_shadow.svg",
            "pixel_size": {"width": 96, "height": 128},
        }
    ]
    with pytest.raises(ValidationError, match="base or main"):
        AssetArchetype.model_validate(invalid)


def test_collision_merging_preserves_cells_and_reduces_shapes() -> None:
    blocked = {(x, y) for y in range(3) for x in range(5)} | {(8, 1), (8, 2)}
    rectangles = merge_blocked_cells(blocked, width=10, height=4)
    reconstructed = {(point.x, point.y) for rectangle in rectangles for point in rectangle.cells()}
    assert reconstructed == blocked
    assert len(rectangles) == 2
    assert len(rectangles) < len(blocked)


def test_lanternmarket_render_diagnostics_cover_layers(bundle: ContentBundle) -> None:
    compiled = compile_layout(bundle, bundle.maps["lanternmarket"])
    assert compiled.render_stats is not None
    assert compiled.render_stats.blocked_cell_count == len(compiled.blocked_cells)
    assert compiled.render_stats.collision_shape_count == len(compiled.collision_rects)
    assert compiled.render_stats.collision_reduction_ratio > 1
    assert set(compiled.render_stats.tile_layer_counts) >= {
        "base",
        "terrain_transitions",
        "paths",
        "ground_decals",
        "water",
    }
    assert compiled.render_stats.object_layer_counts["static_structures"] == 3
    assert compiled.render_stats.object_layer_counts["y_sorted_entities_props"] > 0


def test_visual_asset_paths_and_licenses_validate(bundle: ContentBundle) -> None:
    visual_issues = [
        issue
        for issue in validate_sources(bundle)
        if issue.code
        in {
            "missing_asset_file",
            "missing_terrain_visual",
            "terrain_scale_mismatch",
            "terrain_movement_mismatch",
        }
    ]
    assert visual_issues == []
    assert all(terrain.license.license for terrain in bundle.assets.terrains)


def test_compiled_format_one_remains_backward_compatible(bundle: ContentBundle) -> None:
    compiled = compile_layout(bundle, bundle.maps["lanternmarket"])
    legacy = compiled.model_dump(mode="json")
    for field in (
        "render_layers",
        "protected_visual_cells",
        "composition_decisions",
        "collision_rects",
        "render_stats",
    ):
        legacy.pop(field)
    reparsed = type(compiled).model_validate(legacy)
    assert reparsed.format_version == 1
    assert reparsed.render_layers == {}
    assert reparsed.collision_rects == []

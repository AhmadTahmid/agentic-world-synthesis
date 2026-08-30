from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from worldsynth.domain.models import (
    CollisionFootprint,
    CollisionKind,
    Dimensions,
    MapSpec,
)
from worldsynth.schemas.loader import ContentBundle
from worldsynth.validation.validators import validate_sources


def test_collision_rect_requires_payload() -> None:
    with pytest.raises(ValidationError, match="rect collision requires rect"):
        CollisionFootprint(kind=CollisionKind.RECT)


def test_map_dimensions_reject_tiny_map() -> None:
    with pytest.raises(ValidationError):
        Dimensions(width=5, height=12)


def test_unknown_fields_are_rejected(bundle: ContentBundle) -> None:
    raw = bundle.maps["lanternmarket"].model_dump(mode="json")
    raw["opaque_generator_magic"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        MapSpec.model_validate(raw)


def test_missing_asset_file_is_blocking(bundle: ContentBundle, tmp_path: Path) -> None:
    missing_root = replace(bundle, root=tmp_path)
    codes = {issue.code for issue in validate_sources(missing_root)}
    assert "missing_asset_file" in codes


def test_registry_tile_scale_is_checked(bundle: ContentBundle) -> None:
    # ContentBundle is a dataclass; copy the registry independently.
    assets = bundle.assets.model_copy(deep=True)
    assets.archetypes[0].pixel_size.width += 1
    changed = replace(bundle, assets=assets)
    codes = {issue.code for issue in validate_sources(changed)}
    assert "asset_scale_mismatch" in codes

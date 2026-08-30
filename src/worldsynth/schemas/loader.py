from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from worldsynth.domain.models import AssetRegistry, MapSpec, WorldBible, WorldGraph

ModelT = TypeVar("ModelT", bound=BaseModel)


class ContentError(RuntimeError):
    """An actionable error while loading canonical authoring data."""


@dataclass(frozen=True)
class ContentBundle:
    root: Path
    bible: WorldBible
    graph: WorldGraph
    assets: AssetRegistry
    maps: dict[str, MapSpec]
    map_paths: dict[str, Path]


def _read_yaml(path: Path, model: type[ModelT]) -> ModelT:
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContentError(f"Could not read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ContentError(f"Malformed YAML in {path}: {exc}") from exc
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        raise ContentError(f"Schema validation failed for {path}:\n{exc}") from exc


def load_bundle(root: Path | str = Path(".")) -> ContentBundle:
    resolved = Path(root).resolve()
    content = resolved / "content"
    bible = _read_yaml(content / "world_bible.yaml", WorldBible)
    graph = _read_yaml(content / "world_graph.yaml", WorldGraph)
    assets = _read_yaml(content / "asset_registry.yaml", AssetRegistry)
    if bible.tile_size != assets.tile_size:
        raise ContentError(
            f"Tile scale mismatch: world bible={bible.tile_size}, registry={assets.tile_size}"
        )
    map_paths = sorted((content / "maps").glob("*.yaml")) + sorted(
        (content / "interiors").glob("*.yaml")
    )
    maps: dict[str, MapSpec] = {}
    sources: dict[str, Path] = {}
    for path in map_paths:
        spec = _read_yaml(path, MapSpec)
        if spec.map_id in maps:
            raise ContentError(
                f"Duplicate map ID {spec.map_id!r} in {path} and {sources[spec.map_id]}"
            )
        maps[spec.map_id] = spec
        sources[spec.map_id] = path
    if not maps:
        raise ContentError(f"No map specifications found under {content}")
    return ContentBundle(resolved, bible, graph, assets, maps, sources)

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from worldsynth import GENERATOR_VERSION
from worldsynth.domain.models import CompiledMap, Diagnostic, ValidationReport
from worldsynth.generation.generator import compile_layout
from worldsynth.rendering.preview import render_preview
from worldsynth.schemas.loader import ContentBundle, load_bundle
from worldsynth.util import canonical_json, content_hash, write_text_if_changed
from worldsynth.validation.validators import (
    build_report,
    report_text,
    validate_compiled_map,
    validate_sources,
)


@dataclass(frozen=True)
class BuildResult:
    bundle: ContentBundle
    maps: dict[str, CompiledMap]
    report: ValidationReport


def compile_bundle(
    bundle: ContentBundle,
    *,
    only_map: str | None = None,
    seed_override: int | None = None,
) -> BuildResult:
    source_issues = validate_sources(bundle, only_map=only_map)
    if any(issue.severity == "error" for issue in source_issues):
        return BuildResult(bundle=bundle, maps={}, report=build_report(source_issues))
    selected = {
        map_id: spec
        for map_id, spec in bundle.maps.items()
        if only_map is None or map_id == only_map
    }
    if only_map is not None and not selected:
        issue = Diagnostic(
            severity="error",
            code="unknown_map",
            message=f"No authored map has ID {only_map!r}.",
        )
        return BuildResult(bundle=bundle, maps={}, report=build_report([*source_issues, issue]))
    compiled = {
        map_id: compile_layout(bundle, spec, seed_override)
        for map_id, spec in sorted(selected.items())
    }
    issues = list(source_issues)
    for compiled_map in compiled.values():
        issues.extend(validate_compiled_map(compiled_map, bundle))
    return BuildResult(bundle=bundle, maps=compiled, report=build_report(issues, compiled.values()))


def _write_outputs(result: BuildResult, *, previews: bool = True) -> None:
    root = result.bundle.root
    report_json = canonical_json(result.report, pretty=True)
    write_text_if_changed(root / "generated" / "reports" / "validation.json", report_json)
    write_text_if_changed(
        root / "generated" / "reports" / "validation.txt", report_text(result.report)
    )
    # Preserve last-known-good runtime maps/manifests when source validation fails.
    if not result.report.success:
        return
    generated_maps = root / "generated" / "maps"
    game_maps = root / "game" / "generated" / "maps"
    for compiled in result.maps.values():
        text = canonical_json(compiled, pretty=True)
        write_text_if_changed(generated_maps / f"{compiled.map_id}.json", text)
        write_text_if_changed(game_maps / f"{compiled.map_id}.json", text)
        if previews:
            render_preview(
                compiled,
                result.bundle.bible,
                root / "generated" / "previews" / f"{compiled.map_id}.png",
            )
    manifest = {
        "format_version": 1,
        "generator_version": GENERATOR_VERSION,
        "world_id": result.bundle.bible.world_id,
        "world_title": result.bundle.bible.title,
        "start_map": result.bundle.graph.start_map,
        "maps": {
            map_id: {"path": f"maps/{map_id}.json", "canonical_hash": item.canonical_hash}
            for map_id, item in sorted(result.maps.items())
        },
        "source_bundle_hash": content_hash(
            {
                "bible": result.bundle.bible,
                "graph": result.bundle.graph,
                "assets": result.bundle.assets,
                "maps": result.bundle.maps,
                "generator_version": GENERATOR_VERSION,
            }
        ),
        "reproducible": True,
    }
    manifest_text = canonical_json(manifest, pretty=True)
    write_text_if_changed(root / "generated" / "manifests" / "world_manifest.json", manifest_text)
    write_text_if_changed(root / "game" / "generated" / "world_manifest.json", manifest_text)
    for reference in sorted(
        {ref for compiled in result.maps.values() for ref in compiled.asset_references}
    ):
        archetype = result.bundle.assets.by_id().get(reference)
        if archetype is None:
            continue
        source = root / archetype.asset_path
        relative = Path(archetype.asset_path)
        if relative.parts and relative.parts[0] == "assets":
            relative = Path(*relative.parts[1:])
        target = root / "game" / "assets" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def build_project(root: Path | str = Path("."), *, write: bool = True) -> BuildResult:
    bundle = load_bundle(root)
    result = compile_bundle(bundle)
    if write:
        _write_outputs(result)
    return result


def write_single_map(result: BuildResult, *, preview: bool = True) -> None:
    """Write a seed-review artifact without mutating the canonical Godot manifest."""
    if not result.report.success:
        return
    root = result.bundle.root
    for compiled in result.maps.values():
        write_text_if_changed(
            root / "generated" / "maps" / f"{compiled.map_id}.json",
            canonical_json(compiled, pretty=True),
        )
        if preview:
            render_preview(
                compiled,
                result.bundle.bible,
                root / "generated" / "previews" / f"{compiled.map_id}.png",
            )

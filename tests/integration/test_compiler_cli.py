from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from worldsynth.cli import app
from worldsynth.compilation.compiler import build_project, compile_bundle, write_single_map
from worldsynth.domain.models import CompiledMap
from worldsynth.providers.interfaces import RuleBasedPlanner
from worldsynth.schemas.loader import ContentBundle, load_bundle

runner = CliRunner()


def _copy_project_inputs(source: Path, target: Path) -> None:
    shutil.copytree(source / "content", target / "content")
    shutil.copytree(source / "assets", target / "assets")
    (target / "game").mkdir(parents=True)


def test_full_build_writes_runtime_previews_and_reports(repo_root: Path, tmp_path: Path) -> None:
    _copy_project_inputs(repo_root, tmp_path)
    first = build_project(tmp_path)
    assert first.report.success
    assert len(first.maps) == 7
    map_path = tmp_path / "game" / "generated" / "maps" / "lanternmarket.json"
    first_bytes = map_path.read_bytes()
    manifest = json.loads(
        (tmp_path / "game" / "generated" / "world_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["start_map"] == "lanternmarket"
    assert manifest["player_visual"]["id"] == "lumen_scout"
    assert "assets/tiles/lumenfold_terrain_atlas.svg" in manifest["asset_content_hashes"]
    assert (tmp_path / "game" / "assets" / "tiles" / "lumenfold_terrain_atlas.svg").is_file()
    assert (tmp_path / "game" / "assets" / "characters" / "lumen_scout.svg").is_file()
    assert (tmp_path / "generated" / "previews" / "echo_cave.png").is_file()
    assert (tmp_path / "generated" / "reports" / "validation.txt").is_file()
    second = build_project(tmp_path)
    assert second.report.map_hashes == first.report.map_hashes
    assert map_path.read_bytes() == first_bytes


def test_review_generation_does_not_replace_game_manifest(repo_root: Path, tmp_path: Path) -> None:
    _copy_project_inputs(repo_root, tmp_path)
    build_project(tmp_path)
    manifest_path = tmp_path / "game" / "generated" / "world_manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    bundle = load_bundle(tmp_path)
    review = compile_bundle(bundle, only_map="mosswood_route", seed_override=999)
    write_single_map(review)
    assert manifest_path.read_bytes() == manifest_bytes
    game_map = tmp_path / "game" / "generated" / "maps" / "mosswood_route.json"
    assert '"seed": 7729' in game_map.read_text(encoding="utf-8")


def test_failed_build_preserves_last_known_good_manifest(repo_root: Path, tmp_path: Path) -> None:
    _copy_project_inputs(repo_root, tmp_path)
    build_project(tmp_path)
    manifest_path = tmp_path / "game" / "generated" / "world_manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    graph_path = tmp_path / "content" / "world_graph.yaml"
    graph_path.write_text(
        graph_path.read_text(encoding="utf-8").replace(
            "to_transition: market_gate", "to_transition: missing_gate", 1
        ),
        encoding="utf-8",
    )
    failed = build_project(tmp_path)
    assert not failed.report.success
    assert manifest_path.read_bytes() == manifest_bytes
    assert "missing_transition_reference" in (
        tmp_path / "generated" / "reports" / "validation.txt"
    ).read_text(encoding="utf-8")


def test_cli_smoke_commands(repo_root: Path) -> None:
    listed = runner.invoke(app, ["list-maps", "--root", str(repo_root)])
    assert listed.exit_code == 0, listed.output
    assert "lanternmarket" in listed.output
    validated = runner.invoke(app, ["validate-map", "echo_cave", "--root", str(repo_root)])
    assert validated.exit_code == 0, validated.output
    inspected = runner.invoke(app, ["inspect", "sunmeadow_route", "--root", str(repo_root)])
    assert inspected.exit_code == 0, inspected.output
    assert "canonical_hash=" in inspected.output


def test_cli_returns_nonzero_on_blocking_reference_error(repo_root: Path, tmp_path: Path) -> None:
    _copy_project_inputs(repo_root, tmp_path)
    graph_path = tmp_path / "content" / "world_graph.yaml"
    graph_path.write_text(
        graph_path.read_text(encoding="utf-8").replace(
            "to_transition: market_gate", "to_transition: absent_gate", 1
        ),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["validate", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "missing_transition_reference" in result.output


def test_malformed_compiled_map_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CompiledMap.model_validate({"format_version": 1, "map_id": "broken"})


def test_offline_planner_produces_typed_candidate(bundle: ContentBundle) -> None:
    planned = RuleBasedPlanner().plan_map("quiet moon orchard", bundle.bible, seed=44)
    assert planned.map_id == "planned_quiet_moon_orchard"
    assert planned.seed == 44
    assert planned.transitions[0].target_map == "placeholder_neighbor"

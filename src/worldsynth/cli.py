from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Annotated, Never

import typer

from worldsynth.compilation.compiler import (
    build_project,
    compile_bundle,
    write_single_map,
)
from worldsynth.rendering.preview import DEFAULT_OVERLAYS, render_preview
from worldsynth.schemas.loader import ContentBundle, ContentError, load_bundle
from worldsynth.util import canonical_json
from worldsynth.validation.validators import report_text

app = typer.Typer(
    name="worldsynth",
    help="Compile authored symbolic world specifications into deterministic Godot runtime maps.",
    no_args_is_help=True,
)
RootOption = Annotated[Path, typer.Option("--root", help="Repository root.")]


def _fail(message: str, code: int = 1) -> Never:
    typer.echo(message, err=True)
    raise typer.Exit(code)


def _load(root: Path) -> ContentBundle:
    try:
        return load_bundle(root)
    except ContentError as exc:
        _fail(str(exc), 2)


@app.command("list-maps")
def list_maps(root: RootOption = Path(".")) -> None:
    """List canonical authored maps."""
    bundle = _load(root)
    for map_id, spec in sorted(bundle.maps.items()):
        typer.echo(f"{map_id:24} {spec.map_type:10} {spec.dimensions.width}x{spec.dimensions.height}  {spec.display_name}")


@app.command()
def validate(root: RootOption = Path(".")) -> None:
    """Validate the full source bundle and generated playability in memory."""
    bundle = _load(root)
    result = compile_bundle(bundle)
    typer.echo(report_text(result.report), nl=False)
    if not result.report.success:
        raise typer.Exit(1)


@app.command("validate-map")
def validate_map(map_id: str, root: RootOption = Path(".")) -> None:
    """Validate one map while still resolving world-level references."""
    bundle = _load(root)
    result = compile_bundle(bundle, only_map=map_id)
    typer.echo(report_text(result.report), nl=False)
    if not result.report.success:
        raise typer.Exit(1)


@app.command()
def build(root: RootOption = Path(".")) -> None:
    """Validate, compile, preview, report, and synchronize the Godot data."""
    try:
        result = build_project(root)
    except ContentError as exc:
        _fail(str(exc), 2)
    typer.echo(report_text(result.report), nl=False)
    if not result.report.success:
        raise typer.Exit(1)
    typer.echo(f"Built {len(result.maps)} maps into generated/ and game/generated/.")


@app.command()
def generate(
    map_id: str,
    seed: Annotated[int | None, typer.Option("--seed", help="Override the authored seed.")] = None,
    root: RootOption = Path("."),
) -> None:
    """Compile one map, optionally with a bounded deterministic seed override."""
    bundle = _load(root)
    result = compile_bundle(bundle, only_map=map_id, seed_override=seed)
    if result.report.success:
        write_single_map(result)
    typer.echo(report_text(result.report), nl=False)
    if not result.report.success:
        raise typer.Exit(1)


@app.command()
def preview(
    map_id: str,
    overlays: Annotated[
        str,
        typer.Option(help="Comma-separated overlays: objects,collision,walkability,zones,spawns,transitions,landmarks,edges or none."),
    ] = ",".join(sorted(DEFAULT_OVERLAYS)),
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    root: RootOption = Path("."),
) -> None:
    """Render a static diagnostic preview with selectable overlays."""
    bundle = _load(root)
    result = compile_bundle(bundle, only_map=map_id)
    if not result.report.success:
        _fail(report_text(result.report))
    selected = set() if overlays.strip().lower() == "none" else {part.strip() for part in overlays.split(",") if part.strip()}
    valid = DEFAULT_OVERLAYS | {"walkability"}
    unknown = selected - valid
    if unknown:
        _fail(f"Unknown overlays: {', '.join(sorted(unknown))}", 2)
    target = output or bundle.root / "generated" / "previews" / f"{map_id}.png"
    render_preview(result.maps[map_id], bundle.bible, target, overlays=selected)
    typer.echo(str(target.resolve()))


@app.command()
def inspect(
    map_id: str,
    as_json: Annotated[bool, typer.Option("--json", help="Print normalized compiled JSON.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Inspect derived semantics without writing build products."""
    bundle = _load(root)
    result = compile_bundle(bundle, only_map=map_id)
    if not result.report.success:
        _fail(report_text(result.report))
    compiled = result.maps[map_id]
    if as_json:
        typer.echo(canonical_json(compiled, pretty=True), nl=False)
        return
    counts = {
        "authored_objects": len(compiled.objects),
        "generated_decorations": len(compiled.decorative_layers),
        "blocked_cells": len(compiled.blocked_cells),
        "transitions": len(compiled.transitions),
        "interactions": len(compiled.interactions),
        "encounter_zones": sum(zone.kind == "encounter" for zone in compiled.zones),
    }
    typer.echo(f"{compiled.display_name} [{compiled.map_id}] {compiled.width}x{compiled.height} seed={compiled.seed}")
    typer.echo(f"canonical_hash={compiled.canonical_hash}")
    typer.echo(json.dumps(counts, indent=2, sort_keys=True))
    typer.echo("Walkability (# blocked, . open):")
    typer.echo("\n".join(compiled.walkability))


@app.command("clean-generated")
def clean_generated(
    yes: Annotated[bool, typer.Option("--yes", help="Confirm removal of generated build products.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Safely remove only known generated directories; canonical content is untouched."""
    resolved = root.resolve()
    targets = [resolved / "generated", resolved / "game" / "generated"]
    if not yes:
        _fail("Refusing to remove build products without --yes.", 2)
    for target in targets:
        checked = target.resolve()
        allowed = checked == resolved / "generated" or checked == resolved / "game" / "generated"
        if not allowed or resolved == checked or resolved not in checked.parents:
            _fail(f"Unsafe generated target: {checked}", 2)
    for target in targets:
        if target.exists():
            shutil.rmtree(target)
            typer.echo(f"Removed {target} (recreatable with worldsynth build).")


if __name__ == "__main__":
    app()

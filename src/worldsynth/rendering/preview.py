from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from worldsynth.domain.models import CompiledMap, Rect, WorldBible

DEFAULT_OVERLAYS = {
    "objects",
    "collision",
    "zones",
    "spawns",
    "transitions",
    "landmarks",
    "edges",
}

FALLBACK_COLORS = {
    "grass": "#6f9f58",
    "forest_floor": "#527346",
    "meadow": "#95b85d",
    "stone_floor": "#777b77",
    "wood_floor": "#b68b59",
    "path": "#c8ad78",
    "dirt_path": "#a88957",
    "water": "#4d88a8",
    "wall": "#353d3c",
    "void": "#171b22",
}


def _tile_rect(x: int, y: int, scale: int) -> tuple[int, int, int, int]:
    return (x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1)


def _world_rect(rect: Rect, scale: int) -> tuple[int, int, int, int]:
    return (
        rect.x * scale,
        rect.y * scale,
        (rect.x + rect.width) * scale - 1,
        (rect.y + rect.height) * scale - 1,
    )


def render_preview(
    compiled: CompiledMap,
    bible: WorldBible,
    output: Path,
    *,
    overlays: set[str] | None = None,
    scale: int = 12,
) -> Path:
    enabled = DEFAULT_OVERLAYS if overlays is None else overlays
    header = 28
    image = Image.new("RGB", (compiled.width * scale, compiled.height * scale + header), "#11151b")
    draw = ImageDraw.Draw(image, "RGBA")
    palette = {**FALLBACK_COLORS, **bible.palette}
    for y, row in enumerate(compiled.terrain):
        for x, terrain_id in enumerate(row):
            color = palette.get(terrain_id, "#d13f7c")
            draw.rectangle(
                (x * scale, y * scale + header, (x + 1) * scale - 1, (y + 1) * scale - 1 + header),
                fill=color,
            )

    # Tile geometry is offset by a non-tile-aligned header, so overlays use an explicit shift.
    def shifted(rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        return (rect[0], rect[1] + header, rect[2], rect[3] + header)

    if "zones" in enabled:
        colors = {
            "encounter": (139, 61, 180, 82),
            "safe": (38, 190, 126, 70),
            "secret": (245, 194, 66, 85),
            "narrative": (78, 132, 220, 75),
        }
        for zone in compiled.zones:
            draw.rectangle(
                shifted(_world_rect(zone.rect, scale)),
                fill=colors[zone.kind],
                outline=colors[zone.kind][0:3] + (210,),
                width=2,
            )
    if "objects" in enabled:
        for item in compiled.decorative_layers + compiled.objects:
            rect = shifted(_world_rect(item.visual_rect, scale))
            alpha = 215 if not item.generated else 170
            draw.rectangle(rect, fill=item.color + f"{alpha:02x}", outline="#202020dd", width=1)
            if not item.generated and scale >= 10:
                draw.text(
                    (rect[0] + 1, rect[1] + 1),
                    item.id[:8],
                    fill="#ffffffdd",
                    font=ImageFont.load_default(),
                )
    if "walkability" in enabled:
        for y, walk_row in enumerate(compiled.walkability):
            for x, char in enumerate(walk_row):
                if char == ".":
                    draw.rectangle(shifted(_tile_rect(x, y, scale)), outline=(75, 220, 120, 55))
    if "collision" in enabled:
        for point in compiled.blocked_cells:
            rect = shifted(_tile_rect(point.x, point.y, scale))
            draw.line((rect[0], rect[1], rect[2], rect[3]), fill=(230, 45, 55, 210), width=1)
            draw.line((rect[2], rect[1], rect[0], rect[3]), fill=(230, 45, 55, 210), width=1)
    if "transitions" in enabled:
        for transition in compiled.transitions:
            draw.rectangle(
                shifted(_world_rect(transition.rect, scale)), outline=(50, 225, 235, 255), width=3
            )
    if "spawns" in enabled:
        for spawn in compiled.spawns:
            cx = spawn.position.x * scale + scale // 2
            cy = spawn.position.y * scale + scale // 2 + header
            draw.ellipse(
                (cx - 4, cy - 4, cx + 4, cy + 4), fill=(50, 125, 255, 255), outline="white"
            )
    if "landmarks" in enabled:
        for landmark in compiled.landmarks:
            cx = landmark.position.x * scale + scale // 2
            cy = landmark.position.y * scale + scale // 2 + header
            draw.regular_polygon((cx, cy, 6), n_sides=5, fill=(255, 213, 64, 255), outline="black")
    if "edges" in enabled:
        for edge in compiled.edge_contracts:
            if edge.side in ("north", "south"):
                y = header if edge.side == "north" else header + compiled.height * scale - 3
                coords = (edge.position * scale, y, (edge.position + edge.width) * scale, y + 3)
            else:
                x = 0 if edge.side == "west" else compiled.width * scale - 3
                coords = (
                    x,
                    header + edge.position * scale,
                    x + 3,
                    header + (edge.position + edge.width) * scale,
                )
            draw.rectangle(coords, fill=(255, 62, 210, 255))
    draw.rectangle((0, 0, image.width, header - 1), fill="#11151b")
    draw.text(
        (7, 7),
        f"{compiled.display_name}  [{compiled.map_id}] seed={compiled.seed} hash={compiled.canonical_hash[:10]}",
        fill="white",
        font=ImageFont.load_default(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=False)
    return output

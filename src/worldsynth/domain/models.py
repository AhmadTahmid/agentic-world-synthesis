from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Point(StrictModel):
    x: int
    y: int


class Rect(StrictModel):
    x: int
    y: int
    width: int = Field(gt=0)
    height: int = Field(gt=0)

    def cells(self) -> list[Point]:
        return [
            Point(x=x, y=y)
            for y in range(self.y, self.y + self.height)
            for x in range(self.x, self.x + self.width)
        ]

    def contains(self, point: Point) -> bool:
        return (
            self.x <= point.x < self.x + self.width
            and self.y <= point.y < self.y + self.height
        )


class Dimensions(StrictModel):
    width: int = Field(ge=6, le=256)
    height: int = Field(ge=6, le=256)


class AssetDimensions(StrictModel):
    width: int = Field(gt=0, le=8192)
    height: int = Field(gt=0, le=8192)


class LicenseInfo(StrictModel):
    creator: str
    source_url: str
    license: str
    attribution_required: bool = False


class CollisionKind(StrEnum):
    NONE = "none"
    RECT = "rect"
    MASK = "mask"
    POLYGON = "polygon"


class CollisionFootprint(StrictModel):
    kind: CollisionKind = CollisionKind.NONE
    rect: Rect | None = None
    cells: list[Point] = Field(default_factory=list)
    polygon: list[Point] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_payload(self) -> CollisionFootprint:
        if self.kind == CollisionKind.RECT and self.rect is None:
            raise ValueError("rect collision requires rect")
        if self.kind == CollisionKind.MASK and not self.cells:
            raise ValueError("mask collision requires cells")
        if self.kind == CollisionKind.POLYGON and len(self.polygon) < 3:
            raise ValueError("polygon collision requires at least three points")
        return self


class Socket(StrictModel):
    id: Identifier
    offset: Point
    prompt: str | None = None


class AnimationInfo(StrictModel):
    frames: int = Field(ge=1)
    fps: float = Field(gt=0)
    row: int = Field(ge=0, default=0)


class AssetArchetype(StrictModel):
    id: Identifier
    asset_path: str
    pixel_size: AssetDimensions
    tile_size: AssetDimensions
    ground_anchor: Point
    render_category: Literal["terrain", "structure", "prop", "character", "marker"]
    y_sort: bool = True
    collision: CollisionFootprint = Field(default_factory=CollisionFootprint)
    interaction_sockets: list[Socket] = Field(default_factory=list)
    doorway_sockets: list[Socket] = Field(default_factory=list)
    tags: list[Identifier] = Field(default_factory=list)
    animation: AnimationInfo | None = None
    variants: list[str] = Field(default_factory=list)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    license: LicenseInfo


class AssetRegistry(StrictModel):
    schema_version: Literal[1]
    tile_size: int = Field(gt=0)
    archetypes: list[AssetArchetype]

    @model_validator(mode="after")
    def unique_archetypes(self) -> AssetRegistry:
        ids = [item.id for item in self.archetypes]
        if len(ids) != len(set(ids)):
            raise ValueError("asset archetype IDs must be unique")
        return self

    def by_id(self) -> dict[str, AssetArchetype]:
        return {item.id: item for item in self.archetypes}


class BiomeDefinition(StrictModel):
    id: Identifier
    base_terrain: Identifier
    path_terrain: Identifier
    decoration_density: float = Field(ge=0, le=0.25)
    allowed_decoration_tags: list[Identifier]
    safe_zone_tags: list[Identifier] = Field(default_factory=list)


class ArchitecturalCulture(StrictModel):
    id: Identifier
    description: str
    preferred_tags: list[Identifier]


class TraversalRules(StrictModel):
    passable_terrain: list[Identifier]
    blocked_terrain: list[Identifier]
    diagonal_movement: bool = True
    max_danger_step: int = Field(ge=0, default=2)


class DensityGuidelines(StrictModel):
    min_open_fraction: float = Field(gt=0, lt=1)
    max_prop_fraction: float = Field(gt=0, lt=1)
    max_featureless_path: int = Field(gt=0)
    landmark_min_distance: int = Field(ge=0)


class WorldBible(StrictModel):
    schema_version: Literal[1]
    world_id: Identifier
    version: str
    title: str
    description: str
    art_direction: str
    tile_size: int = Field(gt=0)
    perspective: Literal["top_down"]
    palette: dict[Identifier, str]
    biomes: list[BiomeDefinition]
    architectural_cultures: list[ArchitecturalCulture]
    factions: dict[Identifier, str]
    monster_ecology_rules: list[str]
    traversal: TraversalRules
    density: DensityGuidelines
    prohibited_combinations: list[list[Identifier]]
    global_tags: list[Identifier]

    @model_validator(mode="after")
    def unique_biomes(self) -> WorldBible:
        ids = [biome.id for biome in self.biomes]
        if len(ids) != len(set(ids)):
            raise ValueError("biome IDs must be unique")
        return self

    def biome_by_id(self) -> dict[str, BiomeDefinition]:
        return {biome.id: biome for biome in self.biomes}


class MapNode(StrictModel):
    id: Identifier
    kind: Literal["settlement", "route", "dungeon", "interior"]
    region: Identifier
    danger_level: int = Field(ge=0)
    required: bool = True
    tags: list[Identifier] = Field(default_factory=list)


class WorldConnection(StrictModel):
    id: Identifier
    from_map: Identifier
    from_transition: Identifier
    to_map: Identifier
    to_transition: Identifier
    bidirectional: bool = True
    story_gate: str | None = None
    transition_type: Literal["edge", "door", "cave", "portal"]


class WorldGraph(StrictModel):
    schema_version: Literal[1]
    world_id: Identifier
    start_map: Identifier
    regions: dict[Identifier, str]
    nodes: list[MapNode]
    connections: list[WorldConnection]

    @model_validator(mode="after")
    def unique_graph_ids(self) -> WorldGraph:
        node_ids = [node.id for node in self.nodes]
        connection_ids = [connection.id for connection in self.connections]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("world node IDs must be unique")
        if len(connection_ids) != len(set(connection_ids)):
            raise ValueError("world connection IDs must be unique")
        return self


class EdgeContract(StrictModel):
    side: Literal["north", "east", "south", "west"]
    feature: Literal["road", "river", "coastline", "opening"]
    position: int = Field(ge=0)
    width: int = Field(gt=0)
    elevation: int
    biome: Identifier
    transition_type: Literal["edge", "bridge", "gate"]
    traversable: bool
    neighbor_map: Identifier


class TerrainRegion(StrictModel):
    terrain_id: Identifier
    rect: Rect


class PathSpec(StrictModel):
    id: Identifier
    points: list[Point] = Field(min_length=2)
    width: int = Field(ge=1, le=9)
    terrain_id: Identifier | None = None
    variation: int = Field(ge=0, le=2, default=1)


class ObjectPlacement(StrictModel):
    id: Identifier
    archetype_id: Identifier
    position: Point
    interaction_id: Identifier | None = None
    transition_id: Identifier | None = None
    landmark_id: Identifier | None = None
    required: bool = False


class TransitionSpec(StrictModel):
    id: Identifier
    rect: Rect
    target_map: Identifier
    target_transition: Identifier
    target_spawn: Point
    kind: Literal["edge", "door", "cave", "portal"]
    mandatory: bool = True


class SpawnPoint(StrictModel):
    id: Identifier
    position: Point
    kind: Literal["player", "npc"]
    required: bool = True


class InteractionSpec(StrictModel):
    id: Identifier
    position: Point
    prompt: str = "Interact"
    text: str
    radius: float = Field(gt=0, default=1.5)


class ZoneSpec(StrictModel):
    id: Identifier
    kind: Literal["encounter", "safe", "narrative", "secret"]
    rect: Rect
    encounter_table: Identifier | None = None
    rate: float = Field(ge=0, le=1, default=0)
    tags: list[Identifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def encounter_has_table(self) -> ZoneSpec:
        if self.kind == "encounter" and self.encounter_table is None:
            raise ValueError("encounter zone requires encounter_table")
        return self


class LandmarkSpec(StrictModel):
    id: Identifier
    position: Point
    unique_key: Identifier | None = None
    required: bool = True


class GenerationConstraints(StrictModel):
    decoration_families: list[Identifier] = Field(default_factory=list)
    decoration_density: float | None = Field(default=None, ge=0, le=0.25)
    protected_path_radius: int = Field(ge=0, default=1)
    min_object_spacing: int = Field(ge=0, default=1)
    reserve: list[Rect] = Field(default_factory=list)


class NarrativeMetadata(StrictModel):
    summary: str
    beats: list[str] = Field(default_factory=list)
    optional_area: str | None = None
    secret: str | None = None


class MapSpec(StrictModel):
    schema_version: Literal[1]
    map_id: Identifier
    display_name: str
    map_type: Literal["settlement", "route", "dungeon", "interior"]
    biome: Identifier
    dimensions: Dimensions
    seed: int
    base_terrain: Identifier
    terrain_regions: list[TerrainRegion] = Field(default_factory=list)
    paths: list[PathSpec] = Field(default_factory=list)
    structures: list[ObjectPlacement] = Field(default_factory=list)
    props: list[ObjectPlacement] = Field(default_factory=list)
    transitions: list[TransitionSpec]
    spawns: list[SpawnPoint]
    interactions: list[InteractionSpec] = Field(default_factory=list)
    encounter_zones: list[ZoneSpec] = Field(default_factory=list)
    zones: list[ZoneSpec] = Field(default_factory=list)
    landmarks: list[LandmarkSpec] = Field(default_factory=list)
    edge_contracts: list[EdgeContract] = Field(default_factory=list)
    generation: GenerationConstraints = Field(default_factory=GenerationConstraints)
    narrative: NarrativeMetadata

    @model_validator(mode="after")
    def unique_local_ids(self) -> MapSpec:
        groups: list[tuple[str, list[str]]] = [
            ("path", [item.id for item in self.paths]),
            ("object", [item.id for item in self.structures + self.props]),
            ("transition", [item.id for item in self.transitions]),
            ("spawn", [item.id for item in self.spawns]),
            ("interaction", [item.id for item in self.interactions]),
            ("zone", [item.id for item in self.encounter_zones + self.zones]),
            ("landmark", [item.id for item in self.landmarks]),
        ]
        for label, ids in groups:
            if len(ids) != len(set(ids)):
                raise ValueError(f"{label} IDs must be unique in map {self.map_id}")
        return self


class Diagnostic(StrictModel):
    severity: Literal["error", "warning", "info", "repair"]
    code: Identifier
    message: str
    map_id: Identifier | None = None
    location: Point | None = None
    repair: str | None = None


class CompiledObject(StrictModel):
    id: Identifier
    archetype_id: Identifier
    position: Point
    visual_rect: Rect
    collision_cells: list[Point]
    asset_path: str
    color: str
    tags: list[Identifier]
    interaction_id: Identifier | None = None
    transition_id: Identifier | None = None
    landmark_id: Identifier | None = None
    generated: bool = False


class CompiledMap(StrictModel):
    format_version: Literal[1]
    map_id: Identifier
    display_name: str
    map_type: Literal["settlement", "route", "dungeon", "interior"]
    biome: Identifier
    source_content_hash: str
    canonical_hash: str = ""
    seed: int
    tile_size: int
    width: int
    height: int
    terrain: list[list[Identifier]]
    decorative_layers: list[CompiledObject]
    objects: list[CompiledObject]
    blocked_cells: list[Point]
    walkability: list[str]
    interactions: list[InteractionSpec]
    transitions: list[TransitionSpec]
    zones: list[ZoneSpec]
    spawns: list[SpawnPoint]
    landmarks: list[LandmarkSpec]
    edge_contracts: list[EdgeContract]
    asset_references: list[Identifier]
    build_metadata: dict[str, str | int | bool]
    diagnostics: list[Diagnostic]


class ValidationReport(StrictModel):
    format_version: Literal[1] = 1
    success: bool
    errors: int
    warnings: int
    issues: list[Diagnostic]
    map_hashes: dict[Identifier, str] = Field(default_factory=dict)

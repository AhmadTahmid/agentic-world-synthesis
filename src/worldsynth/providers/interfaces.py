from __future__ import annotations

from typing import Protocol

from worldsynth.domain.models import (
    AssetRegistry,
    Dimensions,
    GenerationConstraints,
    MapSpec,
    NarrativeMetadata,
    Point,
    Rect,
    SpawnPoint,
    TransitionSpec,
    WorldBible,
)


class PlannerProvider(Protocol):
    """Produces an untrusted MapSpec candidate that must enter normal validation."""

    def plan_map(self, brief: str, bible: WorldBible, seed: int) -> MapSpec: ...


class ConceptAnalyzer(Protocol):
    def analyze(self, image_path: str) -> dict[str, object]: ...


class PaletteAnalyzer(Protocol):
    def analyze_palette(self, image_path: str, color_count: int = 12) -> list[str]: ...


class SegmentationProvider(Protocol):
    def segment(self, image_path: str, semantic_labels: list[str]) -> dict[str, object]: ...


class InpaintingProvider(Protocol):
    def inpaint(self, image_path: str, mask_path: str, prompt: str) -> str: ...


class AssetGenerator(Protocol):
    def propose(self, prompt: str, registry: AssetRegistry) -> list[str]: ...


class MapRepairProvider(Protocol):
    def propose_revision(self, map_spec: MapSpec, diagnostics: list[str]) -> MapSpec: ...


class RuleBasedPlanner:
    """Offline orchestration fixture; intentionally modest but real and typed."""

    def plan_map(self, brief: str, bible: WorldBible, seed: int) -> MapSpec:
        slug_words = [part.lower() for part in brief.split() if part.isalnum()][:3]
        map_id = "planned_" + ("_".join(slug_words) or "clearing")
        biome = bible.biomes[0]
        return MapSpec(
            schema_version=1,
            map_id=map_id,
            display_name="Planned Clearing",
            map_type="route",
            biome=biome.id,
            dimensions=Dimensions(width=16, height=12),
            seed=seed,
            base_terrain=biome.base_terrain,
            paths=[],
            transitions=[
                TransitionSpec(
                    id="return_path",
                    rect=Rect(x=7, y=11, width=2, height=1),
                    target_map="placeholder_neighbor",
                    target_transition="planned_entry",
                    target_spawn=Point(x=8, y=10),
                    kind="edge",
                )
            ],
            spawns=[SpawnPoint(id="start", position=Point(x=8, y=9), kind="player")],
            generation=GenerationConstraints(decoration_families=[]),
            narrative=NarrativeMetadata(summary=brief),
        )

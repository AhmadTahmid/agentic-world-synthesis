class_name WorldSynthTileRenderer
extends Node2D

const LAYER_ORDER := ["base", "terrain_transitions", "paths", "ground_decals", "water", "walls"]
const LAYER_Z := {
	"base": -900,
	"terrain_transitions": -890,
	"paths": -880,
	"ground_decals": -870,
	"water": -860,
	"walls": -100,
}

var rendered_counts: Dictionary = {}


func configure(map_data: Dictionary) -> bool:
	if not map_data.has("render_layers"):
		# Backward-compatible format-1 maps use the explicit diagnostic canvas.
		return true
	var tile_size := int(map_data["tile_size"])
	for layer_name in LAYER_ORDER:
		var tiles: Array = map_data["render_layers"].get(layer_name, [])
		if tiles.is_empty():
			continue
		var layer := TileMapLayer.new()
		layer.name = str(layer_name).to_pascal_case()
		layer.z_index = int(LAYER_Z[layer_name])
		var tile_set := TileSet.new()
		tile_set.tile_size = Vector2i(tile_size, tile_size)
		layer.tile_set = tile_set
		var source_ids: Dictionary = {}
		for tile_data in tiles:
			var asset_path := str(tile_data["asset_path"])
			if not source_ids.has(asset_path):
				var source_id := _add_atlas_source(tile_set, asset_path, tile_size)
				if source_id < 0:
					return false
				source_ids[asset_path] = source_id
			var cell_data: Dictionary = tile_data["atlas_cell"]
			var atlas_cell := Vector2i(int(cell_data["x"]), int(cell_data["y"]))
			var atlas_source := tile_set.get_source(int(source_ids[asset_path])) as TileSetAtlasSource
			if not atlas_source.has_tile(atlas_cell):
				atlas_source.create_tile(atlas_cell)
			var point: Dictionary = tile_data["position"]
			layer.set_cell(Vector2i(int(point["x"]), int(point["y"])), int(source_ids[asset_path]), atlas_cell)
		add_child(layer)
		rendered_counts[layer_name] = tiles.size()
	return true


func _add_atlas_source(tile_set: TileSet, asset_path: String, tile_size: int) -> int:
	var resource_path := "res://" + asset_path
	if not ResourceLoader.exists(resource_path):
		push_error("Terrain atlas is missing: %s" % resource_path)
		return -1
	var texture := load(resource_path) as Texture2D
	if texture == null:
		push_error("Terrain atlas is not a Texture2D: %s" % resource_path)
		return -1
	var source := TileSetAtlasSource.new()
	source.texture = texture
	source.texture_region_size = Vector2i(tile_size, tile_size)
	return tile_set.add_source(source)

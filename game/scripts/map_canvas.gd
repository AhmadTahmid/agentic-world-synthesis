class_name WorldSynthMapCanvas
extends Node2D

var map_data: Dictionary
var tile_size := 32
var debug_flags := {
	"collision": false,
	"walkability": false,
	"zones": false,
	"transitions": false,
	"anchors": false,
	"neighbors": false,
}

const TERRAIN_COLORS := {
	"grass": "#6f9f58", "forest_floor": "#476a45", "meadow": "#9abc65",
	"stone_floor": "#747b78", "wood_floor": "#b5895a", "cobble": "#b7a98b",
	"dirt_path": "#aa8a5c", "cave_path": "#929083", "water": "#4d88a8",
	"wall": "#343c3b", "void": "#171b22"
}


func configure(data: Dictionary) -> void:
	map_data = data
	tile_size = int(data["tile_size"])
	queue_redraw()


func toggle_flag(flag: String) -> void:
	if debug_flags.has(flag):
		debug_flags[flag] = not debug_flags[flag]
		queue_redraw()


func set_all_debug(enabled: bool) -> void:
	for flag in debug_flags:
		debug_flags[flag] = enabled
	queue_redraw()


func _cell_rect(x: int, y: int) -> Rect2:
	return Rect2(x * tile_size, y * tile_size, tile_size, tile_size)


func _data_rect(data: Dictionary) -> Rect2:
	return Rect2(
		float(data["x"]) * tile_size, float(data["y"]) * tile_size,
		float(data["width"]) * tile_size, float(data["height"]) * tile_size
	)


func _draw() -> void:
	if map_data.is_empty():
		return
	var terrain: Array = map_data["terrain"]
	for y in terrain.size():
		var row: Array = terrain[y]
		for x in row.size():
			var terrain_id := str(row[x])
			draw_rect(_cell_rect(x, y), Color(str(TERRAIN_COLORS.get(terrain_id, "#d13f7c"))))
	if debug_flags["walkability"]:
		for y in map_data["walkability"].size():
			var row: String = map_data["walkability"][y]
			for x in row.length():
				if row[x] == ".":
					draw_rect(_cell_rect(x, y), Color(0.2, 0.95, 0.45, 0.12), false, 1.0)
	if debug_flags["zones"]:
		for zone in map_data["zones"]:
			var zone_color := Color(0.55, 0.2, 0.75, 0.24) if zone["kind"] == "encounter" else Color(0.1, 0.8, 0.5, 0.2)
			draw_rect(_data_rect(zone["rect"]), zone_color, true)
			draw_rect(_data_rect(zone["rect"]), zone_color.lightened(0.4), false, 2.0)
	if debug_flags["collision"]:
		for point in map_data["blocked_cells"]:
			var rect := _cell_rect(int(point["x"]), int(point["y"]))
			draw_line(rect.position, rect.end, Color(1.0, 0.1, 0.15, 0.85), 1.0)
			draw_line(Vector2(rect.end.x, rect.position.y), Vector2(rect.position.x, rect.end.y), Color(1.0, 0.1, 0.15, 0.85), 1.0)
	if debug_flags["transitions"]:
		for transition in map_data["transitions"]:
			draw_rect(_data_rect(transition["rect"]), Color(0.1, 0.9, 1.0, 0.85), false, 3.0)
	if debug_flags["anchors"]:
		for item in map_data["decorative_layers"] + map_data["objects"]:
			var point: Dictionary = item["position"]
			var center := Vector2((float(point["x"]) + 0.5) * tile_size, (float(point["y"]) + 0.5) * tile_size)
			draw_circle(center, 3.5, Color("#ffd540"))
	if debug_flags["neighbors"]:
		for edge in map_data["edge_contracts"]:
			var side := str(edge["side"])
			var start := int(edge["position"]) * tile_size
			var extent := int(edge["width"]) * tile_size
			if side == "north" or side == "south":
				var y := 2.0 if side == "north" else float(map_data["height"] * tile_size - 2)
				draw_line(Vector2(start, y), Vector2(start + extent, y), Color("#ff3ed2"), 4.0)
			else:
				var x := 2.0 if side == "west" else float(map_data["width"] * tile_size - 2)
				draw_line(Vector2(x, start), Vector2(x, start + extent), Color("#ff3ed2"), 4.0)

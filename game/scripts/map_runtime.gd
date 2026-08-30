class_name WorldSynthMapRuntime
extends Node2D

const MAP_CANVAS_SCRIPT := preload("res://scripts/map_canvas.gd")
const TILE_RENDERER_SCRIPT := preload("res://scripts/tile_renderer.gd")
const RUNTIME_OBJECT_SCRIPT := preload("res://scripts/runtime_object.gd")
const PLAYER_SCRIPT := preload("res://scripts/player.gd")

signal transition_requested(transition: Dictionary)
signal encounter_triggered(zone: Dictionary)

var map_data: Dictionary
var tile_size := 32
var actor_layer: Node2D
var structure_layer: Node2D
var shadow_layer: Node2D
var foreground_layer: Node2D
var tile_renderer
var canvas
var transition_count := 0
var collision_shape_count := 0
var load_error := ""


func load_map(map_id: String) -> bool:
	name = "MapRuntime_" + map_id
	var path := "res://generated/maps/%s.json" % map_id
	if not FileAccess.file_exists(path):
		return _fail("Compiled map is missing: %s. Run `worldsynth build`." % path)
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return _fail("Could not open compiled map %s (error %s)." % [path, FileAccess.get_open_error()])
	var parsed = JSON.parse_string(file.get_as_text())
	if not parsed is Dictionary:
		return _fail("Compiled map %s is not a JSON object." % path)
	map_data = parsed
	for key in ["format_version", "map_id", "tile_size", "width", "height", "terrain", "walkability", "objects", "decorative_layers", "blocked_cells", "transitions", "zones", "interactions"]:
		if not map_data.has(key):
			return _fail("Compiled map %s is missing required field %s." % [map_id, key])
	if int(map_data["format_version"]) != 1:
		return _fail("Unsupported compiled format %s in %s." % [map_data["format_version"], path])
	if map_data["terrain"].size() != int(map_data["height"]) or map_data["walkability"].size() != int(map_data["height"]):
		return _fail("Compiled map %s row count does not match height." % map_id)
	for row in map_data["terrain"]:
		if row.size() != int(map_data["width"]):
			return _fail("Compiled map %s has a terrain row with the wrong width." % map_id)
	tile_size = int(map_data["tile_size"])
	tile_renderer = TILE_RENDERER_SCRIPT.new()
	tile_renderer.name = "ProductionTileRenderer"
	add_child(tile_renderer)
	if not tile_renderer.configure(map_data):
		return _fail("Failed to construct production tile layers for %s." % map_id)
	shadow_layer = Node2D.new()
	shadow_layer.name = "GroundShadows"
	shadow_layer.z_index = -200
	add_child(shadow_layer)
	structure_layer = Node2D.new()
	structure_layer.name = "StaticStructures"
	structure_layer.z_index = -10
	add_child(structure_layer)
	actor_layer = Node2D.new()
	actor_layer.name = "YSortedActors"
	actor_layer.y_sort_enabled = true
	add_child(actor_layer)
	foreground_layer = Node2D.new()
	foreground_layer.name = "ForegroundOverhangs"
	foreground_layer.z_index = 500
	add_child(foreground_layer)
	canvas = MAP_CANVAS_SCRIPT.new()
	canvas.name = "SemanticDebugOverlay"
	canvas.z_index = 1000
	add_child(canvas)
	canvas.configure(map_data)
	if tile_renderer.rendered_counts.is_empty():
		canvas.toggle_flag("semantic_colors")
	if not _create_objects():
		return false
	_create_collision()
	_create_transitions()
	_create_encounters()
	return true


func _fail(message: String) -> bool:
	load_error = message
	push_error(message)
	return false


func _create_objects() -> bool:
	for data in map_data["decorative_layers"] + map_data["objects"]:
		var item := RUNTIME_OBJECT_SCRIPT.new()
		var tags: Array = data.get("tags", [])
		var parent := structure_layer if tags.has("building") else actor_layer
		parent.add_child(item)
		if not item.configure(data, tile_size, shadow_layer, foreground_layer):
			return _fail("Failed to instantiate object %s in map %s." % [data.get("id", "?"), map_data["map_id"]])
	return true


func _create_collision() -> void:
	var body := StaticBody2D.new()
	body.name = "CompiledCollision"
	body.collision_layer = 1
	body.collision_mask = 0
	add_child(body)
	var rectangles: Array = map_data.get("collision_rects", [])
	if rectangles.is_empty():
		for point in map_data["blocked_cells"]:
			rectangles.append({"x": point["x"], "y": point["y"], "width": 1, "height": 1})
	for rect in rectangles:
		var shape_node := CollisionShape2D.new()
		var shape := RectangleShape2D.new()
		shape.size = Vector2(float(rect["width"]) * tile_size, float(rect["height"]) * tile_size)
		shape_node.shape = shape
		shape_node.position = Vector2((float(rect["x"]) + float(rect["width"]) / 2.0) * tile_size, (float(rect["y"]) + float(rect["height"]) / 2.0) * tile_size)
		body.add_child(shape_node)
		collision_shape_count += 1


func _create_transitions() -> void:
	for transition in map_data["transitions"]:
		var area := Area2D.new()
		area.name = "Transition_" + str(transition["id"])
		area.collision_layer = 0
		area.collision_mask = 2
		var shape_node := CollisionShape2D.new()
		var shape := RectangleShape2D.new()
		var rect: Dictionary = transition["rect"]
		shape.size = Vector2(float(rect["width"]) * tile_size, float(rect["height"]) * tile_size)
		shape_node.shape = shape
		area.position = Vector2((float(rect["x"]) + float(rect["width"]) / 2.0) * tile_size, (float(rect["y"]) + float(rect["height"]) / 2.0) * tile_size)
		area.add_child(shape_node)
		area.body_entered.connect(_on_transition_entered.bind(transition))
		add_child(area)
		transition_count += 1


func _create_encounters() -> void:
	for zone in map_data["zones"]:
		if zone["kind"] != "encounter":
			continue
		var area := Area2D.new()
		area.name = "Encounter_" + str(zone["id"])
		area.collision_layer = 0
		area.collision_mask = 2
		var shape_node := CollisionShape2D.new()
		var shape := RectangleShape2D.new()
		var rect: Dictionary = zone["rect"]
		shape.size = Vector2(float(rect["width"]) * tile_size, float(rect["height"]) * tile_size)
		shape_node.shape = shape
		area.position = Vector2((float(rect["x"]) + float(rect["width"]) / 2.0) * tile_size, (float(rect["y"]) + float(rect["height"]) / 2.0) * tile_size)
		area.add_child(shape_node)
		area.body_entered.connect(_on_encounter_entered.bind(zone))
		add_child(area)


func _on_transition_entered(body: Node2D, transition: Dictionary) -> void:
	if body.get_script() == PLAYER_SCRIPT:
		transition_requested.emit(transition)


func _on_encounter_entered(body: Node2D, zone: Dictionary) -> void:
	if body.get_script() == PLAYER_SCRIPT:
		encounter_triggered.emit(zone)


func nearest_interaction(world_position: Vector2) -> Dictionary:
	var closest: Dictionary = {}
	var best := INF
	for interaction in map_data["interactions"]:
		var point: Dictionary = interaction["position"]
		var target := Vector2((float(point["x"]) + 0.5) * tile_size, (float(point["y"]) + 0.5) * tile_size)
		var distance := world_position.distance_to(target)
		var radius := float(interaction.get("radius", 1.5)) * tile_size
		if distance <= radius and distance < best:
			closest = interaction
			best = distance
	return closest

extends Node2D

const SAVE_PATH := "user://worldsynth_save.json"
const MAP_RUNTIME_SCRIPT := preload("res://scripts/map_runtime.gd")
const PLAYER_SCRIPT := preload("res://scripts/player.gd")

var runtime
var player
var current_map_id := ""
var manifest: Dictionary
var transition_lock_until := 0
var debug_all := false
var message_until := 0
var current_interaction: Dictionary = {}

var map_label: Label
var prompt_label: Label
var message_label: Label
var debug_label: Label


func _ready() -> void:
	_ensure_input_actions()
	_create_ui()
	manifest = _read_json("res://generated/world_manifest.json")
	if manifest.is_empty() or not manifest.has("start_map"):
		_show_fatal("World manifest is missing or malformed. Run `worldsynth build` first.")
		return
	var saved := _read_json(SAVE_PATH) if FileAccess.file_exists(SAVE_PATH) else {}
	var start_id := str(saved.get("map_id", manifest["start_map"]))
	if not manifest["maps"].has(start_id):
		start_id = str(manifest["start_map"])
	if saved.has("pixel_x") and saved.has("pixel_y"):
		load_world_map(start_id, {"pixel_x": saved["pixel_x"], "pixel_y": saved["pixel_y"]})
	else:
		load_world_map(start_id)


func _ensure_input_actions() -> void:
	_add_keys("move_up", [KEY_W, KEY_UP])
	_add_keys("move_down", [KEY_S, KEY_DOWN])
	_add_keys("move_left", [KEY_A, KEY_LEFT])
	_add_keys("move_right", [KEY_D, KEY_RIGHT])
	_add_keys("interact", [KEY_E, KEY_SPACE])
	_add_keys("save_game", [KEY_F5])
	_add_keys("toggle_debug", [KEY_F3])
	_add_keys("debug_collision", [KEY_1])
	_add_keys("debug_walkability", [KEY_2])
	_add_keys("debug_zones", [KEY_3])
	_add_keys("debug_transitions", [KEY_4])
	_add_keys("debug_anchors", [KEY_5])
	_add_keys("debug_neighbors", [KEY_6])


func _add_keys(action: StringName, keycodes: Array) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	for keycode in keycodes:
		var event := InputEventKey.new()
		event.physical_keycode = int(keycode)
		InputMap.action_add_event(action, event)


func _create_ui() -> void:
	var ui := CanvasLayer.new()
	ui.name = "UI"
	ui.layer = 20
	add_child(ui)
	map_label = Label.new()
	map_label.position = Vector2(14, 12)
	map_label.add_theme_font_size_override("font_size", 18)
	map_label.add_theme_color_override("font_color", Color.WHITE)
	map_label.add_theme_color_override("font_shadow_color", Color.BLACK)
	map_label.add_theme_constant_override("shadow_offset_x", 2)
	map_label.add_theme_constant_override("shadow_offset_y", 2)
	ui.add_child(map_label)
	prompt_label = Label.new()
	prompt_label.position = Vector2(330, 580)
	prompt_label.size = Vector2(300, 40)
	prompt_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	prompt_label.add_theme_font_size_override("font_size", 18)
	prompt_label.add_theme_color_override("font_color", Color("#fff2b0"))
	ui.add_child(prompt_label)
	message_label = Label.new()
	message_label.position = Vector2(170, 510)
	message_label.size = Vector2(620, 62)
	message_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	message_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	message_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	message_label.add_theme_font_size_override("font_size", 17)
	message_label.add_theme_color_override("font_color", Color.WHITE)
	message_label.add_theme_stylebox_override("normal", _panel_style(Color(0.04, 0.06, 0.09, 0.88)))
	message_label.visible = false
	ui.add_child(message_label)
	debug_label = Label.new()
	debug_label.position = Vector2(650, 10)
	debug_label.size = Vector2(300, 150)
	debug_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	debug_label.add_theme_font_size_override("font_size", 13)
	debug_label.add_theme_color_override("font_color", Color("#bff7da"))
	debug_label.add_theme_stylebox_override("normal", _panel_style(Color(0.02, 0.08, 0.06, 0.75)))
	debug_label.visible = false
	ui.add_child(debug_label)


func _panel_style(color: Color) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.corner_radius_top_left = 7
	style.corner_radius_top_right = 7
	style.corner_radius_bottom_left = 7
	style.corner_radius_bottom_right = 7
	style.content_margin_left = 12
	style.content_margin_right = 12
	style.content_margin_top = 8
	style.content_margin_bottom = 8
	return style


func _read_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("Could not open JSON file %s (error %s)." % [path, FileAccess.get_open_error()])
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	if not parsed is Dictionary:
		push_error("JSON file %s does not contain an object." % path)
		return {}
	return parsed


func load_world_map(map_id: String, spawn_data: Dictionary = {}) -> bool:
	if not manifest.get("maps", {}).has(map_id):
		_show_fatal("Map %s is absent from the compiled manifest." % map_id)
		return false
	if is_instance_valid(player) and is_instance_valid(player.get_parent()):
		player.reparent(self)
	if is_instance_valid(runtime):
		runtime.queue_free()
	runtime = MAP_RUNTIME_SCRIPT.new()
	add_child(runtime)
	if not runtime.load_map(map_id):
		_show_fatal(runtime.load_error)
		return false
	runtime.transition_requested.connect(_on_transition_requested)
	runtime.encounter_triggered.connect(_on_encounter_triggered)
	if not is_instance_valid(player):
		player = PLAYER_SCRIPT.new()
		runtime.actor_layer.add_child(player)
	else:
		player.reparent(runtime.actor_layer)
	current_map_id = map_id
	if spawn_data.has("pixel_x"):
		player.position = Vector2(float(spawn_data["pixel_x"]), float(spawn_data["pixel_y"]))
	elif spawn_data.has("x"):
		player.position = Vector2((float(spawn_data["x"]) + 0.5) * runtime.tile_size, (float(spawn_data["y"]) + 0.5) * runtime.tile_size)
	else:
		var spawn: Dictionary = runtime.map_data["spawns"][0]
		for candidate in runtime.map_data["spawns"]:
			if candidate["kind"] == "player":
				spawn = candidate
				break
		var point: Dictionary = spawn["position"]
		player.position = Vector2((float(point["x"]) + 0.5) * runtime.tile_size, (float(point["y"]) + 0.5) * runtime.tile_size)
	player.configure_camera(Vector2(float(runtime.map_data["width"] * runtime.tile_size), float(runtime.map_data["height"] * runtime.tile_size)))
	map_label.text = "%s  [%s]" % [runtime.map_data["display_name"], map_id]
	runtime.canvas.set_all_debug(debug_all)
	transition_lock_until = Time.get_ticks_msec() + 550
	_save_game(false)
	return true


func _process(_delta: float) -> void:
	if not is_instance_valid(runtime) or not is_instance_valid(player):
		return
	current_interaction = runtime.nearest_interaction(player.position)
	prompt_label.text = "[E] %s" % current_interaction.get("prompt", "") if not current_interaction.is_empty() else ""
	if message_label.visible and Time.get_ticks_msec() > message_until:
		message_label.visible = false
	if debug_label.visible:
		var tile := Vector2i(floori(player.position.x / runtime.tile_size), floori(player.position.y / runtime.tile_size))
		var neighbors: Array[String] = []
		for edge in runtime.map_data["edge_contracts"]:
			neighbors.append(str(edge["neighbor_map"]))
		debug_label.text = "F3 debug | 1 collision 2 walk 3 zones\n4 transitions 5 anchors 6 neighbors\nmap: %s\ntile: %s,%s\nneighbors: %s" % [current_map_id, tile.x, tile.y, ", ".join(neighbors) if not neighbors.is_empty() else "portal-only"]


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("interact") and not current_interaction.is_empty():
		_show_message(str(current_interaction["text"]), 5.0)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("save_game"):
		_save_game(true)
	elif event.is_action_pressed("toggle_debug") and is_instance_valid(runtime):
		debug_all = not debug_all
		runtime.canvas.set_all_debug(debug_all)
		debug_label.visible = debug_all
	else:
		var debug_actions := {
			"debug_collision": "collision", "debug_walkability": "walkability",
			"debug_zones": "zones", "debug_transitions": "transitions",
			"debug_anchors": "anchors", "debug_neighbors": "neighbors"
		}
		for action in debug_actions:
			if event.is_action_pressed(action) and is_instance_valid(runtime):
				runtime.canvas.toggle_flag(debug_actions[action])
				debug_label.visible = true
				get_viewport().set_input_as_handled()
				return


func _on_transition_requested(transition: Dictionary) -> void:
	if Time.get_ticks_msec() < transition_lock_until:
		return
	transition_lock_until = Time.get_ticks_msec() + 700
	load_world_map(str(transition["target_map"]), transition["target_spawn"])


func _on_encounter_triggered(zone: Dictionary) -> void:
	var table := str(zone.get("encounter_table", "unknown"))
	_show_message("Wild encounter activity detected!  Table: %s  (battle placeholder)" % table, 3.0)


func _show_message(text: String, seconds: float) -> void:
	message_label.text = text
	message_label.visible = true
	message_until = Time.get_ticks_msec() + int(seconds * 1000.0)


func _show_fatal(text: String) -> void:
	push_error(text)
	if not is_instance_valid(message_label):
		_create_ui()
	message_label.text = "LOAD ERROR: " + text
	message_label.visible = true
	message_until = Time.get_ticks_msec() + 3600000


func _save_game(show_notice: bool) -> void:
	if not is_instance_valid(player) or current_map_id.is_empty():
		return
	var file := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file == null:
		push_error("Could not write save file (error %s)." % FileAccess.get_open_error())
		return
	file.store_string(JSON.stringify({"format_version": 1, "map_id": current_map_id, "pixel_x": player.position.x, "pixel_y": player.position.y}))
	if show_notice:
		_show_message("Journey saved.", 1.5)


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		_save_game(false)

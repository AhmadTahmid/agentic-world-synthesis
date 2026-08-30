extends SceneTree


func _initialize() -> void:
	OS.set_environment("WORLDSYNTH_NO_SAVE", "1")
	call_deferred("_run")


func _run() -> void:
	var packed := load("res://scenes/main.tscn") as PackedScene
	if packed == null:
		_fail("main scene could not be loaded")
		return
	var main := packed.instantiate()
	root.add_child(main)
	await process_frame
	await process_frame
	if not main.load_world_map("lanternmarket", {"x": 20, "y": 23}):
		_fail("canonical initial map could not be loaded")
		return
	await process_frame
	if not is_instance_valid(main.player):
		_fail("player was not created")
		return
	if not is_instance_valid(main.runtime):
		_fail("map runtime was not created")
		return
	if not is_instance_valid(main.player.animated_sprite):
		_fail("data-driven animated player sprite was not created")
		return
	if main.runtime.load_error != "":
		_fail("map loader error: " + main.runtime.load_error)
		return
	if main.runtime.collision_shape_count <= 0:
		_fail("compiled collision was not instantiated")
		return
	if not is_instance_valid(main.runtime.tile_renderer):
		_fail("production TileMapLayer renderer was not created")
		return
	if main.runtime.tile_renderer.rendered_counts.is_empty():
		_fail("production tile renderer loaded no compiled visual tiles")
		return
	var stats: Dictionary = main.runtime.map_data.get("render_stats", {})
	if main.runtime.collision_shape_count != int(stats.get("collision_shape_count", -1)):
		_fail("merged collision-shape count disagrees with compiled diagnostics")
		return
	if main.runtime.transition_count <= 0:
		_fail("compiled transitions were not instantiated")
		return
	var tavern_transition: Dictionary = {}
	for transition in main.runtime.map_data["transitions"]:
		if transition["id"] == "tavern_door":
			tavern_transition = transition
			break
	if tavern_transition.is_empty():
		_fail("Lanternmarket tavern transition was absent")
		return
	main.transition_lock_until = 0
	main._on_transition_requested(tavern_transition)
	await process_frame
	await process_frame
	if main.current_map_id != "tavern_interior" or main.runtime.load_error != "":
		_fail("deferred exterior-to-interior transition did not load")
		return
	var tile_counts: Dictionary = stats.get("tile_layer_counts", {})
	print("WORLDSYNTH_SMOKE_OK map=lanternmarket blocked=%s collision_shapes=%s transitions=5 tile_layers=%s deferred_interior=tavern_interior" % [stats.get("blocked_cell_count", 0), int(stats.get("collision_shape_count", 0)), tile_counts.size()])
	quit(0)


func _fail(message: String) -> void:
	push_error("WORLDSYNTH_SMOKE_FAIL: " + message)
	quit(1)

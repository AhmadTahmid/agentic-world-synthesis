extends SceneTree


func _initialize() -> void:
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
	if not is_instance_valid(main.player):
		_fail("player was not created")
		return
	if not is_instance_valid(main.runtime):
		_fail("map runtime was not created")
		return
	if main.runtime.load_error != "":
		_fail("map loader error: " + main.runtime.load_error)
		return
	if main.runtime.collision_shape_count <= 0:
		_fail("compiled collision was not instantiated")
		return
	if main.runtime.transition_count <= 0:
		_fail("compiled transitions were not instantiated")
		return
	print("WORLDSYNTH_SMOKE_OK map=%s collision=%s transitions=%s" % [main.current_map_id, main.runtime.collision_shape_count, main.runtime.transition_count])
	quit(0)


func _fail(message: String) -> void:
	push_error("WORLDSYNTH_SMOKE_FAIL: " + message)
	quit(1)

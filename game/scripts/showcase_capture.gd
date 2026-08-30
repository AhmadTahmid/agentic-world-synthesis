extends SceneTree

const OUTPUTS := [
	{"name": "central_market", "tile": Vector2(20.0, 18.0)},
	{"name": "tavern_entrance", "tile": Vector2(9.0, 10.0)},
	{"name": "tree_overhang", "tile": Vector2(2.65, 4.55)},
	{"name": "terrain_boundary", "tile": Vector2(31.0, 7.0)},
]


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
	if not main.load_world_map("lanternmarket", {"x": 20, "y": 18}):
		_fail("Lanternmarket did not load")
		return
	main.player.movement_enabled = false
	main.prompt_label.visible = false
	main.message_label.visible = false
	await process_frame
	await process_frame
	var output_dir := ProjectSettings.globalize_path("res://../generated/showcase")
	DirAccess.make_dir_recursive_absolute(output_dir)
	for shot in OUTPUTS:
		var tile: Vector2 = shot["tile"]
		main.player.position = Vector2((tile.x + 0.5) * main.runtime.tile_size, (tile.y + 0.5) * main.runtime.tile_size)
		main.player.camera.reset_smoothing()
		await process_frame
		await process_frame
		if not _capture(output_dir.path_join(str(shot["name"]) + ".png")):
			return
	main.player.position = Vector2(20.5 * main.runtime.tile_size, 18.5 * main.runtime.tile_size)
	main.player.camera.reset_smoothing()
	main.runtime.canvas.set_all_debug(true)
	main.debug_label.visible = true
	await process_frame
	await process_frame
	if not _capture(output_dir.path_join("semantic_debug.png")):
		return
	print("WORLDSYNTH_SHOWCASE_OK shots=5 output=%s" % output_dir)
	quit(0)


func _capture(path: String) -> bool:
	var image := root.get_texture().get_image()
	if image == null or image.is_empty():
		_fail("viewport capture returned an empty image")
		return false
	var error := image.save_png(path)
	if error != OK:
		_fail("could not save %s (error %s)" % [path, error])
		return false
	return true


func _fail(message: String) -> void:
	push_error("WORLDSYNTH_SHOWCASE_FAIL: " + message)
	quit(1)

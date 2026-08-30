class_name WorldSynthPlayer
extends CharacterBody2D

var speed := 150.0
var movement_enabled := true
var facing := Vector2.DOWN
var camera: Camera2D
var animated_sprite: AnimatedSprite2D
var visual_ready := false


func _ready() -> void:
	name = "Player"
	collision_layer = 2
	collision_mask = 1
	var shape := CollisionShape2D.new()
	var capsule := CapsuleShape2D.new()
	capsule.radius = 8.0
	capsule.height = 22.0
	shape.shape = capsule
	shape.position = Vector2(0, 4)
	add_child(shape)
	camera = Camera2D.new()
	camera.name = "PlayerCamera"
	camera.position_smoothing_enabled = true
	camera.position_smoothing_speed = 7.0
	add_child(camera)


func configure_visual(data: Dictionary) -> bool:
	if data.is_empty() or not data.has("animation"):
		push_error("World manifest has no valid player_visual animation contract.")
		return false
	var resource_path := "res://" + str(data.get("asset_path", ""))
	if not ResourceLoader.exists(resource_path):
		push_error("Player sprite sheet is missing: %s" % resource_path)
		return false
	var texture := load(resource_path) as Texture2D
	if texture == null:
		push_error("Player sprite sheet could not be loaded: %s" % resource_path)
		return false
	var animation: Dictionary = data["animation"]
	var frame_size: Dictionary = animation.get("frame_size", {})
	if frame_size.is_empty():
		push_error("Player animation has no frame_size.")
		return false
	var frames := SpriteFrames.new()
	frames.remove_animation("default")
	var directions: Dictionary = animation.get("directions", {})
	for direction in ["down", "left", "right", "up"]:
		if not directions.has(direction):
			return false
		frames.add_animation("walk_" + direction)
		frames.set_animation_speed("walk_" + direction, float(animation["fps"]))
		frames.set_animation_loop("walk_" + direction, true)
		frames.add_animation("idle_" + direction)
		var row := int(directions[direction])
		for frame_index in int(animation["frames"]):
			var atlas := AtlasTexture.new()
			atlas.atlas = texture
			atlas.region = Rect2(
				frame_index * int(frame_size["width"]), row * int(frame_size["height"]),
				int(frame_size["width"]), int(frame_size["height"])
			)
			frames.add_frame("walk_" + direction, atlas)
		var idle_atlas := AtlasTexture.new()
		idle_atlas.atlas = texture
		idle_atlas.region = Rect2(
			int(animation.get("idle_frame", 0)) * int(frame_size["width"]), row * int(frame_size["height"]),
			int(frame_size["width"]), int(frame_size["height"])
		)
		frames.add_frame("idle_" + direction, idle_atlas)
	animated_sprite = AnimatedSprite2D.new()
	animated_sprite.name = "PlayerSprite"
	animated_sprite.sprite_frames = frames
	animated_sprite.position = Vector2(0, -8)
	add_child(animated_sprite)
	visual_ready = true
	animated_sprite.play("idle_down")
	return true


func configure_camera(map_size_pixels: Vector2) -> void:
	camera.limit_left = 0
	camera.limit_top = 0
	camera.limit_right = int(map_size_pixels.x)
	camera.limit_bottom = int(map_size_pixels.y)
	camera.position = Vector2.ZERO


func _physics_process(_delta: float) -> void:
	if not movement_enabled:
		velocity = Vector2.ZERO
		return
	var direction := Vector2(
		Input.get_action_strength("move_right") - Input.get_action_strength("move_left"),
		Input.get_action_strength("move_down") - Input.get_action_strength("move_up")
	).normalized()
	velocity = direction * speed
	if direction.length_squared() > 0.0:
		facing = direction
	if visual_ready:
		var direction_name := _direction_name()
		var animation_name := ("walk_" if direction.length_squared() > 0.0 else "idle_") + direction_name
		if animated_sprite.animation != animation_name:
			animated_sprite.play(animation_name)
	move_and_slide()


func _direction_name() -> String:
	if abs(facing.x) > abs(facing.y):
		return "right" if facing.x > 0 else "left"
	return "down" if facing.y > 0 else "up"

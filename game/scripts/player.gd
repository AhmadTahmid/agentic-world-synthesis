class_name WorldSynthPlayer
extends CharacterBody2D

var speed := 150.0
var movement_enabled := true
var facing := Vector2.DOWN
var camera: Camera2D


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
	queue_redraw()


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
	move_and_slide()
	queue_redraw()


func _draw() -> void:
	# Original provisional player art, drawn at runtime and replaceable independently of maps.
	draw_circle(Vector2(0, 4), 10.0, Color("#253744"))
	draw_circle(Vector2(0, -4), 8.0, Color("#f2d0a5"))
	draw_polygon(
		PackedVector2Array([Vector2(-10, 1), Vector2(10, 1), Vector2(7, 17), Vector2(-7, 17)]),
		PackedColorArray([Color("#d96d4c")])
	)
	draw_line(Vector2.ZERO, facing * 9.0, Color("#fff3b0"), 2.0)

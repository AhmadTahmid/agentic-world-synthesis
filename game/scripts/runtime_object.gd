class_name WorldSynthRuntimeObject
extends Node2D

var object_data: Dictionary
var tile_size := 32
var fallback_color := Color.MAGENTA


func configure(data: Dictionary, size: int) -> bool:
	object_data = data
	tile_size = size
	name = str(data.get("id", "Object"))
	var anchor: Dictionary = data["position"]
	position = Vector2((float(anchor["x"]) + 0.5) * tile_size, (float(anchor["y"]) + 0.5) * tile_size)
	fallback_color = Color(str(data.get("color", "#d13f7c")))
	var source_path := str(data.get("asset_path", ""))
	if source_path.is_empty():
		push_error("Compiled object %s has no asset_path" % name)
		return false
	var resource_path := "res://" + source_path
	var texture: Texture2D
	if ResourceLoader.exists(resource_path):
		texture = load(resource_path) as Texture2D
	elif FileAccess.file_exists(resource_path):
		# A direct --script smoke test can run before Godot creates its import cache.
		var image := Image.new()
		var image_error := image.load(resource_path)
		if image_error == OK:
			texture = ImageTexture.create_from_image(image)
	else:
		push_error("Compiled object %s references missing asset %s" % [name, resource_path])
		return false
	if texture == null:
		push_error("Asset %s could not be loaded as a Texture2D" % resource_path)
		return false
	var sprite := Sprite2D.new()
	sprite.texture = texture
	sprite.centered = false
	var visual: Dictionary = data["visual_rect"]
	sprite.position = Vector2(
		float(visual["x"]) * tile_size - position.x,
		float(visual["y"]) * tile_size - position.y
	)
	add_child(sprite)
	return true

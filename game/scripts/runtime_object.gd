class_name WorldSynthRuntimeObject
extends Node2D

var object_data: Dictionary
var tile_size := 32
var fallback_color := Color.MAGENTA


func configure(data: Dictionary, size: int, shadow_parent: Node2D, foreground_parent: Node2D) -> bool:
	object_data = data
	tile_size = size
	name = str(data.get("id", "Object"))
	var anchor: Dictionary = data["position"]
	position = Vector2((float(anchor["x"]) + 0.5) * tile_size, (float(anchor["y"]) + 0.5) * tile_size)
	fallback_color = Color(str(data.get("color", "#d13f7c")))
	var layers: Array = data.get("visual_layers", [])
	if not layers.is_empty():
		for layer_data in layers:
			var role := str(layer_data["role"])
			var parent := shadow_parent if role == "shadow" else foreground_parent if role == "foreground" else self
			if not _add_visual_layer(layer_data, parent):
				return false
		return true
	return _add_fallback_sprite(str(data.get("asset_path", "")))


func _load_texture(source_path: String) -> Texture2D:
	if source_path.is_empty():
		push_error("Compiled object %s has no asset_path" % name)
		return null
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
	if texture == null:
		push_error("Asset %s could not be loaded as a Texture2D" % resource_path)
	return texture


func _sprite_top_left() -> Vector2:
	var visual: Dictionary = object_data["visual_rect"]
	return Vector2(float(visual["x"]) * tile_size, float(visual["y"]) * tile_size)


func _add_visual_layer(layer_data: Dictionary, parent: Node2D) -> bool:
	var texture := _load_texture(str(layer_data["asset_path"]))
	if texture == null:
		return false
	var sprite := Sprite2D.new()
	sprite.texture = texture
	sprite.centered = false
	var offset: Dictionary = layer_data.get("offset_pixels", {"x": 0, "y": 0})
	var world_position := _sprite_top_left() + Vector2(float(offset["x"]), float(offset["y"]))
	sprite.position = world_position - position if parent == self else world_position
	sprite.modulate.a = float(layer_data.get("opacity", 1.0))
	sprite.name = str(layer_data["role"]).to_pascal_case() + "_" + name
	parent.add_child(sprite)
	return true


func _add_fallback_sprite(source_path: String) -> bool:
	var texture := _load_texture(source_path)
	if texture == null:
		return false
	var sprite := Sprite2D.new()
	sprite.texture = texture
	sprite.centered = false
	sprite.position = _sprite_top_left() - position
	add_child(sprite)
	return true

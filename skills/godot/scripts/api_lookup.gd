extends SceneTree
## ClassDB lookup against the installed engine, run by gd.py api.
## Args after `--`: one or more `Class`, `Class.member` or `@GlobalScope.CONSTANT`.
## Prints `FOUND <kind> <signature>` or `MISSING <query> suggest: a, b, c` per query.

var _missing := 0


func _initialize() -> void:
	for query: String in OS.get_cmdline_user_args():
		_lookup(query)
	quit(1 if _missing > 0 else 0)


func _lookup(query: String) -> void:
	var parts := query.split(".", false, 1)
	var cls := parts[0]
	var builtin := _builtin_type(cls)
	if builtin != TYPE_NIL:
		_lookup_builtin(query, cls, builtin, parts)
		return
	if not ClassDB.class_exists(cls):
		_miss(query, _closest(cls, ClassDB.get_class_list()))
		return
	if parts.size() == 1:
		print("FOUND class %s extends %s" % [cls, ClassDB.get_parent_class(cls)])
		return
	var member := parts[1]
	for m: Dictionary in ClassDB.class_get_method_list(cls):
		if m.name == member:
			print("FOUND method %s.%s" % [cls, _signature(m)])
			return
	for p: Dictionary in ClassDB.class_get_property_list(cls):
		if p.name == member:
			print("FOUND property %s.%s: %s" % [cls, member, _type_name(p)])
			return
	for s: Dictionary in ClassDB.class_get_signal_list(cls):
		if s.name == member:
			print("FOUND signal %s.%s" % [cls, _signature(s)])
			return
	if ClassDB.class_has_integer_constant(cls, member):
		print("FOUND constant %s.%s = %d" % [cls, member, ClassDB.class_get_integer_constant(cls, member)])
		return
	if ClassDB.class_has_enum(cls, member):
		print("FOUND enum %s.%s %s" % [cls, member, ClassDB.class_get_enum_constants(cls, member)])
		return
	var names: PackedStringArray = []
	for m: Dictionary in ClassDB.class_get_method_list(cls):
		names.append(m.name)
	for p: Dictionary in ClassDB.class_get_property_list(cls):
		names.append(p.name)
	for s: Dictionary in ClassDB.class_get_signal_list(cls):
		names.append(s.name)
	names.append_array(ClassDB.class_get_integer_constant_list(cls))
	_miss(query, _closest(member, names))


func _builtin_type(type_name: String) -> int:
	for t: int in range(1, TYPE_MAX):
		if type_string(t) == type_name and t != TYPE_OBJECT:
			return t
	return TYPE_NIL


## Built-in Variant types (Vector3, Array, String…) are not in ClassDB.
func _lookup_builtin(query: String, type_name: String, type_id: int, parts: PackedStringArray) -> void:
	if parts.size() == 1:
		print("FOUND builtin %s" % type_name)
		return
	var member := parts[1]
	var value: Variant = type_convert(null, type_id)
	if Callable.create(value, member).is_valid():
		print("FOUND method %s(...)" % query)
		return
	if _compiles("return %s.%s" % [type_name, member]):
		print("FOUND constant %s" % query)
		return
	if _compiles("var v: %s\n\treturn v.%s" % [type_name, member]):
		print("FOUND property %s" % query)
		return
	_miss(query, PackedStringArray())


func _compiles(body: String) -> bool:
	var script := GDScript.new()
	script.source_code = "extends RefCounted\n\nfunc probe() -> Variant:\n\t%s\n" % body
	return script.reload() == OK


func _signature(info: Dictionary) -> String:
	var args: PackedStringArray = []
	for a: Dictionary in info.get("args", []):
		args.append("%s: %s" % [a.name, _type_name(a)])
	var ret := ""
	if info.has("return"):
		ret = " -> " + _type_name(info.return)
	return "%s(%s)%s" % [info.name, ", ".join(args), ret]


func _type_name(info: Dictionary) -> String:
	if info.get("class_name", "") != "":
		return info.class_name
	if info.type == TYPE_NIL:
		return "void" if info.get("usage", 0) & PROPERTY_USAGE_NIL_IS_VARIANT == 0 else "Variant"
	return type_string(info.type)


func _closest(needle: String, pool: PackedStringArray) -> PackedStringArray:
	var scored: Array = []
	var lower := needle.to_lower()
	for item: String in pool:
		var s := item.to_lower().similarity(lower)
		if item.to_lower().contains(lower) or lower.contains(item.to_lower()):
			s += 0.5
		scored.append([s, item])
	scored.sort_custom(func(a: Array, b: Array) -> bool: return a[0] > b[0])
	var out: PackedStringArray = []
	for pair: Array in scored.slice(0, 5):
		out.append(pair[1])
	return out


func _miss(query: String, suggestions: PackedStringArray) -> void:
	_missing += 1
	print("MISSING %s suggest: %s" % [query, ", ".join(suggestions)])

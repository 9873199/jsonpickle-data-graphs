# Copyright (C) 2025 David Aguilar (davvid -at- gmail.com)
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""Tests for the ``data_only`` decoding mode.

``data_only=True`` is the mode for processing jsonpickle data from untrusted
uploads. It must rebuild JSON scalars, plain lists and string-keyed dicts,
including ``py/id`` shared and cyclic references, while proving that no class
import, custom handler call, ``eval()`` or object-restoration hook can ever
run. The side-effect tests below record every restoration attempt so that a
regression that reaches the object machinery fails loudly.
"""

import json

import pytest

import jsonpickle
from jsonpickle.unpickler import DataOnlyDecodeError, Unpickler


# ---------------------------------------------------------------------------
# Accepted data format: scalars, plain containers and ordinary business keys
# ---------------------------------------------------------------------------
def test_data_only_scalars():
    assert jsonpickle.decode("null", data_only=True) is None
    assert jsonpickle.decode("true", data_only=True) is True
    assert jsonpickle.decode("false", data_only=True) is False
    result = jsonpickle.decode("false", data_only=True)
    assert type(result) is bool
    assert jsonpickle.decode("36", data_only=True) == 36
    assert type(jsonpickle.decode("36", data_only=True)) is int
    assert jsonpickle.decode("3.5", data_only=True) == 3.5
    assert jsonpickle.decode('"hello"', data_only=True) == "hello"


def test_data_only_plain_containers():
    result = jsonpickle.decode(
        '[{"a": [1, true, null, 2.5, "s"]}, {"b": {}}]', data_only=True
    )
    assert result == [{"a": [1, True, None, 2.5, "s"]}, {"b": {}}]
    assert type(result) is list
    assert type(result[0]) is dict
    assert type(result[0]["a"]) is list
    assert type(result[1]["b"]) is dict


def test_data_only_ordinary_business_keys_are_kept():
    # Keys that are not defined protocol markers survive verbatim, including
    # ones that merely share the "py/" prefix.
    payload = json.dumps({"py/name": 1, "ordinary": [1, 2], "py/id-like": "x"})
    assert jsonpickle.decode(payload, data_only=True) == {
        "py/name": 1,
        "ordinary": [1, 2],
        "py/id-like": "x",
    }


def test_data_only_matches_real_encoder_output():
    original = {
        "name": "graph",
        "values": [1, 2, {"deep": [True, None]}],
        "flag": False,
    }
    encoded = jsonpickle.encode(original)
    assert jsonpickle.decode(encoded, data_only=True) == original


# ---------------------------------------------------------------------------
# py/id references: sharing, self references and mutual references
# ---------------------------------------------------------------------------
def test_data_only_shared_list_keeps_identity():
    shared = [1, 2]
    encoded = jsonpickle.encode([shared, shared])
    decoded = jsonpickle.decode(encoded, data_only=True)
    assert decoded == [[1, 2], [1, 2]]
    assert decoded[0] is decoded[1]
    assert type(decoded[0]) is list


def test_data_only_shared_dict_keeps_identity():
    shared = {"k": 1}
    encoded = jsonpickle.encode([shared, shared])
    decoded = jsonpickle.decode(encoded, data_only=True)
    assert decoded == [{"k": 1}, {"k": 1}]
    assert decoded[0] is decoded[1]
    assert type(decoded[0]) is dict


def test_data_only_self_referencing_list():
    self_list = []
    self_list.append(self_list)
    encoded = jsonpickle.encode(self_list)
    assert encoded == '[{"py/id": 0}]'
    decoded = jsonpickle.decode(encoded, data_only=True)
    assert type(decoded) is list
    assert decoded[0] is decoded


def test_data_only_self_referencing_dict():
    self_dict = {}
    self_dict["self"] = self_dict
    encoded = jsonpickle.encode(self_dict)
    assert encoded == '{"self": {"py/id": 0}}'
    decoded = jsonpickle.decode(encoded, data_only=True)
    assert type(decoded) is dict
    assert decoded["self"] is decoded


def test_data_only_mutual_list_and_dict_references():
    a = []
    b = {"a": a}
    a.append(b)
    encoded = jsonpickle.encode([a, b])
    decoded = jsonpickle.decode(encoded, data_only=True)
    list_obj, dict_obj = decoded
    assert type(list_obj) is list
    assert type(dict_obj) is dict
    assert list_obj[0] is dict_obj
    assert dict_obj["a"] is list_obj


def test_data_only_mutual_dict_references():
    root = {"a": {"b": {"py/id": 0}}, "c": {"py/id": 1}}
    decoded = jsonpickle.decode(json.dumps(root), data_only=True)
    assert decoded["a"]["b"] is decoded
    assert decoded["c"] is decoded["a"]


def test_data_only_list_to_list_cycle():
    first = []
    second = [first]
    first.append(second)
    encoded = jsonpickle.encode(first)
    assert encoded == '[[{"py/id": 0}]]'
    decoded = jsonpickle.decode(encoded, data_only=True)
    assert type(decoded) is list
    assert type(decoded[0]) is list
    assert decoded[0][0] is decoded


def test_data_only_dict_to_dict_cycle():
    first = {}
    second = {"x": first}
    first["y"] = second
    encoded = jsonpickle.encode(first)
    decoded = jsonpickle.decode(encoded, data_only=True)
    assert decoded["y"]["x"] is decoded


def test_data_only_three_node_cycle():
    first = []
    second = []
    third = [first]
    first.append(second)
    second.append(third)
    encoded = jsonpickle.encode(first)
    decoded = jsonpickle.decode(encoded, data_only=True)
    assert decoded[0][0][0] is decoded


def test_data_only_same_forward_reference_shared_at_two_sites():
    # list=0, first dict=1, second dict=2, third dict=3; id 2 is referenced
    # twice before it is built, so both sites must end up identical.
    payload = json.dumps(
        [{"a": {"py/id": 2}}, {"b": {"py/id": 2}}, {"k": 1}]
    )
    decoded = jsonpickle.decode(payload, data_only=True)
    assert decoded[0]["a"] is decoded[1]
    assert decoded[1]["b"] is decoded[1]


def test_data_only_empty_containers():
    assert jsonpickle.decode("[[], {}]", data_only=True) == [[], {}]


def test_data_only_dangling_reference_at_root():
    with pytest.raises(DataOnlyDecodeError, match="out of range"):
        jsonpickle.decode(json.dumps({"py/id": 0}), data_only=True)


def test_data_only_backward_reference_inside_dict():
    # root dict is index 0, its list value index 1; "y" points back at it.
    payload = json.dumps({"x": [1], "y": {"py/id": 1}})
    decoded = jsonpickle.decode(payload, data_only=True)
    assert decoded["y"] is decoded["x"]


def test_data_only_forward_reference_inside_dict():
    payload = json.dumps({"a": {"py/id": 0}})
    decoded = jsonpickle.decode(payload, data_only=True)
    assert decoded["a"] is decoded


def test_data_only_numbering_follows_traversal_order():
    # index 0: outer list, index 1: dict, index 2: inner list
    payload = json.dumps([{"a": []}, {"py/id": 1}])
    decoded = jsonpickle.decode(payload, data_only=True)
    assert decoded[1] is decoded[0]
    assert type(decoded[0]) is dict


def test_data_only_shared_nested_containers_roundtrip():
    inner = {"shared": [1, 2, 3]}
    original = [inner, [inner], {"again": inner}]
    encoded = jsonpickle.encode(original)
    decoded = jsonpickle.decode(encoded, data_only=True)
    assert decoded[0] is decoded[1][0]
    assert decoded[0] is decoded[2]["again"]
    assert decoded == original


# ---------------------------------------------------------------------------
# Rejection of every object-restoration marker, including nested ones
# ---------------------------------------------------------------------------
DISALLOWED_TAGS = [
    "py/object",
    "py/type",
    "py/function",
    "py/reduce",
    "py/repr",
    "py/mod",
    "py/state",
    "py/newargs",
    "py/newargsex",
    "py/newobj",
    "py/initargs",
    "py/seq",
    "py/set",
    "py/tuple",
    "py/iterator",
    "py/property",
    "py/default_factory",
    "py/ref",
    "py/bytes",
    "py/bytea",
    "py/memoryview",
    # Dispatched directly by the regular unpickler, absent from tags.RESERVED.
    "py/b64",
    "py/b85",
]


@pytest.mark.parametrize("tag", DISALLOWED_TAGS)
def test_data_only_rejects_reserved_markers(tag):
    payload = json.dumps({"x": {tag: "anything"}})
    with pytest.raises(DataOnlyDecodeError, match=tag):
        jsonpickle.decode(payload, data_only=True)


@pytest.mark.parametrize(
    "payload",
    [
        '[{"py/object": "os.system"}]',
        '[{"nested": [{"py/reduce": []}]}]',
        '{"a": {"b": {"c": {"py/type": "os.system"}}}}',
        '[{"a": 1}, [{"py/newargs": []}]]',
    ],
)
def test_data_only_rejects_markers_nested_inside_containers(payload):
    with pytest.raises(DataOnlyDecodeError):
        jsonpickle.decode(payload, data_only=True)


def test_data_only_rejects_json_key_smuggling():
    # A json:// key wraps another jsonpickle document and must not be decoded,
    # otherwise an object marker could hide inside the encoded key.
    payload = json.dumps({'json://{"py/object": "os.system"}': 1})
    with pytest.raises(DataOnlyDecodeError, match="json://"):
        jsonpickle.decode(payload, data_only=True)


def test_data_only_rejects_escaped_reserved_business_key():
    # The encoder escapes a business key that collides with a reserved marker
    # using json://; that escape cannot be honored without the object machinery.
    encoded = jsonpickle.encode({"py/object": 1})
    assert encoded.startswith('{"json://')
    with pytest.raises(DataOnlyDecodeError):
        jsonpickle.decode(encoded, data_only=True)


# ---------------------------------------------------------------------------
# Invalid py/id values must raise, never silently become None
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "value,label",
    [
        ('"1"', "str"),
        ("true", "bool"),
        ("false", "bool"),
        ("1.0", "float"),
        ("null", "NoneType"),
    ],
)
def test_data_only_rejects_non_integer_ids(value, label):
    payload = json.dumps([{"py/id": json.loads(value)}])
    with pytest.raises(DataOnlyDecodeError, match=label):
        jsonpickle.decode(payload, data_only=True)


def test_data_only_rejects_boolean_id_explicitly():
    # bool is an int subclass; True must not masquerade as index 1.
    with pytest.raises(DataOnlyDecodeError, match="bool"):
        jsonpickle.decode(json.dumps([{"py/id": True}]), data_only=True)


def test_data_only_rejects_negative_id():
    with pytest.raises(DataOnlyDecodeError, match="non-negative"):
        jsonpickle.decode(json.dumps([{"py/id": -1}]), data_only=True)


def test_data_only_rejects_out_of_range_id():
    with pytest.raises(DataOnlyDecodeError, match="out of range"):
        jsonpickle.decode(json.dumps([{"py/id": 5}]), data_only=True)


def test_data_only_rejects_out_of_range_id_nested_forward_ref():
    with pytest.raises(DataOnlyDecodeError, match="out of range"):
        jsonpickle.decode(json.dumps([[{"py/id": 9}]]), data_only=True)


def test_data_only_rejects_id_marker_with_extra_keys():
    with pytest.raises(DataOnlyDecodeError, match="must not contain other keys"):
        jsonpickle.decode(
            json.dumps([{"py/id": 0, "extra": "ignored?"}]), data_only=True
        )


def test_data_only_error_is_a_value_error():
    with pytest.raises(ValueError):
        jsonpickle.decode('{"py/object": "x"}', data_only=True)


# ---------------------------------------------------------------------------
# Side-effect guarantees: the object machinery must never be reached
# ---------------------------------------------------------------------------
class SideEffect:
    """A class whose every restoration hook records that it was touched."""

    events = []

    def __new__(cls, *args, **kwargs):
        cls.events.append("__new__")
        return super().__new__(cls)

    def __init__(self):
        self.events.append("__init__")

    def __setstate__(self, state):
        self.events.append("__setstate__")


class RecordingHandler(jsonpickle.handlers.BaseHandler):
    events = []

    def flatten(self, obj, data):
        data["py/object"] = "data_only_test.SideEffect"
        return data

    def restore(self, obj):
        self.events.append("handler.restore")
        return SideEffect()


def test_data_only_never_invokes_handler_or_class_hooks():
    jsonpickle.handlers.register(SideEffect, RecordingHandler)
    try:
        encoded = jsonpickle.encode(SideEffect())
        assert "py/object" in encoded

        # Sanity check: the ordinary path really does reach the machinery.
        SideEffect.events.clear()
        RecordingHandler.events.clear()
        jsonpickle.decode(encoded)
        assert RecordingHandler.events == ["handler.restore"]
        assert "__new__" in SideEffect.events

        # data_only must reject the same payload without touching either.
        SideEffect.events.clear()
        RecordingHandler.events.clear()
        with pytest.raises(DataOnlyDecodeError):
            jsonpickle.decode(encoded, data_only=True)
        assert SideEffect.events == []
        assert RecordingHandler.events == []
    finally:
        jsonpickle.handlers.unregister(SideEffect)


def test_data_only_classes_argument_cannot_bypass():
    encoded = json.dumps({"py/object": "data_only_test.SideEffect"})

    SideEffect.events.clear()
    with pytest.raises(DataOnlyDecodeError):
        jsonpickle.decode(
            encoded, data_only=True, classes=[SideEffect], on_missing="error"
        )
    assert SideEffect.events == []


def test_data_only_on_missing_callback_is_never_called():
    calls = []
    encoded = json.dumps({"py/object": "does.not.Exist"})
    with pytest.raises(DataOnlyDecodeError):
        jsonpickle.decode(
            encoded, data_only=True, on_missing=lambda name: calls.append(name)
        )
    assert calls == []


def test_data_only_blocks_eval_path_even_with_safe_false():
    # If validation did not run first, loadrepr() would import the module and
    # raise ModuleNotFoundError from inside eval().
    payload = json.dumps({"py/repr": "no_such_module_xyz/whatever"})
    with pytest.raises(DataOnlyDecodeError):
        jsonpickle.decode(payload, data_only=True, safe=False)


def test_data_only_does_not_import_modules():
    candidate = next(
        (name for name in ("wave", "shelve", "netrc", "tabnanny")
         if name not in __import__("sys").modules),
        None,
    )
    if candidate is None:  # pragma: no cover - environment dependent
        pytest.skip("all probe modules already imported")
    payload = json.dumps({"py/mod": f"{candidate}/{candidate}.whatever"})
    with pytest.raises(DataOnlyDecodeError):
        jsonpickle.decode(payload, data_only=True)
    assert candidate not in __import__("sys").modules


def test_data_only_failure_leaves_no_partial_state():
    unpickler = Unpickler(data_only=True)
    with pytest.raises(DataOnlyDecodeError):
        unpickler.restore(json.loads('[{"py/object": "x"}]'))
    assert unpickler._data_only_objs == []
    # The same instance is still usable afterwards and keeps independent state.
    assert unpickler.restore(json.loads("[1, 2]")) == [1, 2]
    # root list is index 0, the child dict is index 1.
    shared = unpickler.restore(json.loads('[{"k": 1}, {"py/id": 1}]'))
    assert shared[1] is shared[0]


class Plain:
    def __init__(self):
        self.value = 7


# ---------------------------------------------------------------------------
# Entry points and backwards compatibility
# ---------------------------------------------------------------------------
def test_data_only_works_through_loads_alias():
    assert jsonpickle.loads('{"a": [1]}', data_only=True) == {"a": [1]}


def test_data_only_works_with_direct_unpickler():
    unpickler = Unpickler(data_only=True)
    assert unpickler.restore(json.loads("[1, 2]")) == [1, 2]


def test_data_only_honors_prebuilt_context():
    unpickler = Unpickler(data_only=True)
    assert jsonpickle.decode("[1]", context=unpickler) == [1]


def test_data_only_supports_reset_false_multi_call_refs():
    unpickler = Unpickler(data_only=True)
    unpickler.restore(json.loads("[1]"), reset=False)
    decoded = unpickler.restore(json.loads('{"py/id": 0}'), reset=False)
    assert decoded == [1]


def test_default_mode_remains_unchanged():
    # Without data_only the historical object behavior is fully preserved.
    decoded = jsonpickle.decode(jsonpickle.encode(Plain()))
    assert type(decoded) is Plain
    assert decoded.value == 7


def test_data_only_defaults_to_off_in_constructor():
    assert Unpickler().data_only is False

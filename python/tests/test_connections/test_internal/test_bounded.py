"""
Unit tests for the internal bounded-collection helpers used by connection
classes to cap memory growth.
"""

import pytest

from barkr.connections.internal.bounded import BoundedIdSet, BoundedOrderedDict


def test_bounded_id_set_basic_set_semantics() -> None:
    """``BoundedIdSet`` behaves like a set for ``in``, ``bool``, ==."""
    s = BoundedIdSet(maxlen=10)
    assert not s
    assert s == set()

    s.add("a")
    s.update(["b", "c"])
    assert "a" in s
    assert "z" not in s
    assert bool(s)
    assert s == {"a", "b", "c"}


def test_bounded_id_set_evicts_oldest_when_capped() -> None:
    """Adding past ``maxlen`` evicts the least-recently-inserted id."""
    s = BoundedIdSet(maxlen=3)
    s.update(["a", "b", "c"])
    assert s == {"a", "b", "c"}

    s.add("d")
    assert s == {"b", "c", "d"}
    assert "a" not in s

    # Re-adding an existing id refreshes its position (becomes most recent).
    s.add("b")
    s.add("e")
    # State is now [c, d, b, e] -> over cap by 1 -> evict c -> [d, b, e]
    assert "c" not in s
    assert s == {"b", "d", "e"}


def test_bounded_id_set_rejects_invalid_maxlen() -> None:
    """``BoundedIdSet`` raises if initialized with invalid maxlen."""
    with pytest.raises(ValueError):
        BoundedIdSet(maxlen=0)


def test_bounded_ordered_dict_evicts_oldest_when_capped() -> None:
    """``BoundedOrderedDict`` evicts least-recently-set keys past the cap."""
    d: BoundedOrderedDict = BoundedOrderedDict(maxlen=3)
    d["a"] = 1
    d["b"] = 2
    d["c"] = 3
    assert list(d) == ["a", "b", "c"]

    d["d"] = 4
    assert list(d) == ["b", "c", "d"]
    assert "a" not in d

    # Updating an existing key moves it to the most-recent end.
    d["b"] = 20
    d["e"] = 5
    assert list(d) == ["d", "b", "e"]
    assert "c" not in d
    assert d["b"] == 20


def test_bounded_ordered_dict_rejects_invalid_maxlen() -> None:
    """``BoundedOrderedDict`` raises if initialized with invalid maxlen."""
    with pytest.raises(ValueError):
        BoundedOrderedDict(maxlen=0)


def test_bounded_id_set_equality_between_instances() -> None:
    """Two ``BoundedIdSet`` instances compare equal iff their order matches."""
    a = BoundedIdSet(maxlen=5)
    b = BoundedIdSet(maxlen=5)
    a.update(["x", "y", "z"])
    b.update(["x", "y", "z"])
    assert a == b

    b.add("z")  # already present; no order change
    assert a == b

    c = BoundedIdSet(maxlen=5)
    c.update(["z", "y", "x"])
    assert a != c


def test_bounded_id_set_equality_with_unrelated_type_returns_notimplemented() -> None:
    """``__eq__`` returns ``NotImplemented`` for unrelated types."""
    s = BoundedIdSet(maxlen=3)
    s.add("a")
    # Direct call to expose the NotImplemented branch (== would coerce to False).
    assert s.__eq__(123) is NotImplemented  # pylint: disable=unnecessary-dunder-call
    assert s.__eq__("a") is NotImplemented  # pylint: disable=unnecessary-dunder-call
    # And the high-level == still returns False for unrelated types.
    assert (s == 123) is False


def test_bounded_id_set_repr() -> None:
    """``__repr__`` includes the contents and the cap."""
    s = BoundedIdSet(maxlen=7)
    s.update(["a", "b"])
    text = repr(s)
    assert text.startswith("BoundedIdSet(")
    assert "maxlen=7" in text
    assert "'a'" in text and "'b'" in text

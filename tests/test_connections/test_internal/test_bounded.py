"""
Unit tests for the internal bounded-collection helpers used by connection
classes to cap memory growth.
"""

import pytest

from barkr.connections.internal.bounded import BoundedIdSet, BoundedOrderedDict


def test_bounded_id_set_basic_set_semantics() -> None:
    """``BoundedIdSet`` behaves like a set for ``in``, ``len``, ``bool``, ==."""
    s = BoundedIdSet(maxlen=10)
    assert not s
    assert len(s) == 0
    assert s == set()

    s.add("a")
    s.update(["b", "c"])
    assert "a" in s
    assert "z" not in s
    assert len(s) == 3
    assert bool(s)
    assert s == {"a", "b", "c"}
    assert sorted(iter(s)) == ["a", "b", "c"]


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

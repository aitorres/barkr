"""
Internal bounded-collection helpers used by connection classes to cap
memory growth in long-running processes.
"""

from collections import OrderedDict
from typing import Any, Final, Iterable, Iterator

# Maximum number of recently-posted message IDs retained per connection.
# Oldest IDs are evicted first (LRU). Size is big enough (vs. realistic polling windows)
# so the bound does not affect duplicate detection in practice.
POSTED_MESSAGE_IDS_MAX: Final[int] = 10_000

# Maximum number of source -> destination message-id mappings retained
# class-wide for ``ThreadAwareConnection`` instances.
MESSAGE_ID_MAP_MAX: Final[int] = 50_000


class BoundedIdSet:
    """
    Set-like container of ``str`` IDs with LRU eviction.

    New insertions move IDs to the most-recent end; when the configured cap is
    exceeded, the least recently inserted ID is evicted.
    """

    __slots__ = ("_data", "_maxlen")

    def __init__(self, maxlen: int = POSTED_MESSAGE_IDS_MAX) -> None:
        if maxlen < 1:
            raise ValueError("maxlen must be at least 1")

        self._data: OrderedDict[str, None] = OrderedDict()
        self._maxlen = maxlen

    def add(self, item: str) -> None:
        """Add an ID, refreshing its position; evict oldest if over cap."""

        if item in self._data:
            self._data.move_to_end(item)
        else:
            self._data[item] = None
            if len(self._data) > self._maxlen:
                self._data.popitem(last=False)

    def update(self, items: Iterable[str]) -> None:
        """Add multiple IDs."""

        for item in items:
            self.add(item)

    def __contains__(self, item: object) -> bool:
        return item in self._data

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __bool__(self) -> bool:
        return bool(self._data)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BoundedIdSet):
            return list(self._data) == list(other._data)

        if isinstance(other, (set, frozenset)):
            return set(self._data) == other

        return NotImplemented

    __hash__ = None  # type: ignore[assignment]

    def __repr__(self) -> str:
        return f"BoundedIdSet({set(self._data)!r}, maxlen={self._maxlen})"


class BoundedOrderedDict(OrderedDict):
    """
    ``OrderedDict`` with LRU-style size cap.

    On ``__setitem__``, an existing key is moved to the most-recent end;
    once the configured cap is exceeded, the least recently set key is
    evicted.
    """

    def __init__(self, maxlen: int = MESSAGE_ID_MAP_MAX) -> None:
        if maxlen < 1:
            raise ValueError("maxlen must be at least 1")

        super().__init__()
        self._maxlen = maxlen

    def __setitem__(self, key: Any, value: Any) -> None:
        if key in self:
            self.move_to_end(key)

        super().__setitem__(key, value)

        while len(self) > self._maxlen:
            self.popitem(last=False)

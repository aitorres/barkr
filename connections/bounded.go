// Package connections implements the base and specialized [Connection] types to handle
// the integration with specific platforms, social media services, and other external [Message]
// sources.
//
// A [Connection] is responsible for managing the lifecycle of a connection to an external
// services to send and/or receive [Message]s.
//
// The package provides a base [Connection] type that can be extended to implement specific
// types for a given platform. It also provides multiple built-in, specialized [Connection] types
// for popular platforms and services.
package connections

import "container/list"

// postedMessageIDsMax is the max amount of message IDs that can be stored
// in a [boundedIDSet]. Smaller threshold can be set, but any higher threshold
// (or unset threshold) will be clamped to this value.
const postedMessageIDsMax = 10_000

// boundedIDSet is a set-like container of strings, with least recently used (LRU)
// eviction up to a given threshold.
//
// New insertions move IDs to the most-recent end; when the configured cap is
// exceeded, the least recently inserted ID is evicted.
type boundedIDSet struct {
	// maxLen is the upper bound for the set elements.
	maxLen int
	// order is a doubly linked list that preserves the order of elements
	// during insertion and update operations.
	order *list.List
	// items maps IDs (strings) to their linked list elements, to easily
	// check for existence and perform removals.
	items map[string]*list.Element
}

// newBoundedIDSet creates and returns a new instance of [boundedIDSet].
func newBoundedIDSet(maxLen int) *boundedIDSet {
	if maxLen < 1 {
		maxLen = postedMessageIDsMax
	}

	return &boundedIDSet{
		maxLen: maxLen,
		order:  list.New(),
		items:  make(map[string]*list.Element, maxLen),
	}
}

// Add inserts an ID into the [boundedIDSet] by placing it at the
// end of the set. If the item was already in the set, its order is refreshed.
func (s *boundedIDSet) Add(id string) {
	if el, ok := s.items[id]; ok {
		s.order.MoveToBack(el)
		return
	}

	s.items[id] = s.order.PushBack(id)
	if s.order.Len() > s.maxLen {
		oldest := s.order.Front()
		if oldest != nil {
			s.order.Remove(oldest)
			delete(s.items, oldest.Value.(string))
		}
	}
}

// Update takes a slice of IDs and inserts each one, in-order.
func (s *boundedIDSet) Update(items []string) {
	for _, item := range items {
		s.Add(item)
	}
}

// Contains reports if a given ID is currently in the [boundedIDSet].
func (s *boundedIDSet) Contains(item string) bool {
	_, ok := s.items[item]
	return ok
}

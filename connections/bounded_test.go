package connections

import "testing"

func TestBoundedIDsSetSemantics(t *testing.T) {
	s := newBoundedIDSet(10)
	if s == nil {
		t.Errorf("expected non-nil bounded set")
	}

	s.Add("a")
	s.Update([]string{"b", "c"})
	if !s.Contains("a") {
		t.Errorf("expected set to contain 'a'")
	}
	if !s.Contains("c") {
		t.Errorf("expected set to contain 'c'")
	}
	if s.Contains("z") {
		t.Errorf("expected set not to contain 'a'")
	}

	s.Add("a")
	if !s.Contains("a") {
		t.Errorf("expected set to contain 'a'")
	}
}

func TestBoundedIDsSetEvictsOldest(t *testing.T) {
	s := newBoundedIDSet(3)

	s.Update([]string{"a", "b", "c"})
	if !s.Contains("a") {
		t.Errorf("expected set to contain 'a'")
	}

	s.Add("d")
	if !s.Contains("d") {
		t.Errorf("expected set to contain 'd'")
	}
	if s.Contains("a") {
		t.Errorf("expected set not to contain 'a'")
	}

	s.Add("b")
	s.Add("e")
	if !s.Contains("b") {
		t.Errorf("expected set to contain 'b'")
	}
	if s.Contains("c") {
		t.Errorf("expected set not to contain 'c'")
	}
	if !s.Contains("e") {
		t.Errorf("expected set to contain 'e'")
	}
}

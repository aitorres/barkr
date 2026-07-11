package connections

import (
	"errors"
	"testing"

	"github.com/aitorres/barkr/models"
)

type fakeConnection struct {
	*BaseConnection
	fetchFn func() ([]models.Message, error)
	postFn  func([]models.Message) ([]string, error)
}

func (f *fakeConnection) Read() []models.Message {
	return f.ApplyRead(f.fetchFn)
}

func (f *fakeConnection) Write(messages []models.Message) error {
	return f.ApplyWrite(messages, f.postFn)
}

func newFake(t *testing.T, name string, modes []ConnectionMode, group string, opts ...Option) *fakeConnection {
	t.Helper()
	base, err := NewBaseConnection(name, modes, group, opts...)
	if err != nil {
		t.Fatalf("NewBaseConnection: %v", err)
	}
	return &fakeConnection{BaseConnection: base}
}

func TestNewBaseConnectionValidation(t *testing.T) {
	if _, err := NewBaseConnection("No Modes", nil, ""); err == nil {
		t.Error("expected error for no modes")
	}
	if _, err := NewBaseConnection("Dup", []ConnectionMode{ConnectionModeRead, ConnectionModeRead}, ""); err == nil {
		t.Error("expected error for duplicate modes")
	}
}

func TestBaseConnectionGroups(t *testing.T) {
	c := newFake(t, "No Group", []ConnectionMode{ConnectionModeRead}, "")
	if c.Group() != defaultConnectionGroup {
		t.Errorf("group = %q, want %s", c.Group(), defaultConnectionGroup)
	}
	g := newFake(t, "Grouped", []ConnectionMode{ConnectionModeRead}, "my-group")
	if g.Group() != "my-group" {
		t.Errorf("group = %q", g.Group())
	}
}

func TestBaseConnectionModeGating(t *testing.T) {
	readOnly := newFake(t, "Read Only", []ConnectionMode{ConnectionModeRead}, "")
	posted := false
	readOnly.postFn = func([]models.Message) ([]string, error) {
		posted = true
		return nil, nil
	}
	_ = readOnly.Write([]models.Message{{ID: "id1", Message: "x"}})
	if posted {
		t.Error("write-mode-less connection should not post")
	}

	writeOnly := newFake(t, "Write Only", []ConnectionMode{ConnectionModeWrite}, "")
	fetched := false
	writeOnly.fetchFn = func() ([]models.Message, error) {
		fetched = true
		return nil, nil
	}
	if got := writeOnly.Read(); got != nil {
		t.Errorf("read = %v, want nil", got)
	}
	if fetched {
		t.Error("read-mode-less connection should not fetch")
	}
}

func TestBaseConnectionDedup(t *testing.T) {
	c := newFake(t, "Read/Write", []ConnectionMode{ConnectionModeRead, ConnectionModeWrite}, "")
	c.fetchFn = func() ([]models.Message, error) {
		return []models.Message{
			{ID: "1", Message: "m1"}, {ID: "2", Message: "m2"}, {ID: "3", Message: "m3"},
		}, nil
	}
	c.postFn = func(msgs []models.Message) ([]string, error) {
		ids := make([]string, len(msgs))
		for i, m := range msgs {
			ids[i] = m.ID
		}
		return ids, nil
	}

	_ = c.Write([]models.Message{{ID: "1", Message: "m1"}, {ID: "2", Message: "m2"}, {ID: "3", Message: "m3"}})
	if !c.HasPostedID("1") || !c.HasPostedID("3") {
		t.Error("posted ids not recorded")
	}

	if got := c.Read(); len(got) != 0 {
		t.Errorf("read after posting same ids = %d, want 0", len(got))
	}
}

func TestBaseConnectionReadSwallowsError(t *testing.T) {
	c := newFake(t, "Read", []ConnectionMode{ConnectionModeRead}, "")
	attempts := 0
	c.fetchFn = func() ([]models.Message, error) {
		attempts++
		if attempts == 1 {
			return nil, errors.New("boom")
		}
		return []models.Message{{ID: "1", Message: "m1"}}, nil
	}

	if got := c.Read(); len(got) != 0 {
		t.Errorf("first read = %d, want 0 (error swallowed)", len(got))
	}
	if got := c.Read(); len(got) != 1 {
		t.Errorf("second read = %d, want 1", len(got))
	}
}

func TestBaseConnectionSkipsEmptyAndMedia(t *testing.T) {
	c := newFake(t, "Write", []ConnectionMode{ConnectionModeWrite}, "")
	var posted []string
	c.postFn = func(msgs []models.Message) ([]string, error) {
		for _, m := range msgs {
			posted = append(posted, m.ID)
		}
		return posted, nil
	}

	_ = c.Write([]models.Message{{ID: "1", Message: ""}})
	if len(posted) != 0 {
		t.Errorf("empty message posted: %v", posted)
	}

	_ = c.Write([]models.Message{{ID: "1", Message: ""}, {ID: "2", Message: "m2"}, {ID: "3", Message: "m3"}})
	if !equal(posted, []string{"2", "3"}) {
		t.Errorf("posted = %v, want [2 3]", posted)
	}

	cm := newFake(t, "WriteMedia", []ConnectionMode{ConnectionModeWrite}, "", WithSupportedMessageType(models.MessageTypeTextMedia))
	var postedMedia []string
	cm.postFn = func(msgs []models.Message) ([]string, error) {
		for _, m := range msgs {
			postedMedia = append(postedMedia, m.ID)
		}
		return postedMedia, nil
	}
	_ = cm.Write([]models.Message{
		{ID: "4", Message: "", Media: []models.Media{{MIMEType: "image/jpeg", Content: []byte("d")}}},
	})
	if !equal(postedMedia, []string{"4"}) {
		t.Errorf("posted = %v, want [4]", postedMedia)
	}

	var postedText []string
	c.postFn = func(msgs []models.Message) ([]string, error) {
		for _, m := range msgs {
			postedText = append(postedText, m.ID)
		}
		return postedText, nil
	}
	_ = c.Write([]models.Message{
		{ID: "9", Message: "", Media: []models.Media{{MIMEType: "image/jpeg", Content: []byte("d")}}},
	})
	if len(postedText) != 0 {
		t.Errorf("text-only connection posted media-only message: %v", postedText)
	}
}

func equal(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

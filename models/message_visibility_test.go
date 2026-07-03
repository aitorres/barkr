package models

import "testing"

func TestMessageVisibilityToMastodonVisibility(t *testing.T) {
	tests := []struct {
		mv       MessageVisibility
		expected string
	}{
		{MessageVisibilityPublic, "public"},
		{MessageVisibilityUnlisted, "unlisted"},
		{MessageVisibilityPrivate, "private"},
		{MessageVisibilityDirect, "direct"},
		{MessageVisibility(999), "public"}, // unknown visibility defaults to "public"
	}

	for _, tt := range tests {
		result := tt.mv.ToMastodonVisibility()
		if result != tt.expected {
			t.Errorf("ToMastodonVisibility(%v) = %v; want %v", tt.mv, result, tt.expected)
		}
	}
}

func TestMastodonVisibilityToMessageVisibility(t *testing.T) {
	tests := []struct {
		input         string
		expected      MessageVisibility
		errorExpected bool
	}{
		{"public", MessageVisibilityPublic, false},
		{"unlisted", MessageVisibilityUnlisted, false},
		{"private", MessageVisibilityPrivate, false},
		{"direct", MessageVisibilityDirect, false},
		{"unknown", 0, true}, // unknown visibility should return an error
	}

	for _, tt := range tests {
		result, err := MastodonVisibilityToMessageVisibility(tt.input)

		if (err != nil) != tt.errorExpected {
			t.Errorf("MastodonVisibilityToMessageVisibility(%v) error = %v; want error: %v", tt.input, err, tt.errorExpected)
		}

		if result != tt.expected && !tt.errorExpected {
			t.Errorf("MastodonVisibilityToMessageVisibility(%v) = %v; want %v", tt.input, result, tt.expected)
		}
	}
}

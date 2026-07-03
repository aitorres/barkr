package models

import "testing"

func TestMentionStyleString(t *testing.T) {
	tests := []struct {
		style    MentionStyle
		expected string
	}{
		{MentionStylePlain, "plain"},
		{MentionStyleAppendURL, "append-url"},
		{MentionStyleReplaceWithURL, "replace-with-url"},
		{MentionStyleMarkdownLink, "markdown-link"},
		{MentionStyleHTMLLink, "html-link"},
		{MentionStyle(999), "unknown (999)"},
	}

	for _, test := range tests {
		result := test.style.String()

		if result != test.expected {
			t.Errorf("expected %s, got %s", test.expected, result)
		}
	}
}

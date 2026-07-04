package helpers

import (
	"slices"
	"testing"
)

func TestExtractURLsFromText(t *testing.T) {
	tt := []struct {
		text string
		want []string
	}{
		{
			text: "Hello world!",
			want: []string{},
		},
		{
			text: "Hello https://example.com",
			want: []string{"https://example.com"},
		},
		{
			text: "Hello http://example.com",
			want: []string{"http://example.com"},
		},
		{
			text: "Hello ftp://example.com",
			want: []string{},
		},
		{
			text: "Hello http://example.com and https://example.org",
			want: []string{"http://example.com", "https://example.org"},
		},
		{
			text: "Hello http://example.com/path/to/resource",
			want: []string{"http://example.com/path/to/resource"},
		},
	}

	for _, tc := range tt {
		got := ExtractURLsFromText(tc.text)
		if !slices.Equal(got, tc.want) {
			t.Errorf("ExtractURLsFromText(%q) = %v, want %v", tc.text, got, tc.want)
		}
	}
}

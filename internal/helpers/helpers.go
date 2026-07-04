// Package helpers provides utility functions for image processing and manipulation,
// as well as generic tools used across the codebase.
package helpers

import (
	"regexp"
)

// ExtractURLsFromText returns all URLs contained inside a text.
func ExtractURLsFromText(text string) []string {
	URLRegexPattern := regexp.MustCompile(`http[s]?://[^\s]+`)
	return URLRegexPattern.FindAllString(text, -1)
}

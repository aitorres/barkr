package models

import (
	"fmt"
	"strings"
)

// MentionStyle represents how user mentions should be rendered when
// serializing a [Message] for a given [Connection]. Each [Connection] implementation
// can decide how to display mentions from an incoming [Message] based on what
// they support.
type MentionStyle int

const (
	// MentionStylePlain indicates that the [Message] is rendered as-is, with no mention enrichment
	MentionStylePlain MentionStyle = iota
	// MentionStyleAppendURL indicates that user mentions on the [Message] are enriched with the profile URL in parenthesis next to it
	MentionStyleAppendURL
	// MentionStyleReplaceWithURL indicates that user mentions on the [Message] are replaced with the profile URL
	MentionStyleReplaceWithURL
	// MentionStyleMarkdownLink indicates that user mentions on the [Message] are linked to the profile URL using Markdown syntax
	MentionStyleMarkdownLink
	// MentionStyleHTMLLink indicates that user mentions on the [Message] are linked to the profile URL using HTML syntax (anchor tag)
	MentionStyleHTMLLink
)

// String returns the string representation of the [MentionStyle].
func (m MentionStyle) String() string {
	switch m {
	case MentionStylePlain:
		return "plain"
	case MentionStyleAppendURL:
		return "append-url"
	case MentionStyleReplaceWithURL:
		return "replace-with-url"
	case MentionStyleMarkdownLink:
		return "markdown-link"
	case MentionStyleHTMLLink:
		return "html-link"
	default:
		return fmt.Sprintf("unknown (%d)", m)
	}
}

// ReplaceMentions replaces or enriches user mentions in a given text according
// to the specified [MentionStyle].
func ReplaceMentions(text string, mentions []MessageMention, style MentionStyle) (string, error) {
	if style == MentionStylePlain || len(mentions) == 0 {
		return text, nil
	}

	var contentParts []string

	cursor := 0
	for _, mention := range mentions {
		index := strings.Index(text[cursor:], mention.Username)

		if index == -1 {
			continue
		}

		start := cursor + index
		contentParts = append(contentParts, text[cursor:start])

		var replacement string
		switch style {
		case MentionStyleAppendURL:
			replacement = fmt.Sprintf("%s (%s)", mention.Username, mention.URL)
		case MentionStyleReplaceWithURL:
			replacement = mention.URL
		case MentionStyleMarkdownLink:
			replacement = fmt.Sprintf("[%s](%s)", mention.Username, mention.URL)
		case MentionStyleHTMLLink:
			replacement = fmt.Sprintf("<a href=\"%s\">%s</a>", mention.URL, mention.Username)
		default:
			return "", fmt.Errorf("unsupported mention style: %s", style)
		}

		contentParts = append(contentParts, replacement)
		cursor = start + len(mention.Username)
	}

	contentParts = append(contentParts, text[cursor:])
	return strings.Join(contentParts, ""), nil
}

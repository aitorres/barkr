package models

import (
	"fmt"
	"slices"
	"strings"
)

// Message represents a generic message, post or publication object.
//
// [Message]s can be retrieved from a source platform via a read-mode [Connection] or instantiated directly,
// and can be posted to a target platform via a write-mode [Connection].
//
// The [Message] struct contains an ID that identifies the post on the source platform, the textual content,
// its source connection, and potentially a list of media attachments.
//
// Optionally, it can also include structured Metadata for interoperability between
// supported [Connections], based on each platform's capabilities and implementation.
type Message struct {
	ID               string          // unique identifier of the message on the source platform
	Message          string          // textual content of the message
	SourceConnection string          // identifier of the source connection
	Media            []Media         // list of media attachments
	Metadata         MessageMetadata // structured metadata
	ReplyToID        string          // identifier of the message this message is replying to, if any
}

// String returns a string representation of the [Message] object.
func (m *Message) String() string {
	return fmt.Sprintf("\"%s\" (ID: %s, source: %s)", m.Message, m.ID, m.SourceConnection)
}

// HasContent checks if the [Message] has any non-empty content based on the specified [MessageType].
func (m *Message) HasContent(messageType MessageType) bool {
	if m == nil {
		return false
	}

	if slices.Contains(unsupportedMessageVisibilities, m.Metadata.Visibility) {
		return false
	}

	hasText := strings.TrimSpace(m.Message) != ""
	hasMedia := len(m.Media) > 0 && slices.ContainsFunc(m.Media, func(media Media) bool {
		return media.IsValid()
	})

	switch messageType {
	case MessageTypeMediaOnly:
		return hasMedia
	case MessageTypeTextMedia:
		return hasText || hasMedia
	default:
		return hasText
	}
}

// GetContent retrieves the textual content of the [Message], optionally
// replacing mentions with a specified [MentionStyle].
func (m *Message) GetContent(mentionStyle MentionStyle) (string, error) {
	if m == nil {
		return "", fmt.Errorf("message is nil")
	}

	return ReplaceMentions(m.Message, m.Metadata.Mentions, mentionStyle)
}

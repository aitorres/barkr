package models

import "fmt"

// MessageVisibility represents the visibility of a [Message] in the source [Connection],
// so it is mapped to the appropriate visibility in the destination [Connection].
type MessageVisibility int

const (
	MessageVisibilityPublic   MessageVisibility = iota // public and visible to everyone
	MessageVisibilityUnlisted                          // unlisted but accessible via a direct link
	MessageVisibilityPrivate                           // private and visible only to the user's followers
	MessageVisibilityDirect                            // direct and visible only to specific users (e.g. a chat or direct message)
)

var (
	// unsupportedMessageVisibilities lists the [MessageVisibility] values that we do not support
	// on barkr, to prevent any private message leaks. Any [Message] whose visibility is set to one
	// of these values will be dropped silently.
	unsupportedMessageVisibilities = []MessageVisibility{
		MessageVisibilityDirect,
		MessageVisibilityPrivate,
	}
)

// String returns the string representation of the [MessageVisibility].
func (mv MessageVisibility) String() string {
	switch mv {
	case MessageVisibilityPublic:
		return "public"
	case MessageVisibilityUnlisted:
		return "unlisted"
	case MessageVisibilityPrivate:
		return "private"
	case MessageVisibilityDirect:
		return "direct"
	default:
		return fmt.Sprintf("unknown (%d)", mv)
	}
}

// MastodonVisibilityToMessageVisibility converts a Mastodon visibility string to a [MessageVisibility] value.
func MastodonVisibilityToMessageVisibility(mv string) (MessageVisibility, error) {
	switch mv {
	case "public":
		return MessageVisibilityPublic, nil
	case "unlisted":
		return MessageVisibilityUnlisted, nil
	case "private":
		return MessageVisibilityPrivate, nil
	case "direct":
		return MessageVisibilityDirect, nil
	default:
		return 0, fmt.Errorf("unknown Mastodon visibility: %s", mv)
	}
}

// ToMastodonVisibility converts a [MessageVisibility] value to a Mastodon visibility string, defaulting to "public" for unknown values.
func (mv MessageVisibility) ToMastodonVisibility() string {
	switch mv {
	case MessageVisibilityUnlisted:
		return "unlisted"
	case MessageVisibilityPrivate:
		return "private"
	case MessageVisibilityDirect:
		return "direct"
	default:
		return "public"
	}
}

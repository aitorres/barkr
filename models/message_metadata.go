package models

// MessageMetadata represents the optional metadata of a [Message] based on its source
// [Connection], including its language, label, visibility, allowed replies, and mentions.
//
// This metadata can be used to enrich the message while it's being published on a target
// platform, and each [Connection] implementation can decide how to map this metadata, if
// applicable, to the target platform's [Message] properties.
//
// The zero value represents a public [Message] with no specific language, label, or allowed replies, and no mentions.
type MessageMetadata struct {
	Language       string                // language of the [Message]
	Label          string                // content label in use for the [Message]
	Visibility     MessageVisibility     // visibility of the [Message] (who can see it) in the source platform
	AllowedReplies MessageAllowedReplies // who can reply to the [Message] in the source platform
	Mentions       []MessageMention      // users mentioned in the [Message]
}

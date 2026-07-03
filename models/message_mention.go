package models

// MessageMention represents a user mentioned in a [Message], including their profile
// URL and the username on the source [Connection]'s platform. This metadata can be used to
// enrich the [Message] and mentions when being published on a target platform, and each
// [Connection] implementation can decide how to map this metadata, if at all.
//
// If the same user is mentioned multiple times in a [Message], the [MessageMention] should
// also be repeated in the [MessageMetadata.Mentions] slice.
type MessageMention struct {
	URL      string // profile URL of the mentioned user on the source [Connection]'s platform.
	Username string // username of the mentioned user on the source [Connection]'s platform.
}

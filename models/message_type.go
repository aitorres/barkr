package models

// MessageType represents the type of supported [Message]s on a [Connection],
// based on the platform's support for text and media content.
type MessageType int

const (
	MessageTypeTextOnly  MessageType = iota // text-only messages
	MessageTypeMediaOnly                    // media-only messages
	MessageTypeTextMedia                    // can contain text and/or media
)

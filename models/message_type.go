package models

// MessageType represents the type of supported [Message]s on a [Connection],
// based on the platform's support for text and media content.
type MessageType int

const (
	// MessageTypeTextOnly indicates that the message is text-only
	MessageTypeTextOnly MessageType = iota
	// MessageTypeMediaOnly indicates that the message is media-only
	MessageTypeMediaOnly
	// MessageTypeTextMedia indicates that the message can contain text and/or media
	MessageTypeTextMedia
)

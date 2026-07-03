package models

import "slices"

// supportedMIMETypes lists the MIME types that Barker can process for media attachments in messages.
var supportedMIMETypes = []string{
	"image/jpeg",
	"image/png",
	"image/gif",
	"image/webp",
	"video/mp4",
	"video/quicktime",
}

// Media represents a generic media attachment in a message, like an image or a video.
// The struct preserves the MIME type and binary content, as well as any alternative text,
// and allows the media to be retrieved as part of a message's content, or posted to a
// target platform.
type Media struct {
	MIMEType string // MIME type of the media (e.g., "image/png", "video/mp4").
	Content  []byte // binary content of the media.
	AltText  string // alternative text for the media, useful for accessibility and descriptions.
}

// IsValid reports whether the [Media] instance represents a valid, non-empty media attachment.
// Valid MIME types are enumerated in [supportedMIMETypes].
func (m *Media) IsValid() bool {
	if m == nil {
		return false
	}

	if m.MIMEType == "" || len(m.Content) == 0 {
		return false
	}

	return slices.Contains(supportedMIMETypes, m.MIMEType)
}

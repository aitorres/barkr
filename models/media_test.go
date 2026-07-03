package models

import (
	"testing"
)

func TestMediaIsValid(t *testing.T) {
	tt := []struct {
		media         Media
		expectedValid bool
	}{
		{
			media: Media{
				MIMEType: "image/png",
				Content:  []byte{0x89, 0x50, 0x4E, 0x47},
				AltText:  "",
			},
			expectedValid: true,
		},
		{
			media: Media{
				MIMEType: "image/jpeg",
				Content:  []byte{0xFF, 0xD8, 0xFF},
				AltText:  "A sample image",
			},
			expectedValid: true,
		},
		{
			media: Media{
				MIMEType: "video/mp4",
				Content:  []byte{0x00, 0x00, 0x00, 0x18},
				AltText:  "",
			},
			expectedValid: true,
		},
		{
			media: Media{
				MIMEType: "image/png",
				Content:  []byte{},
			},
			expectedValid: false,
		},
		{
			media: Media{
				MIMEType: "application/pdf",
				Content:  []byte{0x25, 0x50, 0x44, 0x46},
			},
			expectedValid: false,
		},
		{
			media: Media{
				MIMEType: "",
				Content:  []byte{0x89, 0x50, 0x4E, 0x47},
			},
			expectedValid: false,
		},
	}

	for _, tc := range tt {
		if tc.media.IsValid() != tc.expectedValid {
			t.Errorf("expected IsValid() to return %v for media %+v", tc.expectedValid, tc.media)
		}
	}

	var nilMedia *Media
	if nilMedia.IsValid() {
		t.Error("expected nil media to be invalid")
	}
}

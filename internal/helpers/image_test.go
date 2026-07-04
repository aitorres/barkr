package helpers

import (
	"bytes"
	"image"
	"image/color"
	"testing"

	"github.com/disintegration/imaging"
)

// makeGradientJPEG builds a smooth gradient image encoded as a high-quality
// JPEG. The image is large in bytes but downscales to a much smaller size.
func makeGradientJPEG(t *testing.T, width, height int) []byte {
	t.Helper()

	img := image.NewRGBA(image.Rect(0, 0, width, height))
	for y := range height {
		for x := range width {
			img.Set(x, y, color.RGBA{
				R: uint8(x * 255 / width),
				G: uint8(y * 255 / height),
				B: uint8((x + y) * 255 / (width + height)),
				A: 255,
			})
		}
	}

	var buf bytes.Buffer
	if err := imaging.Encode(&buf, img, imaging.JPEG, imaging.JPEGQuality(100)); err != nil {
		t.Fatalf("failed to encode gradient jpeg: %v", err)
	}
	return buf.Bytes()
}

func TestCompressImage(t *testing.T) {
	// A 1000x1000 gradient encodes to ~211KB at quality 100
	image := makeGradientJPEG(t, 1000, 1000)

	t.Run("returns original when already within limit", func(t *testing.T) {
		input := []byte{0x01, 0x02, 0x03, 0x04}

		got, err := CompressImage(input, len(input))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if !bytes.Equal(got, input) {
			t.Errorf("expected original bytes to be returned unchanged")
		}
	})

	t.Run("returns error for undecodable image over the limit", func(t *testing.T) {
		input := bytes.Repeat([]byte{0xFF}, 200)

		got, err := CompressImage(input, 100)
		if err == nil {
			t.Fatalf("expected error for undecodable image, got nil")
		}
		if got != nil {
			t.Errorf("expected nil bytes on error, got %d bytes", len(got))
		}
	})

	t.Run("compresses image within the limit", func(t *testing.T) {
		limit := 50_000

		got, err := CompressImage(image, limit)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if len(got) >= len(image) {
			t.Errorf("expected output to be smaller than input (%d bytes), got %d", len(image), len(got))
		}
		if len(got) > limit {
			t.Errorf("expected compressed size <= %d, got %d", limit, len(got))
		}
		if _, err := imaging.Decode(bytes.NewReader(got)); err != nil {
			t.Errorf("expected compressed output to be a valid image: %v", err)
		}
	})

	t.Run("returns error when target size is unreachable", func(t *testing.T) {
		got, err := CompressImage(image, 5_000)
		if err == nil {
			t.Fatalf("expected error for unreachable target size, got nil")
		}
		if got != nil {
			t.Errorf("expected nil bytes on error, got %d bytes", len(got))
		}
	})
}

func TestResponseContainsImage(t *testing.T) {
	tt := []struct {
		contentType string
		body        []byte
		want        bool
	}{
		{
			contentType: "image/jpeg",
			body:        []byte{0x89, 0x50, 0x4E, 0x47},
			want:        true,
		},
		{
			contentType: "image/png",
			body:        []byte{0x89, 0x50, 0x4E, 0x47},
			want:        true,
		},
		{
			contentType: "video/mp4",
			body:        []byte{},
			want:        false,
		},
		{
			contentType: "video/mp4",
			body:        []byte{0x89, 0x50, 0x4E, 0x47},
			want:        false,
		},
	}

	for _, tc := range tt {
		got := ResponseContainsImage(tc.contentType, tc.body)
		if got != tc.want {
			t.Errorf("expected %t, got %t", tc.want, got)
		}
	}
}

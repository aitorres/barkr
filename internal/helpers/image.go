package helpers

import (
	"bytes"
	"errors"
	"fmt"
	"log/slog"
	"strings"

	"github.com/disintegration/imaging"
)

var (
	// scaleFactors determines the scaling to apply to images during compression attempts
	scaleFactors = []float64{0.8, 0.75}
	// qualitySteps determines the quality options to use when encoding a compressed image
	qualitySteps = []int{85, 70}
)

// ResponseContainsImage reports whether an HTTP response and body contain
// image data, based on the content type header and/or content.
func ResponseContainsImage(contentType string, body []byte) bool {
	if strings.HasPrefix(contentType, "image/") {
		return true
	}

	imageReader := bytes.NewReader(body)
	_, err := imaging.Decode(imageReader)
	return err == nil
}

// CompressImage attempts to compress an image to fit within the given size limit (in bytes),
// iteratively reducing the image's dimensions and using different quality factors.
func CompressImage(imageData []byte, sizeLimitBytes int) ([]byte, error) {
	if len(imageData) <= sizeLimitBytes {
		return imageData, nil
	}

	imageReader := bytes.NewReader(imageData)
	image, err := imaging.Decode(imageReader)
	if err != nil {
		slog.Error("unable to open image for compression", "error", err)
		return nil, fmt.Errorf("failed to decode image: %w", err)
	}

	bounds := image.Bounds()
	width, height := float64(bounds.Dx()), float64(bounds.Dy())

	for _, scaleFactor := range scaleFactors {
		newWidth, newHeight := max(1, int(width*scaleFactor)), max(1, int(height*scaleFactor))

		resizedImage := imaging.Resize(image, newWidth, newHeight, imaging.Lanczos)
		for _, quality := range qualitySteps {
			var imageBuffer bytes.Buffer
			if err := imaging.Encode(&imageBuffer, resizedImage, imaging.JPEG, imaging.JPEGQuality(quality)); err != nil {
				slog.Warn("unable to encode resized image", "scale", scaleFactor, "quality", quality, "error", err)
				continue
			}

			if imageBuffer.Len() <= sizeLimitBytes {
				return imageBuffer.Bytes(), nil
			}
		}

	}

	return nil, errors.New("unable to compress image to target size")
}

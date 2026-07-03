package models

import (
	"testing"
)

func TestMessageHasContent(t *testing.T) {
	tt := []struct {
		message            Message
		messageType        MessageType
		expectedHasContent bool
	}{
		{
			message: Message{
				Message: "Hello, world!",
			},
			messageType:        MessageTypeTextOnly,
			expectedHasContent: true,
		},
		{
			message: Message{
				Message: "Hello, world!",
			},
			messageType:        MessageTypeTextMedia,
			expectedHasContent: true,
		},
		{
			message: Message{
				Message: "Hello, world!",
			},
			messageType:        MessageTypeMediaOnly,
			expectedHasContent: false,
		},
		{
			message: Message{
				Message: "",
				Media: []Media{
					{
						MIMEType: "image/png",
						Content:  []byte{0x89, 0x50, 0x4E, 0x47},
					},
				},
			},
			messageType:        MessageTypeMediaOnly,
			expectedHasContent: true,
		},
		{
			message: Message{
				Message: "",
				Media: []Media{
					{
						MIMEType: "image/png",
						Content:  []byte{0x89, 0x50, 0x4E, 0x47},
					},
				},
			},
			messageType:        MessageTypeTextOnly,
			expectedHasContent: false,
		},
		{
			message: Message{
				Message: "",
				Media: []Media{
					{
						MIMEType: "image/png",
						Content:  []byte{0x89, 0x50, 0x4E, 0x47},
					},
				},
			},
			messageType:        MessageTypeTextMedia,
			expectedHasContent: true,
		},
		{
			message: Message{
				Message: "",
			},
			messageType:        MessageTypeTextOnly,
			expectedHasContent: false,
		},
		{
			message: Message{
				Message: "   ",
			},
			messageType:        MessageTypeTextOnly,
			expectedHasContent: false,
		},
		{
			message: Message{
				Message: "\t\n",
			},
			messageType:        MessageTypeTextOnly,
			expectedHasContent: false,
		},
		{
			message: Message{
				Message: "\t.  hello \n",
			},
			messageType:        MessageTypeTextOnly,
			expectedHasContent: true,
		},
		{
			message: Message{
				Message: "",
				Media: []Media{
					{
						MIMEType: "application/pdf",
						Content:  []byte{0x25, 0x50, 0x44, 0x46},
					},
				},
			},
			messageType:        MessageTypeMediaOnly,
			expectedHasContent: false,
		},
		{
			message:            Message{},
			messageType:        MessageTypeTextOnly,
			expectedHasContent: false,
		},
		{
			message:            Message{},
			messageType:        MessageTypeMediaOnly,
			expectedHasContent: false,
		},
		{
			message:            Message{},
			messageType:        MessageTypeTextMedia,
			expectedHasContent: false,
		},
	}

	for _, tc := range tt {
		if tc.message.HasContent(tc.messageType) != tc.expectedHasContent {
			t.Errorf("Expected HasContent to be %v for message type %v, but got %v", tc.expectedHasContent, tc.messageType, !tc.expectedHasContent)
		}
	}
}

func TestMessageGetContent(t *testing.T) {
	tt := []struct {
		message      Message
		mentionStyle MentionStyle
		want         string
	}{
		{
			message: Message{
				Message: "Hello, world!",
			},
			mentionStyle: MentionStylePlain,
			want:         "Hello, world!",
		},
		{
			message: Message{
				Message: "Hello, world!",
			},
			mentionStyle: MentionStyleMarkdownLink,
			want:         "Hello, world!",
		},
		{
			message: Message{
				Message: "Hello, world!",
				Metadata: MessageMetadata{
					Mentions: []MessageMention{
						{
							Username: "@alice.bsky.social",
							URL:      "https://bsky.social/profile/did:plc:alice",
						},
					},
				},
			},
			mentionStyle: MentionStylePlain,
			want:         "Hello, world!",
		},
		{
			message: Message{
				Message: "Hello, world!",
				Metadata: MessageMetadata{
					Mentions: []MessageMention{
						{
							Username: "@alice.bsky.social",
							URL:      "https://bsky.social/profile/did:plc:alice",
						},
					},
				},
			},
			mentionStyle: MentionStyleMarkdownLink,
			want:         "Hello, world!",
		},
		{
			message: Message{
				Message: "Hello, @alice.bsky.social!",
				Metadata: MessageMetadata{
					Mentions: []MessageMention{
						{
							Username: "@alice.bsky.social",
							URL:      "https://bsky.social/profile/did:plc:alice",
						},
					},
				},
			},
			mentionStyle: MentionStylePlain,
			want:         "Hello, @alice.bsky.social!",
		},
		{
			message: Message{
				Message: "Hello, @alice.bsky.social!",
				Metadata: MessageMetadata{
					Mentions: []MessageMention{
						{
							Username: "@alice.bsky.social",
							URL:      "https://bsky.social/profile/did:plc:alice",
						},
					},
				},
			},
			mentionStyle: MentionStyleMarkdownLink,
			want:         "Hello, [@alice.bsky.social](https://bsky.social/profile/did:plc:alice)!",
		},
		{
			message: Message{
				Message: "Hello, @alice.bsky.social!",
				Metadata: MessageMetadata{
					Mentions: []MessageMention{
						{
							Username: "@alice.bsky.social",
							URL:      "https://bsky.social/profile/did:plc:alice",
						},
					},
				},
			},
			mentionStyle: MentionStyleHTMLLink,
			want:         "Hello, <a href=\"https://bsky.social/profile/did:plc:alice\">@alice.bsky.social</a>!",
		},
		{
			message: Message{
				Message: "Hello, @alice.bsky.social!",
				Metadata: MessageMetadata{
					Mentions: []MessageMention{
						{
							Username: "@alice.bsky.social",
							URL:      "https://bsky.social/profile/did:plc:alice",
						},
					},
				},
			},
			mentionStyle: MentionStyleAppendURL,
			want:         "Hello, @alice.bsky.social (https://bsky.social/profile/did:plc:alice)!",
		},
		{
			message: Message{
				Message: "Hello, @alice.bsky.social!",
				Metadata: MessageMetadata{
					Mentions: []MessageMention{
						{
							Username: "@alice.bsky.social",
							URL:      "https://bsky.social/profile/did:plc:alice",
						},
					},
				},
			},
			mentionStyle: MentionStyleReplaceWithURL,
			want:         "Hello, https://bsky.social/profile/did:plc:alice!",
		},
		{
			message: Message{
				Message: "Hello, @alice.bsky.social and @bob.bsky.social!",
				Metadata: MessageMetadata{
					Mentions: []MessageMention{
						{
							Username: "@alice.bsky.social",
							URL:      "https://bsky.social/profile/did:plc:alice",
						},
					},
				},
			},
			mentionStyle: MentionStyleMarkdownLink,
			want:         "Hello, [@alice.bsky.social](https://bsky.social/profile/did:plc:alice) and @bob.bsky.social!",
		},
		{
			message: Message{
				Message: "Hello, @alice.bsky.social and @alice.bsky.social!",
				Metadata: MessageMetadata{
					Mentions: []MessageMention{
						{
							Username: "@alice.bsky.social",
							URL:      "https://bsky.social/profile/did:plc:alice",
						},
						{
							Username: "@alice.bsky.social",
							URL:      "https://bsky.social/profile/did:plc:alice",
						},
					},
				},
			},
			mentionStyle: MentionStyleMarkdownLink,
			want:         "Hello, [@alice.bsky.social](https://bsky.social/profile/did:plc:alice) and [@alice.bsky.social](https://bsky.social/profile/did:plc:alice)!",
		},
		{
			message: Message{
				Message: "Hello, @alice.bsky.social and @bob.bsky.social!",
				Metadata: MessageMetadata{
					Mentions: []MessageMention{
						{
							Username: "@alice.bsky.social",
							URL:      "https://bsky.social/profile/did:plc:alice",
						},
						{
							Username: "@bob.bsky.social",
							URL:      "https://bsky.social/profile/did:plc:bob",
						},
					},
				},
			},
			mentionStyle: MentionStyleMarkdownLink,
			want:         "Hello, [@alice.bsky.social](https://bsky.social/profile/did:plc:alice) and [@bob.bsky.social](https://bsky.social/profile/did:plc:bob)!",
		},
	}

	for _, tc := range tt {
		got, err := tc.message.GetContent(tc.mentionStyle)

		if err != nil {
			t.Errorf("Unexpected error for mention style %v: %v", tc.mentionStyle, err)
		}

		if got != tc.want {
			t.Errorf("Expected GetContent to be %v for mention style %v, but got %v", tc.want, tc.mentionStyle, got)
		}
	}
}

func TestMessageString(t *testing.T) {
	message := Message{
		ID:               "12345",
		Message:          "Hello, world!",
		SourceConnection: "test-connection",
	}
	want := "\"Hello, world!\" (ID: 12345, source: test-connection)"

	got := message.String()
	if got != want {
		t.Errorf("Expected String() to return %v, but got %v", want, got)
	}
}

package models

// MessageAllowedReplies represents who can reply to a [Message].
type MessageAllowedReplies int

const (
	// MessageAllowedRepliesEveryone indicates that everyone can reply
	MessageAllowedRepliesEveryone MessageAllowedReplies = iota
	// MessageAllowedRepliesFollowers indicates that only followers can reply
	MessageAllowedRepliesFollowers
	// MessageAllowedRepliesFollowing indicates that only accounts the user is following can reply
	MessageAllowedRepliesFollowing
	// MessageAllowedRepliesMentioned indicates that only mentioned users can reply
	MessageAllowedRepliesMentioned
	// MessageAllowedRepliesNoOne indicates that no one can reply
	MessageAllowedRepliesNoOne
)

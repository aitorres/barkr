package models

// MessageAllowedReplies represents who can reply to a [Message].
type MessageAllowedReplies int

const (
	MessageAllowedRepliesEveryone  MessageAllowedReplies = iota // everyone can reply
	MessageAllowedRepliesFollowers                              // only followers can reply
	MessageAllowedRepliesFollowing                              // only accounts the user is following can reply
	MessageAllowedRepliesMentioned                              // only mentioned users can reply
	MessageAllowedRepliesNoOne                                  // no one can reply
)

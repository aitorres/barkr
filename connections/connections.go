// Package connections implements the base and specialized [Connection] types to handle
// the integration with specific platforms, social media services, and other external [Message]
// sources.
//
// A [Connection] is responsible for managing the lifecycle of a connection to an external
// services to send and/or receive [Message]s.
//
// The package provides a base [Connection] type that can be extended to implement specific
// types for a given platform. It also provides multiple built-in, specialized [Connection] types
// for popular platforms and services.
package connections

import (
	"fmt"
	"log/slog"
	"slices"
	"strings"

	"github.com/aitorres/barkr/models"
)

// defaultConnectiongroup is the default group name used when a [Connection] is created
// without an explicit group. [Connection]s can be grouped together so they only relay
// messages to other [Connection]s in the same group.
const defaultConnectionGroup = "default"

// ConnectionMode defines the mode of operation for a [Connection].
type ConnectionMode int

const (
	// ConnectionModeRead indicates that the connection is allowed to fetch messages from
	// an external source.
	ConnectionModeRead ConnectionMode = iota
	// ConnectionModeWrite indicates that the connection is allowed to send messages to
	// an external source.
	ConnectionModeWrite
)

// Connection represents the behaviour that every connection exposes to the [Barkr] orchestrator.
type Connection interface {
	// Name returns the name of the connection.
	Name() string
	// Modes returns the modes of operation for the connection.
	Modes() []ConnectionMode
	// HasMode reports if the connection supports the given mode of operation.
	HasMode(mode ConnectionMode) bool
	// Group returns the group name of the connection, used for routing.
	Group() string
	// Read fetches and returns new (non-duplicate) messages.
	Read() []models.Message
	// Write posts the given messages to the connection's external source.
	Write(messages []models.Message) error
}

// BaseConnection is a base implementation of the shared state and behaviour of
// a [Connection]. Concrete [Connection] types can embed this struct to inherit
// its functionality and override specific methods as needed, mainly fetch and post.
type BaseConnection struct {
	name                 string
	modes                []ConnectionMode
	group                string
	supportedMessageType models.MessageType
	postedMessageIDs     *boundedIDSet
}

// Option customizes a [BaseConnection] during its initialization.
type Option func(*BaseConnection)

// WithSupportedMessageType sets the supported message type for the [BaseConnection].
func WithSupportedMessageType(messageType models.MessageType) Option {
	return func(c *BaseConnection) {
		c.supportedMessageType = messageType
	}
}

// NewBaseConnection validates and creates a new [BaseConnection], with the given name, group and at least
// one provided mode. Optional behaviour can be provided via [Option]s.
func NewBaseConnection(name string, modes []ConnectionMode, group string, options ...Option) (*BaseConnection, error) {
	name = strings.TrimSpace(name)
	if len(name) == 0 {
		return nil, fmt.Errorf("new connection must have a non-empty name")
	}

	if len(modes) == 0 {
		return nil, fmt.Errorf("at least one mode must be provided for connection %s", name)
	}

	seen := make(map[ConnectionMode]struct{}, len(modes))
	for _, mode := range modes {
		if _, dup := seen[mode]; dup {
			return nil, fmt.Errorf("duplicate modes are not allowed for connection %s", name)
		}

		seen[mode] = struct{}{}
	}

	if group == "" {
		group = defaultConnectionGroup
	}

	conn := &BaseConnection{
		name:                 name,
		modes:                slices.Clone(modes),
		group:                group,
		supportedMessageType: models.MessageTypeTextOnly, // concrete types may override
		postedMessageIDs:     newBoundedIDSet(postedMessageIDsMax),
	}

	for _, option := range options {
		option(conn)
	}

	return conn, nil
}

// Name returns the name of the connection.
func (c *BaseConnection) Name() string {
	return c.name
}

// Modes returns the modes of operation for the connection.
func (c *BaseConnection) Modes() []ConnectionMode {
	return c.modes
}

// HasMode reports if the connection supports the given mode of operation.
func (c *BaseConnection) HasMode(mode ConnectionMode) bool {
	return slices.Contains(c.modes, mode)
}

// Group returns the group name of the connection, used for routing.
func (c *BaseConnection) Group() string {
	return c.group
}

// Read is the default read behaviour for a [BaseConnection] that does not read.
// Returns no messages. Concrete [Connection] types that support reading should
// override this method and implement their own behaviour.
func (c *BaseConnection) Read() []models.Message {
	return nil
}

// Write is the default write behaviour for a [BaseConnection] that does not write.
// Returns no error. Concrete [Connection] types that support writing should override
// this method and implement their own behaviour.
func (c *BaseConnection) Write(messages []models.Message) error {
	return nil
}

// HasPostedID reports if the given message ID has already been posted by this connection.
func (c *BaseConnection) HasPostedID(id string) bool {
	return c.postedMessageIDs.Contains(id)
}

// AddPostedIDs adds the given message IDs to the set of posted message IDs for this connection.
func (c *BaseConnection) AddPostedIDs(ids []string) {
	c.postedMessageIDs.Update(ids)
}

// ApplyRead implements the base read behaviour for a [BaseConnection] that supports reading. It calls the provided fetch function to retrieve messages, filters out duplicates, and returns the new messages. Concrete [Connection] types that support reading should call this method from their own Read implementation.
func (c *BaseConnection) ApplyRead(fetch func() ([]models.Message, error)) []models.Message {
	if !c.HasMode(ConnectionModeRead) {
		return nil
	}

	messages, err := fetch()
	if err != nil {
		slog.Error("error fetching messages from connection", "connection", c.name, "error", err)
		return []models.Message{}
	}

	newMessages := make([]models.Message, 0, len(messages))
	for _, message := range messages {
		if c.postedMessageIDs.Contains(message.ID) {
			slog.Info("skipping duplicate message", "connection", c.name, "message_id", message.ID)
			continue
		}

		newMessages = append(newMessages, message)
	}

	return newMessages
}

// ApplyWrite implements the base write behaviour for a [BaseConnection] that supports writing. It filters the provided messages to only include those with supported content types, calls the provided post function to send them, and updates the posted message IDs. Concrete [Connection] types that support writing should call this method from their own Write implementation.
func (c *BaseConnection) ApplyWrite(messages []models.Message, post func([]models.Message) ([]string, error)) error {
	if !c.HasMode(ConnectionModeWrite) {
		return nil
	}

	validMessages := make([]models.Message, 0, len(messages))
	for _, message := range messages {
		if message.HasContent(c.supportedMessageType) {
			validMessages = append(validMessages, message)
		}
	}

	if len(validMessages) == 0 {
		slog.Info("no valid messages to post", "connection", c.name)
		return nil
	}

	if len(validMessages) < len(messages) {
		slog.Info("some messages were skipped due to unsupported content type", "connection", c.name, "discarded", len(messages)-len(validMessages))
	}

	postedIDs, err := post(validMessages)
	if err != nil {
		slog.Error("error posting messages to connection", "connection", c.name, "error", err)
		return fmt.Errorf("error posting messages to %s: %w", c.name, err)
	}

	c.AddPostedIDs(postedIDs)
	return nil
}

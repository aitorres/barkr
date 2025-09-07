# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.10.8] - 2025-09-07

### Changed

- Bluesky connection: added exponential back-off logic when fetching new posts, to account for transient network issues.
- Increased unit test coverage
- Minor dependency updates and other refactors

## [0.10.7] - 2025-08-27

### Changed

- Increased timeout for Bluesky-related network requests to 15 seconds, to prevent timeouts on slow connections or when uploading blobs.

## [0.10.6] - 2025-08-05

### Fixed

- Addressed a bug on the Bluesky connection where retrying to post a message after certain kinds of failures would post correctly, but break the rest of the writing thread, preventing further messages from being posted. The root cause is an unbound local variable in the retry logic that was not being assigned correctly.

### Changed

- Minor dependency updates

## [0.10.5] - 2025-08-04

### Added

- Bluesky connection: added support to set who can reply to a post (through thread gates) when posting a message, with the `allowed_replies` parameter.
  - This is an optional parameter, and defaults to `None`, which means that anyone can reply to the post (default behavior before this update).
  - If set, it will be used to set the thread gate for the post, allowing only users who meet the criteria to reply.

### Changed

- Implemented exponential back-off retry logic when retrieving a recently posted message's details on Bluesky.
- Minor dependency updates
- Minor tweaks to error messages and logging statements to support debugging flows.

## [0.10.4] - 2025-07-22

### Changed

- Minor dependency updates

### Fixed

- Catch the right exception on Mastodon connections when there's timeouts and network issues
- Prevent the RSS tests from getting stuck

## [0.10.3] - 2025-06-29

### Changed

- Minor dependency updates
- Minor test coverage updates
- Improved error message on Bluesky errors
- Early return when trying to compress an image that's already within the maximum size allowed by Bluesky, to avoid unnecessary processing.

### Fixed

- Handle invalid MIME types when posting images to Bluesky
- Bluesky connection: handle Bluesky internal server errors gracefully when attempting to upload an embed image for a post.

## [0.10.2] = 2025-05-31

### Added

- Bluesky connection: added a new, optional parameter (off by default) to allow Barkr to compress images that are being posted to Bluesky, if their size exceeds the maximum allowed by the platform.
  - Initially this is only done on embed blobs (e.g. for URL previews), as Barkr doesn't yet support posting images as embeds.
  - This is useful to prevent Bluesky from rejecting images that are too large, and to avoid having to manually resize images before posting them.
  - The default behavior is to not compress images, to keep the current behavior. Images too large will still be rejected by Bluesky, resulting in posts without images.

### Changed

- Minor performance improvements to the Bluesky connection
- Minor dependency updates

## [0.10.1] - 2025-05-21

### Changed

- Minor dependency updates.

### Fixed

- Bluesky connection: fixed an issue where URL facets were not being correctly added to a post with a URL when a request to get embed metadata for the URL failed, even though the facet doesn't need said metadata.

## [0.10.0] - 2025-05-11

aka the media update!

### Added

- Implemented support for storing media (images, videos) in the `Message` model, with descriptive or alt text.
  - Connections can decide whether to support text-only messages or text+media messages.
  - Empty message filter now considers supported message type when deciding if a message is empty (e.g. a message with only media is not empty if the connection supports media).
- Bluesky connection: added support for reading media from messages.
- Mastodon connection: added support for reading media from messages, and adding media to messages.

### Changed

- Minor dependency updates
- Minor tweaks to Github Actions pipeline

## [0.9.8] - 2025-05-06

### Added

- Mastodon connection: added support for reading and writing messages with `visibility` metadata: public, unlisted, private, direct.
  - Note that private and direct messages will not be published to the other connections, to prevent accidental leaks of private messages.

### Changed

- Minor dependency updates
- Minor tweaks to the `Message` model

## [0.9.7] - 2025-04-20

### Added

- Mastodon connection: added support for reading and writing messages with `label` metadata: content warnings, spoiler tags, etc.

### Changed

- Minor dependency updates
- Tweaks to logging statements
- Increased unit test coverage

## [0.9.6] - 2025-04-08

### Fixed

- Bluesky connection: properly handle errors when uploading embed images for posted links.

### Changed

- Minor dependency updates

## [0.9.5] - 2025-04-07

### Added

- More unit test coverage for utility and helper functions.

### Fixed

- Bluesky connection: fixed an issue where the writing thread would stop working after an unhandled timeout exception.

## [0.9.4] - 2025-04-06

### Fixed

- Bluesky connection: fixed an issue where the writing thread would stop working if a message is posted and the details are not retrieved successfully.

## [0.9.3] - 2025-04-03

### Added

- Added support for `language` metadata on the `Message` model, which is currently supported by the Mastodon and Bluesky connections, on read and write operations.

### Changed

- Connections will now raise an error if duplicate modes are being passed on instantiation.
- Minor dependency updates

## [0.9.2] - 2025-03-30

### Fixed

- Twitter connection: fixed an issue retrieving the ID of a posted tweet
- Telegram connection: fixed an issue where the message content was not properly being passed to the bot when sending a message

## [0.9.1] - 2025-03-30

### Fixed

- When posting messages via `Barkr.write_message`, each connection will have its own error-catching logic, so that if one connection fails, the others will still be able to post.

## [0.9.0] - 2025-03-30

### Added

- Implemented a new connection class for ActivityBot, a Mastodon bot implementation, with write support.

### Changed

- Minor dependency updates

## [0.8.11] - 2025-03-22

### Fixed

- Barkr will not attempt to publish a message whose length exceeds a channel's known maximum (Bluesky, Twitter)

### Changed

- Removed unneeded / empty method implementations from non-read/write connections
- Increased test coverage for Mastodon connection
- Minor dependency updates

## [0.8.10] - 2025-03-19

### Fixed

- When posting on Bluesky, an exception trying to retrieve an image thumbnail for a URL embed will no longer cause the whole writing thread to stop working.
- When posting on Bluesky, if the message contains accented characters (e.g. the _é_ in "Andrés") and a URL, the URL facet is now being set to the right substring.

### Changed

- Minor refactors
- Adding small tests for uncovered cases

## [0.8.9] - 2025-03-18

### Fixed

- Bluesky connection can now recover when attempting to post a message with an embed whose preview image is too large

### Changed

- Minor dependency updates
- Increased test coverage for RSS and Telegram connections
- `Message` model can now be imported from `barkr.models` (`barkr.models.message` is still supported to keep backwards compatibility)
- Documented `write_message` method on [`README.md`](./README.md) sample code.

## [0.8.8] - 2025-03-16

### Added

- Add support for embedding URLs (with URL preview and clickable URLs) when creating posts in Bluesky
- Unit tests for MastodonConnection's retry logic

### Changed

- Minor dependency updates

## [0.8.7] - 2025-03-15

### Fixed

- RSS connections will no longer attempt to publish all old entries on connection init.

### Changed

- Minor refactor of the Bluesky connection to handle post embeds.
- Minor dependency updates.

## [0.8.6] - 2025-03-09

### Fixed

- Bluesky posts that contain a single link and multiple words are now being reconstructed successfully.

## [0.8.5] - 2025-03-08

### Fixed

- Connections no longer attempt to publish a post with an empty message
- Bluesky posts that contain a single link (which is trimmed when stored on  `atproto` and stored as an embed) are now being reconstructed successfully.

### Changed

- Minor dependency updates

## [0.8.4] - 2025-03-01

### Fixed

- Gracefully handles server errors when trying to read new messages from connections

### Changed

- Minor dependency updates

## [0.8.3] - 2025-02-25

### Added

- New option on the `Barkr` class to set up a "write rate limit", optional and defaults to `None`. If set, `barkr` will only write the specified amount of messages per each polling period, as a safeguard to prevent publishing too many posts in a limited time.

### Changed

- Minor refactor and more validations added to the `Barkr` class

## [0.8.2] - 2025-02-23

### Added

- New method on the `Barkr` class to enable posting a message to the existing Connections on a non-blocking way, i.e. not requiring the read-write loop to be started.

### Fixed

- Introduce artificial delay after posting on Bluesky to prevent an error when querying for the new post's indexed datetime

### Changed

- Modified minimum supported Python version from 3.9 to 3.9.2

## [0.8.1] - 2025-02-23

### Added

- Support for Python 3.9 and 3.10 (all the way to 3.13)

### Changed

- Minor dependency updates

## [0.8.0] - 2025-02-22

### Added

- Implement an initial, read-only connection class for RSS feeds.

### Changed

- Minor dependency updates

## [0.7.0] - 2025-02-15

### Added

- Implement an initial, write-only connection class for Discord.

### Changed

- All connection classes and enums are now exported from `barkr.connections` in addition to their specific submodules for ease of use (e.g. to use `from barkr.connections import MastodonConnection, DiscordConnection` instead of requiring two different import lines)
- Updated sample code in the [README](./README.md) to showcase all existing connections.

### Fixed

- Minor Python type annotation non-breaking tweaks.

## [0.6.1] - 2025-02-15

### Added

- New Github Actions pipeline to publish new releases directly to PyPI from a clean state, to solve the issue of releases having unneeded, development or test files inside by accident.

### Fixed

- Sample code in the [README](./README.md) file had typos when importing `barkr` modules.

### Changed

- Updated the `mastodon` package to its latest release
- Other minor dependency updates

## [0.6.0] - 2025-02-04

### Added

- Implemented Telegram connection with write support to a chat or channel through a Telegram bot

### Changed

- Minor dependency updates

## [0.5.1] - 2025-01-26

### Changed

- Minor dependency updates

### Fixed

- Fixed an issue in which posted messages were not being tracked successfully on Bluesky, leading to duplicates
- Cleaner filtering of reblogs and replies for Bluesky and Mastodon
- Cleaner logging statements

## [0.5.0] - 2025-01-19

### Added

- Implemented Bluesky connection with read and write support

### Changed

- Minor dependency updates

### Fixed

- Addressed a bug that caused messages to constantly push in a loop due to not keeping track of previously seen messages properly. New unit tests added to prevent this issue from arising again in the future.

## [0.4.0] - 2025-01-11

### Added

- Implemented Twitter connection with support for write-only mode

### Changed

- Dependency updates

## [0.3.0] - 2024-09-25

### Changed

- Dependency updates

### Removed

- Cohost support has been removed since [the platform is now on read-only mode and is being sunsetted](https://cohost.org/staff/post/7611443-cohost-to-shut-down).

## [0.2.1] - 2023-09-27

### Changed

- Test coverage for Cohost Connection increased

## [0.2.0] - 2023-09-26

### Added

- Initial implementation of a Cohost connection. This is the first version to officially support distinct channels!

### Changed

- Test coverage for Mastodon Connection increased

## [0.1.2] - 2023-09-09

### Added

- Library is now marked as a typed package

### Fixed

- Messages retrieved from Mastodon will no longer include HTML tags

## [0.1.1] - 2023-09-09

### Added

- Messages are now wrapped in a custom wrapper class to allow connections to provide with optional metadata

### Fixed

- Connections no longer will attempt to queue / distribute a fetched message that they actually posted before (i.e. only messages posted outside of each connection will be queued)
- Use most recent Mastodon status to retrieve next `min_id`

## [0.1.0] - 2023-09-09

Initial release!

### Added

- Initial implementation of the **Barkr** social media cross-posting tool.
- Implementation of a Mastodon connection
- Basic documentation for the project

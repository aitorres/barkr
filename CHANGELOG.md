# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

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

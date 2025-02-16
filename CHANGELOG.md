
# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

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

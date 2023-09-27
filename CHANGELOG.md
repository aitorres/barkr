
# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

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

# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.9] - Unreleased
### Fixed
- `--html` output now HTML-escapes the domain, server address, tags and record text, preventing markup in DNS records (e.g. TXT) from being injected into the report.

### Changed
- Record-to-string conversion is now handled by a single `_record_text` helper instead of being repeated in four places.

### Tests
- Added tests for `--no-color` output and malformed YAML input.
- Added tests for `--html` output and HTML escaping, server list schema validation (non-list and non-mapping entries), empty DNS answers, and record text conversion.
- Tests now import the package from the local `src/` directory instead of any installed copy.

## [0.0.8] - 2026-05-08
### Added
- `--custom_list` now accepts an `http://` or `https://` URL in addition to a local file path, allowing a DNS server list to be loaded remotely. Remote lists are fetched with a 10-second timeout and a 1 MB size limit. All entries (local and remote) are validated to contain a well-formed IP address in the `ipv4` field.
- Exit code `3` when no DNS servers match the specified `--tags` or `--owner` filters.
- Exit code `5` when `--expected` is set and at least one server returned an unexpected answer.
- Exit code `15` for HTTP error responses (4xx/5xx) when fetching a remote server list.
- Exit code `16` for server list schema validation failures (missing or invalid `ipv4` field).

## [0.0.7] - 2026-04-15
### Fixed
- `--html` parameter in pip package

## [0.0.6] - 2026-04-15
### Added
- `--html` flag to output results as a self-contained HTML page to STDOUT

### Changed
- `--country` replaced by `--tags`; servers now carry a list of tags instead of a single country
- When multiple tags are specified, only servers that have all of them are selected

### Removed
- `--country` flag (superseded by `--tags`)

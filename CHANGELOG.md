# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.6] - 2026-04-15
### Added
- `--html` flag to output results as a self-contained HTML page to STDOUT

### Changed
- `--country` replaced by `--tags`; servers now carry a list of tags instead of a single country
- When multiple tags are specified, only servers that have all of them are selected

### Removed
- `--country` flag (superseded by `--tags`)

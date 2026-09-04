# Changelog

All notable changes to Story Companion are documented here.

## [0.2.0] — 2026-09-04

### Added

- Responsive web interface served directly by FastAPI
- Original offline sample story and provenance-validated example result
- Secret-free runtime capability endpoint and browser security headers
- Release screenshots and public-facing product documentation

### Changed

- Character profiles are now usable through the browser as well as the API
- Local pytest runs use a repository-local temporary directory on Windows
- Package data now includes all web and demo assets

## [0.1.0] — 2026-08-22

### Added

- UTF-8 TXT upload and deterministic chapter detection
- Inclusive chapter spoiler boundary and spoiler-safe context
- Evidence schemas and deterministic provenance validation
- Provider-neutral character extraction with an optional OpenAI adapter
- Docker, Makefile, pytest, Ruff, and GitHub Actions foundation

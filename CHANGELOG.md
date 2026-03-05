# Changelog

All notable changes to the Home Assistant Notes Addon are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.4] - 2026-03-04

### Fixed
- **Import broken** — form field name mismatch between `index.html` (`zip_file`) and
  `import_note()` route (`file`) meant import never worked. Route now reads `zip_file`.
- **Import now actually extracts notes** — previously saved the raw zip file as-is to the
  notes directory. Now opens the zip in memory and extracts `.txt` files from it.
- **Path traversal in edit/delete routes** — `filename` from the URL was passed directly to
  `os.path.join()` with no sanitisation. Now hardened with `os.path.basename()` and
  validation checks on all affected routes.
- **Zip-slip protection on import** — zip entries with path separators or `..` in their
  names are now rejected.
- **Notes directory created once at startup** instead of on every request.
- **Filename sanitisation on note creation** — special characters, very long titles,
  and reserved names are now normalised to safe alphanumeric filenames.
- **bashio config reading restored** in `run.sh` — the `homeassistant_config_notes_path`
  configuration option was non-functional due to commented-out bashio calls; now restored.

### Changed
- Production server switched from Flask development server (`app.run()`) to
  **gunicorn** (2 workers). More stable under load; suppresses Flask dev-mode warnings.
- Upload size capped at **10 MB** (`MAX_CONTENT_LENGTH`).
- Import now validates that the uploaded file has a `.zip` extension before processing.
- Import only extracts `.txt` files from the zip; all other file types are silently skipped.

### Removed
- Exhaustive debug logging removed from `ReverseProxied` middleware (was logging every
  HTTP header and environ key on every request, including auth tokens).
- `log_request_info_after_middleware` before_request handler removed (logged full request
  details on every request in production).

## [1.0.3] - 2025

### Added
- Export all notes as a zip file.
- Import notes from a zip file (UI only — functionality completed in 1.0.4).

## [1.0.2] - 2025

### Added
- Edit existing notes.
- Delete notes with confirmation dialog.

## [1.0.1] - 2025

### Added
- Persistent storage via user-configurable `homeassistant_config_notes_path`.
- HA Ingress support via `ReverseProxied` WSGI middleware.

## [1.0.0] - 2025

### Added
- Initial release.
- Create and view notes via Home Assistant sidebar.
- Notes stored as `.txt` files in `/config/notes`.

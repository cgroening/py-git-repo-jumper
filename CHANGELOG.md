# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

–

### Changed

–

### Fixed

–

## [0.1.2] – 2026-03-17

### Added

- Example mode: when `example-mode: true` is set in the config, the repository selector displays example git info (`current-branch-name`, `status` and `github-repo-name`) defined per repository via `example-git-info` instead of fetching live data – useful for demos and screenshots

### Changed

- Adjust column stretch priorities of the repository selector so that available extra width is distributed to the status column first
- Simplifiy application header

## [0.1.1] – 2026-03-16

### Fixed

- Clear fuzzy finder output (answered state) from terminal after a repository is selected

## [0.1.0] – 2026-03-15

### Added

- Initial Release

[Unreleased]: https://github.com/cgroening/py-git-repo-jumper/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/cgroening/py-git-repo-jumper/releases/tag/v0.1.2
[0.1.1]: https://github.com/cgroening/py-git-repo-jumper/releases/tag/v0.1.1
[0.1.0]: https://github.com/cgroening/py-git-repo-jumper/releases/tag/v0.1.0

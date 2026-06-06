# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

### Added

- `doc_theme` now supports a `logo` (inlined SVG) and `website` attribute.
  Logos are embedded directly into the cover page so rendered HTML remains a
  single self-contained file; the website is shown and linked on the cover.
- Company theme (`//company:company_theme`) ships the Farakov logo and website.

## [0.0.0]

### Added

- Initial implementation of the documentation ruleset.
- `doc_theme` rule: declares reusable typography, colors, layout policy, and
  bundled assets; normalizes to a stable JSON config.
- `doc_section` rule: declares ordered, reusable Markdown sections.
- `doc_template` rule: bundles a default theme with package layout policy
  (cover page, table of contents).
- `documentation_package` rule: composes sections, applies a theme/template,
  and renders a single themed HTML document plus a JSON manifest.
- Hermetic, standard-library-only Python renderer supporting headings,
  emphasis, inline/fenced code, lists, blockquotes, links, images, horizontal
  rules, and tables; emits an auto-generated table of contents and cover page.
- `tests/` workspace consuming the ruleset via `local_path_override` with an
  end-to-end security-assessment example and HTML/manifest assertion tests.

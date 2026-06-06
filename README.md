# rules_farakov_documentation

**Status:** Early prototype. Not production-ready.

A domain-agnostic Bazel ruleset to generate **complete, themed, and templated documentation packages** for multiple applications, including cybersecurity assessments, contracts, project/product documentation, and more.

---

## Overview

`rules_farakov_documentation` provides:

- **Bazel rules and macros** that standardize how documentation is defined, themed, and built.
- **Support for multiple output formats**, including PDFs, Markdown, and optionally HTML.
- **A configurable theming system** for typography, color schemes, cover pages, headers/footers, and section layouts.
- **Extensible templates** so different applications can define rich, verbose, and structured documentation with minimal setup.

The primary goal is to make it **trivial for downstream Bazel monorepos** to declare documentation in a **declarative, reproducible, and standardized way**.

---

## Key Concepts

### Documentation Targets

A “documentation target” is a Bazel target that generates a full documentation artifact. Each target includes:

- `sources`: Markdown or reStructuredText files
- `metadata`: YAML/JSON defining title, authors, revision, version, etc.
- `theme`: Optional, overrides default styling
- `outputs`: PDF, HTML, or other formats

### Rules Provided

| Rule | Purpose |
|------|---------|
| `documentation_package` | Generates a full PDF/HTML documentation package from Markdown and metadata. |
| `doc_section` | Defines a logical section of documentation; can be reused across packages. |
| `doc_template` | Predefined templates that include cover page, table of contents, and standardized layouts. |
| `doc_theme` | A reusable theme specification; downstream projects can override fonts, colors, and styles. |

### Configurable Parameters

- **Environment:** Output directories, target platform, versioning.
- **Metadata:** Authors, titles, dates, revision numbers.
- **Assets:** Logos, cover images, references.
- **Markdown processing options:** Support for diagrams, tables, cross-references.
- **Build options:** PDF engine (e.g., LaTeX), HTML output options, incremental builds.

---

## Getting Started

1. **Add the ruleset to your `MODULE.bazel` (Bzlmod):**

```starlark
bazel_dep(name = "rules_farakov_documentation", version = "<VERSION>")
```

   Release tags publish a consumer snippet with the exact `archive_override`
   block (URL + integrity hash) to paste while the module is pre-registry.

2. **Declare a theme, sections, and a package:**

```starlark
load(
    "@rules_farakov_documentation//documentation:defs.bzl",
    "doc_section",
    "doc_template",
    "doc_theme",
    "documentation_package",
)

doc_theme(
    name = "corporate_theme",
    theme_name = "corporate",
    colors = {"primary": "#0b3d91"},
    max_width = "900px",
)

doc_template(
    name = "assessment_template",
    theme = ":corporate_theme",
)

doc_section(
    name = "summary",
    title = "Executive Summary",
    srcs = ["content/summary.md"],
)

documentation_package(
    name = "security_assessment",
    title = "Example Corp Security Assessment",
    authors = ["A. Tester"],
    metadata = {
        "subtitle": "Web Platform Penetration Test",
        "version": "1.0",
        "date": "2026-02-15",
    },
    sections = [":summary"],
    template = ":assessment_template",
)
```

3. **Build it:**

```sh
bazel build //path/to:security_assessment
```

   This produces `security_assessment.html` (a single themed, self-contained
   document) and `security_assessment.manifest.json` (a build manifest).

---

## Rendering

The renderer is a hermetic, standard-library-only Python tool that runs under
Bazel's pinned Python toolchain — no system dependencies, fully reproducible.
It supports headings, emphasis, inline and fenced code, lists, blockquotes,
links, images, horizontal rules, and tables, and auto-generates a cover page
and table of contents based on the theme/template layout policy.

When both a `theme` and a `template` are supplied to a package, the explicit
`theme` takes precedence over the template's bundled theme.

---

## Development

The ruleset and its consumer-facing tests live in two Bazel modules:

```sh
# Build the ruleset itself.
bazel build //...

# Build and test the example consumer workspace.
cd tests
bazel build //...
bazel test //...
```
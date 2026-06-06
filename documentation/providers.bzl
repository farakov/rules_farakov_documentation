"""Provider definitions for rules_farakov_documentation.

Providers are the typed contract passed between the documentation rules.
Keeping them in one place lets the rule implementations stay small and lets
downstream rules depend on a stable surface.
"""

DocThemeInfo = provider(
    doc = "A reusable theme: typography, colors, and layout knobs plus assets.",
    fields = {
        "name": "str: human-readable theme name.",
        "config": "File: a normalized JSON file describing the theme.",
        "assets": "depset[File]: theme assets (fonts, logos, css) to bundle.",
        "logo": "File or None: an SVG logo inlined onto the cover page.",
    },
)

DocSectionInfo = provider(
    doc = "A reusable logical section of documentation.",
    fields = {
        "name": "str: section identifier, used for ordering and anchors.",
        "title": "str: human-readable section title.",
        "sources": "depset[File]: ordered Markdown source files for the section.",
        "assets": "depset[File]: images/files referenced by the section.",
    },
)

DocTemplateInfo = provider(
    doc = "A package template: cover page, table-of-contents and layout policy.",
    fields = {
        "name": "str: template identifier.",
        "config": "File: a normalized JSON file describing template options.",
        "theme": "DocThemeInfo: the default theme bundled with this template.",
    },
)

DocPackageInfo = provider(
    doc = "The output of a fully rendered documentation package.",
    fields = {
        "name": "str: package identifier.",
        "html": "File: the rendered single-file HTML document.",
        "manifest": "File: a JSON manifest describing the build inputs/outputs.",
        "outputs": "depset[File]: all files that make up the package.",
    },
)

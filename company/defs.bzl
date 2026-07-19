"""Company-standard documentation building blocks.

This module defines:

  * `company_theme`        - the standard corporate visual theme target name.
  * `company_template`     - the standard template (theme + layout policy).
  * `responsible_disclosure` - a macro that stamps out a complete responsible
    disclosure document from the standard boilerplate plus caller-supplied
    sections and metadata.

Consumers in this repo (or downstream, once published) should prefer the
`responsible_disclosure` macro over wiring rules by hand.
"""

load(
    "@rules_coen_applied_docs//documentation:defs.bzl",
    "documentation_package",
)

# Labels for the shared theme/template defined in //company:BUILD.bazel.
COMPANY_THEME = "//company:company_theme"
COMPANY_TEMPLATE = "//company:disclosure_template"

# The ordered set of standard disclosure boilerplate sections. These are
# defined as doc_section targets in //company:BUILD.bazel.
_STANDARD_DISCLOSURE_SECTIONS = [
    "//company:sec_policy",
    "//company:sec_scope",
    "//company:sec_reporting",
    "//company:sec_severity",
    "//company:sec_safe_harbor",
]

def responsible_disclosure(
        name,
        title = "Responsible Disclosure Policy",
        org_name = None,
        metadata = None,
        extra_sections = None,
        prepend_sections = None,
        template = COMPANY_TEMPLATE,
        **kwargs):
    """Generate a complete responsible-disclosure document.

    Args:
      name: target name for the resulting documentation_package.
      title: document title shown on the cover.
      org_name: convenience metadata field recorded as metadata['org_name'].
      metadata: dict of additional metadata (subtitle, version, date, ...).
        Merged on top of sensible defaults.
      extra_sections: optional list of doc_section labels appended after the
        standard boilerplate (e.g. program-specific findings or appendices).
      prepend_sections: optional list of doc_section labels inserted before the
        standard boilerplate (e.g. a custom executive note).
      template: the template to apply. Defaults to the company template.
      **kwargs: forwarded to documentation_package (e.g. visibility, authors).
    """
    md = {
        "subtitle": "Coordinated Vulnerability Disclosure",
        "language": "en",
    }
    if org_name:
        md["org_name"] = org_name
    if metadata:
        md.update(metadata)

    sections = []
    sections.extend(prepend_sections or [])
    sections.extend(_STANDARD_DISCLOSURE_SECTIONS)
    sections.extend(extra_sections or [])

    documentation_package(
        name = name,
        title = title,
        metadata = md,
        sections = sections,
        template = template,
        **kwargs
    )

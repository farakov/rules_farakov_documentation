"""Public API for rules_coen_applied_docs.

Downstream consumers should load rules from this file only:

    load("@rules_coen_applied_docs//documentation:defs.bzl",
         "doc_theme", "doc_section", "doc_template", "documentation_package")

Everything else under //documentation is an implementation detail and may
change without notice.
"""

load("//documentation:package.bzl", _documentation_package = "documentation_package")
load("//documentation:providers.bzl", _DocPackageInfo = "DocPackageInfo", _DocSectionInfo = "DocSectionInfo", _DocTemplateInfo = "DocTemplateInfo", _DocThemeInfo = "DocThemeInfo")
load("//documentation:section.bzl", _doc_section = "doc_section")
load("//documentation:template.bzl", _doc_template = "doc_template")
load("//documentation:theme.bzl", _doc_theme = "doc_theme")

# Rules.
doc_theme = _doc_theme
doc_section = _doc_section
doc_template = _doc_template
documentation_package = _documentation_package

# Providers (for advanced consumers writing their own rules).
DocThemeInfo = _DocThemeInfo
DocSectionInfo = _DocSectionInfo
DocTemplateInfo = _DocTemplateInfo
DocPackageInfo = _DocPackageInfo

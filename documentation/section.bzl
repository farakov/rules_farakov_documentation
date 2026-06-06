"""The `doc_section` rule.

A section is an ordered, reusable bundle of Markdown sources plus any assets
they reference. Sections are composed into packages, and may be shared across
many packages.
"""

load("//documentation:providers.bzl", "DocSectionInfo")

def _doc_section_impl(ctx):
    if not ctx.files.srcs:
        fail("doc_section '%s' must declare at least one source file in srcs." % ctx.label.name)

    sources = depset(ctx.files.srcs, order = "preorder")
    assets = depset(ctx.files.assets)
    return [
        DefaultInfo(files = depset(transitive = [sources, assets])),
        DocSectionInfo(
            name = ctx.label.name,
            title = ctx.attr.title,
            sources = sources,
            assets = assets,
        ),
    ]

doc_section = rule(
    implementation = _doc_section_impl,
    doc = "Declares a reusable logical section of documentation.",
    attrs = {
        "title": attr.string(
            doc = "Optional heading rendered before the section's content.",
        ),
        "srcs": attr.label_list(
            allow_files = [".md", ".markdown"],
            mandatory = True,
            doc = "Ordered Markdown source files. Order is preserved in output.",
        ),
        "assets": attr.label_list(
            allow_files = True,
            doc = "Images or other files referenced by the section.",
        ),
    },
)

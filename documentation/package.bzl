"""The `documentation_package` rule.

This is the primary, consumer-facing rule. It composes one or more sections,
applies a theme and/or template, and runs the hermetic renderer to produce a
single themed HTML document plus a JSON manifest.
"""

load(
    "//documentation:providers.bzl",
    "DocPackageInfo",
    "DocSectionInfo",
    "DocTemplateInfo",
    "DocThemeInfo",
)

def _doc_package_impl(ctx):
    if not ctx.attr.sections:
        fail("documentation_package '%s' must list at least one section." % ctx.label.name)

    # Resolve theme: explicit `theme` wins, else the template's bundled theme.
    theme_info = None
    template_info = None
    if ctx.attr.template:
        template_info = ctx.attr.template[DocTemplateInfo]
        theme_info = template_info.theme
    if ctx.attr.theme:
        theme_info = ctx.attr.theme[DocThemeInfo]

    # Gather section data and inputs.
    section_entries = []
    transitive_inputs = []
    for target in ctx.attr.sections:
        info = target[DocSectionInfo]
        sources = info.sources.to_list()
        section_entries.append({
            "title": info.title,
            "sources": [f.path for f in sources],
        })
        transitive_inputs.append(info.sources)
        transitive_inputs.append(info.assets)

    metadata = dict(ctx.attr.metadata)
    if ctx.attr.title and "title" not in metadata:
        metadata["title"] = ctx.attr.title
    if ctx.attr.authors and "authors" not in metadata:
        metadata["authors"] = ctx.attr.authors

    request = {
        "name": ctx.label.name,
        "metadata": metadata,
        "sections": section_entries,
    }

    request_file = ctx.actions.declare_file(ctx.label.name + ".request.json")
    ctx.actions.write(
        output = request_file,
        content = json.encode_indent(request, indent = "  "),
    )

    html_out = ctx.actions.declare_file(ctx.label.name + ".html")
    manifest_out = ctx.actions.declare_file(ctx.label.name + ".manifest.json")

    args = ctx.actions.args()
    args.add("--request", request_file)
    args.add("--html-out", html_out)
    args.add("--manifest-out", manifest_out)

    direct_inputs = [request_file]
    if theme_info:
        args.add("--theme", theme_info.config)
        direct_inputs.append(theme_info.config)
        transitive_inputs.append(theme_info.assets)
    if template_info:
        args.add("--template", template_info.config)
        direct_inputs.append(template_info.config)

    inputs = depset(direct_inputs, transitive = transitive_inputs)

    ctx.actions.run(
        executable = ctx.executable._renderer,
        arguments = [args],
        inputs = inputs,
        outputs = [html_out, manifest_out],
        mnemonic = "RenderDocs",
        progress_message = "Rendering documentation package %s" % ctx.label,
    )

    outputs = depset([html_out, manifest_out])
    return [
        DefaultInfo(files = outputs),
        DocPackageInfo(
            name = ctx.label.name,
            html = html_out,
            manifest = manifest_out,
            outputs = outputs,
        ),
    ]

documentation_package = rule(
    implementation = _doc_package_impl,
    doc = "Generates a full themed HTML documentation package with a manifest.",
    attrs = {
        "title": attr.string(
            doc = "Document title. Shorthand for metadata['title'].",
        ),
        "authors": attr.string_list(
            doc = "Document authors. Shorthand for metadata['authors'].",
        ),
        "metadata": attr.string_dict(
            doc = "Arbitrary metadata: title, subtitle, version, revision, date, language, etc.",
        ),
        "sections": attr.label_list(
            providers = [DocSectionInfo],
            mandatory = True,
            doc = "Ordered list of doc_section targets composing the package.",
        ),
        "theme": attr.label(
            providers = [DocThemeInfo],
            doc = "Optional theme. Overrides the template's theme when both are set.",
        ),
        "template": attr.label(
            providers = [DocTemplateInfo],
            doc = "Optional template providing layout policy and a default theme.",
        ),
        "_renderer": attr.label(
            default = Label("//documentation/private:render"),
            executable = True,
            cfg = "exec",
            doc = "The hermetic renderer tool.",
        ),
    },
)

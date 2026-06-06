"""The `doc_template` rule.

A template bundles a default theme together with package-layout policy such as
whether to render a cover page or a table of contents. Packages can adopt a
template to get a consistent, standardized look with minimal configuration.
"""

load("//documentation:providers.bzl", "DocTemplateInfo", "DocThemeInfo")

def _doc_template_impl(ctx):
    theme = ctx.attr.theme[DocThemeInfo]

    config = {
        "name": ctx.attr.template_name or ctx.label.name,
        "show_cover": ctx.attr.show_cover,
        "show_toc": ctx.attr.show_toc,
    }
    config_file = ctx.actions.declare_file(ctx.label.name + ".template.json")
    ctx.actions.write(
        output = config_file,
        content = json.encode_indent(config, indent = "  "),
    )

    return [
        DefaultInfo(files = depset([config_file, theme.config], transitive = [theme.assets])),
        DocTemplateInfo(
            name = config["name"],
            config = config_file,
            theme = theme,
        ),
    ]

doc_template = rule(
    implementation = _doc_template_impl,
    doc = "Declares a reusable package template (layout policy + default theme).",
    attrs = {
        "template_name": attr.string(
            doc = "Human-readable template name. Defaults to the target name.",
        ),
        "theme": attr.label(
            providers = [DocThemeInfo],
            mandatory = True,
            doc = "The default theme bundled with this template.",
        ),
        "show_cover": attr.bool(
            default = True,
            doc = "Whether packages using this template render a cover page.",
        ),
        "show_toc": attr.bool(
            default = True,
            doc = "Whether packages using this template render a table of contents.",
        ),
    },
)

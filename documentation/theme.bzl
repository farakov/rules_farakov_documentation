"""The `doc_theme` rule.

A theme captures typography, colors, layout policy and bundled assets. It is
normalized to a single JSON file at build time so consumers (templates and
packages) read a stable shape regardless of how the theme was declared.
"""

load("//documentation:providers.bzl", "DocThemeInfo")

def _doc_theme_impl(ctx):
    config = {
        "name": ctx.attr.theme_name or ctx.label.name,
        "colors": {k: v for k, v in ctx.attr.colors.items() if v},
        "typography": {k: v for k, v in ctx.attr.typography.items() if v},
        "layout": {},
    }
    if ctx.attr.max_width:
        config["layout"]["max_width"] = ctx.attr.max_width
    config["layout"]["show_toc"] = ctx.attr.show_toc
    config["layout"]["show_cover"] = ctx.attr.show_cover

    config_file = ctx.actions.declare_file(ctx.label.name + ".theme.json")
    ctx.actions.write(
        output = config_file,
        content = json.encode_indent(config, indent = "  "),
    )

    assets = depset(ctx.files.assets)
    return [
        DefaultInfo(files = depset([config_file], transitive = [assets])),
        DocThemeInfo(
            name = config["name"],
            config = config_file,
            assets = assets,
        ),
    ]

doc_theme = rule(
    implementation = _doc_theme_impl,
    doc = "Declares a reusable documentation theme.",
    attrs = {
        "theme_name": attr.string(
            doc = "Human-readable theme name. Defaults to the target name.",
        ),
        "colors": attr.string_dict(
            doc = "Color overrides: text, background, primary, muted, border, code_bg.",
        ),
        "typography": attr.string_dict(
            doc = "Typography overrides: body_font, heading_font, mono_font, base_size, line_height.",
        ),
        "max_width": attr.string(
            doc = "Content max width, e.g. '820px'.",
        ),
        "show_toc": attr.bool(
            default = True,
            doc = "Whether packages using this theme render a table of contents by default.",
        ),
        "show_cover": attr.bool(
            default = True,
            doc = "Whether packages using this theme render a cover page by default.",
        ),
        "assets": attr.label_list(
            allow_files = True,
            doc = "Theme assets (fonts, logos, css) bundled with the package.",
        ),
    },
)

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
        "branding": {},
    }
    if ctx.attr.max_width:
        config["layout"]["max_width"] = ctx.attr.max_width
    config["layout"]["show_toc"] = ctx.attr.show_toc
    config["layout"]["show_cover"] = ctx.attr.show_cover

    logo = None
    if ctx.file.logo:
        logo = ctx.file.logo
        # The renderer reads the SVG from this exec-relative path at action
        # time; the package rule adds the logo as an action input.
        config["branding"]["logo_path"] = logo.path
    if ctx.attr.website:
        config["branding"]["website"] = ctx.attr.website

    # Embedded TrueType faces for the PDF backend. The HTML output styles text
    # with the CSS `typography` font stacks, but the PDF renderer (fpdf2) needs
    # the actual font files to embed. Record each provided face in the theme
    # JSON as an exec-relative path (like the logo); it is also added as a
    # package action input below. Faces are optional; the renderer falls back to
    # a core font when none are supplied. This must run before the config is
    # serialized so the paths land in the written JSON.
    pdf_font_files = []
    pdf_fonts = {}
    for style, f in [
        ("regular", ctx.file.pdf_font_regular),
        ("bold", ctx.file.pdf_font_bold),
        ("italic", ctx.file.pdf_font_italic),
        ("bold_italic", ctx.file.pdf_font_bold_italic),
    ]:
        if f:
            pdf_fonts[style] = f.path
            pdf_font_files.append(f)
    if pdf_fonts:
        config["typography"]["pdf_fonts"] = pdf_fonts

    config_file = ctx.actions.declare_file(ctx.label.name + ".theme.json")
    ctx.actions.write(
        output = config_file,
        content = json.encode_indent(config, indent = "  "),
    )

    asset_files = list(ctx.files.assets)
    if logo:
        asset_files.append(logo)
    asset_files.extend(pdf_font_files)

    assets = depset(asset_files)
    return [
        DefaultInfo(files = depset([config_file], transitive = [assets])),
        DocThemeInfo(
            name = config["name"],
            config = config_file,
            assets = assets,
            logo = logo,
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
            doc = "Color overrides (hex): text, background, primary, muted, border, code_bg. " +
                  "A non-white background is also painted in the PDF output, so " +
                  "dark themes render correctly in both HTML and PDF.",
        ),
        "typography": attr.string_dict(
            doc = "Typography overrides: body_font, heading_font, mono_font, base_size, line_height.",
        ),
        "max_width": attr.string(
            doc = "Content max width, e.g. '820px'.",
        ),
        "logo": attr.label(
            allow_single_file = [".svg"],
            doc = "An SVG logo inlined onto the cover page of packages using this theme.",
        ),
        "pdf_font_regular": attr.label(
            allow_single_file = [".ttf"],
            doc = "Regular TrueType face embedded in the PDF output as the proportional " +
                  "body/heading font. When set, the PDF uses it instead of the built-in " +
                  "core font; the HTML output is unaffected and keeps using the " +
                  "`typography` font stacks.",
        ),
        "pdf_font_bold": attr.label(
            allow_single_file = [".ttf"],
            doc = "Bold TrueType face for the PDF output. Falls back to the regular face if unset.",
        ),
        "pdf_font_italic": attr.label(
            allow_single_file = [".ttf"],
            doc = "Italic TrueType face for the PDF output. Falls back to the regular face if unset.",
        ),
        "pdf_font_bold_italic": attr.label(
            allow_single_file = [".ttf"],
            doc = "Bold-italic TrueType face for the PDF output. Falls back to the regular face if unset.",
        ),
        "website": attr.string(
            doc = "Company/website URL shown and linked on the cover page.",
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

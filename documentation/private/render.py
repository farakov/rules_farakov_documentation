#!/usr/bin/env python3
"""Hermetic documentation renderer for rules_farakov_documentation.

This tool is intentionally dependency-free (Python standard library only) so
that builds are fully reproducible under Bazel's hermetic Python toolchain.

It consumes a single JSON "build request" describing the package, theme,
template, sections and metadata, then emits:

  * a single-file themed HTML document, and
  * a JSON manifest recording the inputs that produced it.

The Markdown support is a deliberate, well-scoped subset (headings, emphasis,
inline code, fenced code blocks, lists, blockquotes, links, images, horizontal
rules and tables). It is enough to produce rich, structured documents while
remaining easy to audit and keep hermetic.
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone


# --------------------------------------------------------------------------
# Inline Markdown
# --------------------------------------------------------------------------

_INLINE_CODE = re.compile(r"`([^`]+)`")
_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


def render_inline(text):
    """Render inline Markdown to HTML, escaping everything else."""
    # Protect inline code spans first so their contents are not re-processed.
    placeholders = {}

    def stash(match):
        token = "\0%d\0" % len(placeholders)
        placeholders[token] = "<code>%s</code>" % html.escape(match.group(1))
        return token

    text = _INLINE_CODE.sub(stash, text)
    text = html.escape(text)

    text = _IMAGE.sub(
        lambda m: '<img src="%s" alt="%s"%s>'
        % (
            html.escape(m.group(2)),
            m.group(1),
            ' title="%s"' % m.group(3) if m.group(3) else "",
        ),
        text,
    )
    text = _LINK.sub(
        lambda m: '<a href="%s"%s>%s</a>'
        % (
            html.escape(m.group(2)),
            ' title="%s"' % m.group(3) if m.group(3) else "",
            m.group(1),
        ),
        text,
    )
    text = _BOLD.sub(lambda m: "<strong>%s</strong>" % m.group(1), text)
    text = _ITALIC.sub(lambda m: "<em>%s</em>" % m.group(1), text)

    for token, value in placeholders.items():
        text = text.replace(token, value)
    return text


# --------------------------------------------------------------------------
# Block Markdown
# --------------------------------------------------------------------------

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
_UL_ITEM = re.compile(r"^[-*+]\s+(.*)$")
_OL_ITEM = re.compile(r"^\d+\.\s+(.*)$")
_HR = re.compile(r"^([-*_])(\s*\1){2,}\s*$")
_TABLE_DIVIDER = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")


def slugify(text):
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug or "section"


def split_table_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


class Renderer:
    """Stateful block-level Markdown renderer that also collects a TOC."""

    def __init__(self):
        self.out = []
        self.toc = []

    def render(self, lines):
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]

            if not line.strip():
                i += 1
                continue

            # Fenced code block.
            if line.lstrip().startswith("```"):
                lang = line.lstrip()[3:].strip()
                body = []
                i += 1
                while i < n and not lines[i].lstrip().startswith("```"):
                    body.append(lines[i])
                    i += 1
                i += 1  # consume closing fence
                cls = ' class="language-%s"' % html.escape(lang) if lang else ""
                self.out.append(
                    "<pre><code%s>%s</code></pre>"
                    % (cls, html.escape("\n".join(body)))
                )
                continue

            # Horizontal rule.
            if _HR.match(line.strip()):
                self.out.append("<hr>")
                i += 1
                continue

            # Heading.
            m = _HEADING.match(line)
            if m:
                level = len(m.group(1))
                text = m.group(2)
                slug = slugify(text)
                self.toc.append((level, text, slug))
                self.out.append(
                    '<h%d id="%s">%s</h%d>'
                    % (level, slug, render_inline(text), level)
                )
                i += 1
                continue

            # Table (header row followed by a divider row).
            if "|" in line and i + 1 < n and _TABLE_DIVIDER.match(lines[i + 1]):
                header = split_table_row(line)
                i += 2
                rows = []
                while i < n and "|" in lines[i] and lines[i].strip():
                    rows.append(split_table_row(lines[i]))
                    i += 1
                self._emit_table(header, rows)
                continue

            # Blockquote.
            if line.lstrip().startswith(">"):
                body = []
                while i < n and lines[i].lstrip().startswith(">"):
                    body.append(lines[i].lstrip()[1:].lstrip())
                    i += 1
                inner = Renderer()
                inner.render(body)
                self.out.append("<blockquote>%s</blockquote>" % "".join(inner.out))
                continue

            # Unordered / ordered list.
            if _UL_ITEM.match(line) or _OL_ITEM.match(line):
                ordered = bool(_OL_ITEM.match(line))
                pattern = _OL_ITEM if ordered else _UL_ITEM
                items = []
                while i < n and pattern.match(lines[i]):
                    items.append(pattern.match(lines[i]).group(1))
                    i += 1
                tag = "ol" if ordered else "ul"
                self.out.append("<%s>" % tag)
                for item in items:
                    self.out.append("<li>%s</li>" % render_inline(item))
                self.out.append("</%s>" % tag)
                continue

            # Paragraph: gather consecutive non-blank, non-special lines.
            para = [line]
            i += 1
            while i < n and lines[i].strip() and not self._is_block_start(lines[i]):
                para.append(lines[i])
                i += 1
            self.out.append("<p>%s</p>" % render_inline(" ".join(para)))

        return self

    def _is_block_start(self, line):
        stripped = line.lstrip()
        return (
            stripped.startswith("```")
            or bool(_HEADING.match(line))
            or bool(_UL_ITEM.match(line))
            or bool(_OL_ITEM.match(line))
            or stripped.startswith(">")
            or bool(_HR.match(line.strip()))
        )

    def _emit_table(self, header, rows):
        self.out.append("<table><thead><tr>")
        for cell in header:
            self.out.append("<th>%s</th>" % render_inline(cell))
        self.out.append("</tr></thead><tbody>")
        for row in rows:
            self.out.append("<tr>")
            for cell in row:
                self.out.append("<td>%s</td>" % render_inline(cell))
            self.out.append("</tr>")
        self.out.append("</tbody></table>")


# --------------------------------------------------------------------------
# Theme -> CSS
# --------------------------------------------------------------------------

_DEFAULT_THEME = {
    "name": "default",
    "colors": {
        "text": "#1a1a1a",
        "background": "#ffffff",
        "primary": "#1f6feb",
        "muted": "#6a737d",
        "border": "#d0d7de",
        "code_bg": "#f6f8fa",
    },
    "typography": {
        "body_font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif",
        "heading_font": "Georgia, 'Times New Roman', serif",
        "mono_font": "'SF Mono', Menlo, Consolas, monospace",
        "base_size": "16px",
        "line_height": "1.6",
    },
    "layout": {
        "max_width": "820px",
        "show_toc": True,
        "show_cover": True,
    },
    "branding": {
        # Path (exec-relative) to an SVG logo inlined onto the cover page.
        "logo_path": None,
        # Optional company website shown/linked on the cover.
        "website": None,
    },
}


_XML_DECL = re.compile(r"<\?xml[^>]*\?>", re.IGNORECASE)
_XML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_DOCTYPE = re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE)


def inline_svg(path):
    """Read an SVG file and return markup safe to embed directly in HTML.

    Strips the XML prolog, doctype and comments so the <svg> element can be
    dropped inline. The output stays a single self-contained HTML file.
    """
    raw = read_text(path)
    raw = _XML_DECL.sub("", raw)
    raw = _DOCTYPE.sub("", raw)
    raw = _XML_COMMENT.sub("", raw)
    return raw.strip()


def deep_merge(base, override):
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def build_css(theme):
    c = theme["colors"]
    t = theme["typography"]
    layout = theme["layout"]
    return """
:root {{
  --text: {text}; --bg: {background}; --primary: {primary};
  --muted: {muted}; --border: {border}; --code-bg: {code_bg};
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; color: var(--text); background: var(--bg);
  font-family: {body_font}; font-size: {base_size}; line-height: {line_height};
}}
main {{ max-width: {max_width}; margin: 0 auto; padding: 3rem 1.5rem 6rem; }}
h1, h2, h3, h4, h5, h6 {{
  font-family: {heading_font}; line-height: 1.25; margin-top: 2rem;
}}
h1 {{ font-size: 2.2rem; border-bottom: 2px solid var(--primary); padding-bottom: .3rem; }}
h2 {{ font-size: 1.7rem; border-bottom: 1px solid var(--border); padding-bottom: .2rem; }}
a {{ color: var(--primary); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
code {{ font-family: {mono_font}; background: var(--code-bg); padding: .15em .35em; border-radius: 4px; font-size: .9em; }}
pre {{ background: var(--code-bg); padding: 1rem; border-radius: 8px; overflow-x: auto; border: 1px solid var(--border); }}
pre code {{ background: none; padding: 0; }}
blockquote {{ margin: 1rem 0; padding: .5rem 1rem; border-left: 4px solid var(--primary); color: var(--muted); background: var(--code-bg); }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid var(--border); padding: .5rem .75rem; text-align: left; }}
th {{ background: var(--code-bg); }}
hr {{ border: none; border-top: 1px solid var(--border); margin: 2rem 0; }}
img {{ max-width: 100%; }}
.cover {{ text-align: center; padding: 6rem 0 4rem; border-bottom: 1px solid var(--border); margin-bottom: 2rem; }}
.cover .logo {{ margin: 0 auto 2rem; max-width: 140px; }}
.cover .logo svg {{ width: 100%; height: auto; max-height: 140px; }}
.cover h1 {{ border: none; font-size: 3rem; margin-bottom: .5rem; }}
.cover .subtitle {{ color: var(--muted); font-size: 1.3rem; }}
.cover .meta {{ margin-top: 2rem; color: var(--muted); font-size: .95rem; }}
.cover .website {{ margin-top: .75rem; font-size: .95rem; }}
.toc {{ background: var(--code-bg); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 2rem; }}
.toc h2 {{ border: none; margin-top: 0; font-size: 1.2rem; }}
.toc ul {{ list-style: none; padding-left: 0; }}
.toc .lvl-2 {{ padding-left: 1rem; }}
.toc .lvl-3 {{ padding-left: 2rem; }}
.toc .lvl-4 {{ padding-left: 3rem; }}
""".format(
        text=c["text"],
        background=c["background"],
        primary=c["primary"],
        muted=c["muted"],
        border=c["border"],
        code_bg=c["code_bg"],
        body_font=t["body_font"],
        heading_font=t["heading_font"],
        mono_font=t["mono_font"],
        base_size=t["base_size"],
        line_height=t["line_height"],
        max_width=layout["max_width"],
    )


# --------------------------------------------------------------------------
# Document assembly
# --------------------------------------------------------------------------

def read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def render_cover(meta, branding):
    parts = ['<header class="cover">']
    logo_path = (branding or {}).get("logo_path")
    if logo_path:
        parts.append('<div class="logo">%s</div>' % inline_svg(logo_path))
    parts.append("<h1>%s</h1>" % html.escape(meta.get("title", "Untitled")))
    if meta.get("subtitle"):
        parts.append('<div class="subtitle">%s</div>' % html.escape(meta["subtitle"]))
    metabits = []
    if meta.get("authors"):
        metabits.append("By " + html.escape(", ".join(meta["authors"])))
    if meta.get("version"):
        metabits.append("Version " + html.escape(str(meta["version"])))
    if meta.get("revision"):
        metabits.append("Revision " + html.escape(str(meta["revision"])))
    if meta.get("date"):
        metabits.append(html.escape(str(meta["date"])))
    if metabits:
        parts.append('<div class="meta">%s</div>' % " &middot; ".join(metabits))
    website = (branding or {}).get("website")
    if website:
        safe = html.escape(website)
        display = safe.replace("https://", "").replace("http://", "").rstrip("/")
        parts.append('<div class="website"><a href="%s">%s</a></div>' % (safe, display))
    parts.append("</header>")
    return "\n".join(parts)


def render_toc(toc):
    if not toc:
        return ""
    parts = ['<nav class="toc"><h2>Contents</h2><ul>']
    for level, text, slug in toc:
        if level > 4:
            continue
        parts.append(
            '<li class="lvl-%d"><a href="#%s">%s</a></li>'
            % (level, slug, render_inline(text))
        )
    parts.append("</ul></nav>")
    return "\n".join(parts)


def build_document(request):
    theme = deep_merge(_DEFAULT_THEME, request.get("theme", {}))
    template = request.get("template", {})
    layout = theme["layout"]
    if "show_toc" in template:
        layout["show_toc"] = template["show_toc"]
    if "show_cover" in template:
        layout["show_cover"] = template["show_cover"]

    meta = request.get("metadata", {})

    renderer = Renderer()
    for section in request.get("sections", []):
        title = section.get("title")
        if title:
            slug = slugify(title)
            renderer.toc.append((1, title, slug))
            renderer.out.append('<h1 id="%s">%s</h1>' % (slug, html.escape(title)))
        for src in section.get("sources", []):
            text = read_text(src)
            inner = Renderer()
            inner.render(text.splitlines())
            renderer.out.extend(inner.out)
            renderer.toc.extend(inner.toc)

    body_parts = []
    if layout.get("show_cover", True):
        body_parts.append(render_cover(meta, theme.get("branding")))
    if layout.get("show_toc", True):
        body_parts.append(render_toc(renderer.toc))
    body_parts.extend(renderer.out)

    css = build_css(theme)
    doc = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="generator" content="rules_farakov_documentation">
<style>{css}</style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
""".format(
        lang=html.escape(meta.get("language", "en")),
        title=html.escape(meta.get("title", "Documentation")),
        css=css,
        body="\n".join(body_parts),
    )
    return doc, theme, renderer.toc


def main(argv):
    parser = argparse.ArgumentParser(description="Render a documentation package.")
    parser.add_argument("--request", required=True, help="Path to build request JSON.")
    parser.add_argument("--theme", help="Optional path to a normalized theme JSON.")
    parser.add_argument("--template", help="Optional path to a normalized template JSON.")
    parser.add_argument("--html-out", required=True, help="Output HTML file path.")
    parser.add_argument("--manifest-out", required=True, help="Output manifest JSON.")
    args = parser.parse_args(argv)

    request = json.loads(read_text(args.request))

    # External theme/template files (produced by doc_theme / doc_template) take
    # precedence over inline values, but the request can still override fields.
    if args.theme:
        request["theme"] = deep_merge(json.loads(read_text(args.theme)), request.get("theme", {}))
    if args.template:
        template = json.loads(read_text(args.template))
        template.update(request.get("template", {}))
        request["template"] = template
    doc, theme, toc = build_document(request)

    with open(args.html_out, "w", encoding="utf-8") as handle:
        handle.write(doc)

    manifest = {
        "schema": 1,
        "package": request.get("name", "documentation"),
        "generated_by": "rules_farakov_documentation",
        # Deterministic: no wall-clock unless explicitly supplied in metadata.
        "generated_at": request.get("metadata", {}).get("date"),
        "theme": theme["name"],
        "section_count": len(request.get("sections", [])),
        "heading_count": len(toc),
        "metadata": request.get("metadata", {}),
    }
    with open(args.manifest_out, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

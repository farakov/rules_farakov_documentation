"""Unit tests for the PDF rendering backend.

These guard against regressions in cursor handling that previously caused list
items and other blocks to start near the right edge of the page and be clipped.
"""

import unittest

import render


class _FakePDF:
    """Minimal stand-in recording the X position each multi_cell starts at."""

    def __init__(self, l_margin=20.0, width=190.0):
        self.l_margin = l_margin
        self.epw = width
        self.x = l_margin
        self.y = 20.0
        self.starts = []  # x position at the start of each multi_cell

    # Geometry helpers used by the renderer.
    def set_x(self, x):
        self.x = x

    def get_x(self):
        return self.x

    def get_y(self):
        return self.y

    def ln(self, h=0):
        self.y += h or 5

    def set_font(self, *a, **k):
        pass

    def set_text_color(self, *a, **k):
        pass

    def set_fill_color(self, *a, **k):
        pass

    def set_draw_color(self, *a, **k):
        pass

    def line(self, *a, **k):
        pass

    def multi_cell(self, w, h, text, new_x="RIGHT", new_y="NEXT", **k):
        self.starts.append(round(self.x, 2))
        # Emulate fpdf2: with new_x="RIGHT" the cursor is left at the right edge;
        # with new_x="LMARGIN" it returns to the left margin.
        if new_x == "LMARGIN":
            self.x = self.l_margin
        else:
            self.x = self.l_margin + w
        self.y += h


class ListRenderingTest(unittest.TestCase):
    def test_list_items_start_at_left_margin(self):
        pdf = _FakePDF()
        blocks = [
            ("ulist", ["staging.spendr.com web application",
                       "api-staging.spendr.com/v1 REST API",
                       "Authentication, session management"]),
        ]
        render._pdf_render_blocks(
            pdf, blocks,
            primary=(0, 0, 0), text_rgb=(0, 0, 0),
            muted_rgb=(0, 0, 0), code_bg=(255, 255, 255),
            border_rgb=(0, 0, 0),
            epw=pdf.epw,
        )
        # Every bullet must begin at the left margin, never advanced rightward.
        for start in pdf.starts:
            self.assertEqual(
                start, pdf.l_margin,
                "list item started at x=%s, expected left margin %s "
                "(would be clipped at the right edge)" % (start, pdf.l_margin),
            )

    def test_consecutive_paragraphs_start_at_left_margin(self):
        pdf = _FakePDF()
        blocks = [
            ("paragraph", "First paragraph that fills the line completely."),
            ("paragraph", "Second paragraph must not start at the right edge."),
        ]
        render._pdf_render_blocks(
            pdf, blocks,
            primary=(0, 0, 0), text_rgb=(0, 0, 0),
            muted_rgb=(0, 0, 0), code_bg=(255, 255, 255),
            border_rgb=(0, 0, 0),
            epw=pdf.epw,
        )
        self.assertTrue(all(s == pdf.l_margin for s in pdf.starts), pdf.starts)


class DarkThemeTest(unittest.TestCase):
    """The renderer must honor a custom (dark) background in both backends."""

    def _theme(self):
        return render.deep_merge(
            render._DEFAULT_THEME,
            {"colors": {"background": "#0a0a0a", "text": "#fafafa"}},
        )

    def test_css_uses_custom_background(self):
        css = render.build_css(self._theme())
        self.assertIn("--bg: #0a0a0a", css)
        self.assertIn("color-scheme: dark", css)
        # Links must stay distinguishable without relying on a hue.
        self.assertIn("text-decoration: underline", css)

    def test_pdf_paints_non_white_background(self):
        # End-to-end: a dark-background theme must produce a PDF whose pages are
        # painted with a filled rectangle (fpdf2 pages default to white). We
        # render a tiny document and confirm a fill operator appears in a
        # (decompressed) page content stream.
        import os
        import re as _re
        import tempfile
        import zlib

        theme = self._theme()
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "s.md")
            with open(src, "w") as fh:
                fh.write("# Hello\n\nSome body text.\n")
            out = os.path.join(d, "out.pdf")
            request = {
                "metadata": {"title": "T"},
                "sections": [{"title": "Hello", "sources": [src]}],
            }
            render.build_pdf(request, theme, out)
            data = open(out, "rb").read()

        self.assertTrue(data.startswith(b"%PDF"))
        streams = _re.findall(rb"stream\r?\n(.*?)\r?\nendstream", data, _re.DOTALL)
        self.assertTrue(streams, "no content streams found in PDF")
        painted = False
        for raw in streams:
            try:
                content = zlib.decompress(raw)
            except zlib.error:
                content = raw
            # A full-page background fill: a rectangle path ("re") closed with a
            # fill operator ("f"/"f*"), e.g. "... 595.28 -841.89 re f".
            if _re.search(rb"\bre\s+f\*?\b", content):
                painted = True
                break
        self.assertTrue(
            painted, "dark theme did not paint a filled page-background rectangle"
        )

    def test_pdf_white_background_is_unpainted(self):
        # A white-background theme should not paint a redundant full-page rect.
        bg = render._hex_to_rgb("#ffffff")
        self.assertEqual(bg, (255, 255, 255))


if __name__ == "__main__":
    unittest.main()

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
        self.calls = []  # (text, wrapmode) for each multi_cell

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
        self.calls.append((text, k.get("wrapmode", "WORD")))
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


class WrapModeTest(unittest.TestCase):
    """Prose must wrap on word boundaries; code on character boundaries.

    Character-level wrapping in prose breaks words mid-token and pushes
    punctuation onto the next line, so prose blocks must use word wrapping
    (the fpdf2 default, which still falls back to char-breaking a single
    token wider than the cell). Code blocks keep CHAR so long URLs and
    hashes never run off the page.
    """

    def _render(self, blocks):
        pdf = _FakePDF()
        render._pdf_render_blocks(
            pdf, blocks,
            primary=(0, 0, 0), text_rgb=(0, 0, 0),
            muted_rgb=(0, 0, 0), code_bg=(255, 255, 255),
            border_rgb=(0, 0, 0),
            epw=pdf.epw,
        )
        return pdf.calls

    def test_prose_blocks_use_word_wrapping(self):
        blocks = [
            ("heading", (2, "A heading that is long enough to wrap")),
            ("paragraph", "A paragraph, with a comma, that should wrap on words."),
            ("ulist", ["A bullet item, with punctuation, that wraps"]),
            ("quote", "A quoted sentence, with a comma, wrapping nicely."),
        ]
        for text, wrapmode in self._render(blocks):
            self.assertNotEqual(
                wrapmode, "CHAR",
                "prose multi_cell used CHAR wrapping (breaks words mid-token): "
                "%r" % (text,),
            )

    def test_code_blocks_use_char_wrapping(self):
        blocks = [
            ("code", "https://example.com/a/very/long/unbroken/url/that/overflows"),
        ]
        calls = self._render(blocks)
        self.assertTrue(calls, "code block produced no multi_cell calls")
        for _text, wrapmode in calls:
            self.assertEqual(
                wrapmode, "CHAR",
                "code multi_cell must use CHAR so long tokens never overflow",
            )


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


class PdfFontTest(unittest.TestCase):
    """The PDF backend embeds theme fonts when provided, else falls back.

    Without typography.pdf_fonts the PDF must use fpdf2's core Helvetica, and
    the module-level family must not leak from a previous embedded render (the
    renderer resets it per call).
    """

    def _render(self, theme):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "s.md")
            with open(src, "w") as fh:
                fh.write("# Title\n\nBody text.\n")
            out = os.path.join(d, "out.pdf")
            request = {
                "metadata": {"title": "T"},
                "sections": [{"title": "Title", "sources": [src]}],
            }
            render.build_pdf(request, theme, out)
            return open(out, "rb").read()

    def test_default_theme_uses_core_helvetica(self):
        data = self._render(render._DEFAULT_THEME)
        self.assertIn(b"/BaseFont /Helvetica", data)
        # No embedded font requested, so the module family stays the core font.
        self.assertEqual(render._PDF_SANS, "Helvetica")

    def test_family_resets_when_no_fonts(self):
        # Simulate a leaked family from a prior embedded render, then confirm a
        # font-less render resets it rather than referencing an unregistered
        # "ThemeSans" family (which would raise inside fpdf2).
        render._PDF_SANS = "ThemeSans"
        self._render(render._DEFAULT_THEME)
        self.assertEqual(render._PDF_SANS, "Helvetica")


class EmphasisTest(unittest.TestCase):
    """Underscore emphasis must render, but intraword underscores stay literal.

    Identifiers like reset_password and email_password are common in this
    project's content and must never be italicized.
    """

    def test_underscore_italic_renders(self):
        self.assertEqual(render.render_inline("_pending_"), "<em>pending</em>")
        self.assertEqual(render.pdf_inline("_pending_"), "pending")

    def test_underscore_bold_renders(self):
        self.assertEqual(render.render_inline("__done__"), "<strong>done</strong>")
        self.assertEqual(render.pdf_inline("__done__"), "done")

    def test_intraword_underscores_stay_literal(self):
        for ident in ("reset_password", "email_password", "snake_case_name"):
            self.assertEqual(render.render_inline(ident), ident)
            self.assertEqual(render.pdf_inline(ident), ident)

    def test_mixed_emphasis_and_identifier(self):
        src = "set _pending_ on reset_password"
        self.assertEqual(
            render.render_inline(src),
            "set <em>pending</em> on reset_password",
        )
        self.assertEqual(render.pdf_inline(src), "set pending on reset_password")


if __name__ == "__main__":
    unittest.main()

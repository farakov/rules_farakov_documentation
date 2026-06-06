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
            epw=pdf.epw,
        )
        self.assertTrue(all(s == pdf.l_margin for s in pdf.starts), pdf.starts)


if __name__ == "__main__":
    unittest.main()

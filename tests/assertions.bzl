"""Test assertions for documentation packages.

These rules wrap the package outputs in lightweight shell tests that assert the
rendered HTML and manifest contain expected substrings. The tests are fully
hermetic: they only read files in the runfiles tree.
"""

load("@rules_farakov_documentation//documentation:defs.bzl", "DocPackageInfo")

def _content_test_impl(ctx):
    info = ctx.attr.target[DocPackageInfo]
    if ctx.attr.kind == "manifest":
        target_file = info.manifest
    elif ctx.attr.kind == "pdf":
        target_file = info.pdf
        if target_file == None:
            fail("pdf assertion requires the package to be built with pdf = True")
    else:
        target_file = info.html

    checks = []
    if ctx.attr.kind == "pdf":
        # PDFs are binary; assert the file exists and has the PDF magic header.
        checks.append(
            "head -c 5 \"$F\" | grep -q '%PDF-' || { echo 'NOT A PDF: missing %PDF- header'; FAIL=1; }",
        )
    for needle in ctx.attr.expected:
        # Single-quote the needle for the shell; needles here contain no single quotes.
        checks.append(
            "grep -F -- '{needle}' \"$F\" > /dev/null || {{ echo \"MISSING: {needle}\"; FAIL=1; }}".format(
                needle = needle,
            ),
        )
    for needle, want in ctx.attr.expected_counts.items():
        checks.append(
            ("N=$(grep -F -c -- '{needle}' \"$F\" || true); " +
             "if [ \"$N\" != \"{want}\" ]; then " +
             "echo \"COUNT MISMATCH for '{needle}': want {want}, got $N\"; FAIL=1; fi").format(
                needle = needle,
                want = want,
            ),
        )

    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        output = script,
        is_executable = True,
        content = """#!/usr/bin/env bash
set -euo pipefail
F="{path}"
if [ ! -f "$F" ]; then
  echo "Output file not found: $F"
  exit 1
fi
FAIL=0
{checks}
if [ "$FAIL" -ne 0 ]; then
  echo "--- file contents ---"
  cat "$F"
  exit 1
fi
echo "All {n} assertion(s) passed for $F"
""".format(
            path = target_file.short_path,
            checks = "\n".join(checks),
            n = len(ctx.attr.expected),
        ),
    )

    runfiles = ctx.runfiles(files = [target_file])
    return [DefaultInfo(executable = script, runfiles = runfiles)]

_content_test = rule(
    implementation = _content_test_impl,
    test = True,
    attrs = {
        "target": attr.label(providers = [DocPackageInfo], mandatory = True),
        "expected": attr.string_list(),
        "expected_counts": attr.string_dict(
            doc = "Map of substring -> exact occurrence count.",
        ),
        "kind": attr.string(values = ["html", "manifest", "pdf"], default = "html"),
    },
)

def output_contains_test(name, target, expected = [], expected_counts = {}):
    """Assert the rendered HTML output contains substrings / exact counts."""
    _content_test(
        name = name,
        target = target,
        expected = expected,
        expected_counts = expected_counts,
        kind = "html",
        size = "small",
    )

def manifest_contains_test(name, target, expected):
    """Assert the package manifest contains each expected substring."""
    _content_test(name = name, target = target, expected = expected, kind = "manifest", size = "small")

def pdf_produced_test(name, target):
    """Assert the package produced a valid (well-formed header) PDF."""
    _content_test(name = name, target = target, kind = "pdf", size = "small")

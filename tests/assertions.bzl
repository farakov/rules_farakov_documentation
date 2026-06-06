"""Test assertions for documentation packages.

These rules wrap the package outputs in lightweight shell tests that assert the
rendered HTML and manifest contain expected substrings. The tests are fully
hermetic: they only read files in the runfiles tree.
"""

load("@rules_farakov_documentation//documentation:defs.bzl", "DocPackageInfo")

def _content_test_impl(ctx):
    info = ctx.attr.target[DocPackageInfo]
    target_file = info.manifest if ctx.attr.kind == "manifest" else info.html

    checks = []
    for needle in ctx.attr.expected:
        # Single-quote the needle for the shell; needles here contain no single quotes.
        checks.append(
            "grep -F -- '{needle}' \"$F\" > /dev/null || {{ echo \"MISSING: {needle}\"; FAIL=1; }}".format(
                needle = needle,
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
        "expected": attr.string_list(mandatory = True),
        "kind": attr.string(values = ["html", "manifest"], default = "html"),
    },
)

def output_contains_test(name, target, expected):
    """Assert the rendered HTML output contains each expected substring."""
    _content_test(name = name, target = target, expected = expected, kind = "html", size = "small")

def manifest_contains_test(name, target, expected):
    """Assert the package manifest contains each expected substring."""
    _content_test(name = name, target = target, expected = expected, kind = "manifest", size = "small")

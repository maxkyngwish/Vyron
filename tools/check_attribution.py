"""Fail the build if the "Made by Maxkingwish" credit is removed or hidden.

This guard exists because the credit is part of VYRON's identity and licence.
See ATTRIBUTION.md. Run it before every commit:

    py tools/check_attribution.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDIT = "Made by Maxkingwish"
COPYRIGHT = "Copyright (c) 2026 Maxkingwish"

failures = []


def read(*parts):
    path = os.path.join(ROOT, *parts)
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as error:
        failures.append("missing file: %s (%s)" % (os.path.join(*parts), error))
        return ""


def require(condition, message):
    if not condition:
        failures.append(message)


def check_app():
    source = read("vyron", "app.py")
    require(
        re.search(
            r'ctk\.CTkLabel\(\s*footer,\s*text="Made by Maxkingwish"',
            source,
        ),
        'app.py: the sidebar footer label "Made by Maxkingwish" is missing or modified.',
    )
    footer = re.search(
        r'ctk\.CTkLabel\(\s*footer,\s*text="Made by Maxkingwish".*?\)\.pack\(',
        source,
        re.DOTALL,
    )
    if footer:
        block = footer.group(0)
        require(
            "transparent" not in block and "text_color=BG" not in block,
            "app.py: the footer credit looks hidden (transparent or background colour).",
        )
    else:
        failures.append("app.py: the footer credit is not packed (it would be invisible).")
    require(
        source.count('self.t("made_by")') >= 2,
        'app.py: the About page must show the "made_by" credit twice (title + footer).',
    )


def check_i18n():
    sys.path.insert(0, ROOT)
    try:
        from vyron.i18n import LANGUAGES, TEXT
    except Exception as error:  # pragma: no cover - import guard
        failures.append("cannot import vyron.i18n: %s" % error)
        return
    require(
        isinstance(LANGUAGES, dict) and len(LANGUAGES) >= 1,
        "i18n: no languages found.",
    )
    for code in LANGUAGES:
        value = (TEXT.get(code) or {}).get("made_by")
        require(
            value == CREDIT,
            'i18n: language "%s" must keep made_by = "%s" (found %r).'
            % (code, CREDIT, value),
        )


def check_docs():
    for name in ("README.md", "README.fr.md", "ATTRIBUTION.md"):
        content = read(name)
        require(CREDIT in content, "%s: the credit line is missing." % name)
    licence = read("LICENSE")
    require(COPYRIGHT in licence, "LICENSE: the copyright holder line is missing.")


def main():
    check_app()
    check_i18n()
    check_docs()
    if failures:
        print("Attribution check FAILED:")
        for failure in failures:
            print("  - " + failure)
        print("")
        print("The credit is protected by ATTRIBUTION.md and must not be removed,")
        print("translated, shortened or hidden. Restore it, then run this check again.")
        return 1
    print("Attribution check OK - " + CREDIT)
    return 0


if __name__ == "__main__":
    sys.exit(main())

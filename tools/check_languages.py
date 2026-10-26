"""Fail if the six translations diverge.

Every user-facing key must exist in every language with the same key set,
otherwise the UI falls back to English silently. Run with:

    py tools/check_languages.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from vyron.i18n import LANGUAGES, TEXT  # noqa: E402


def main():
    base_lang = "en"
    base = set(TEXT.get(base_lang) or {})
    failed = False
    if not base:
        print("No English strings found.")
        return 1
    for code in LANGUAGES:
        keys = set(TEXT.get(code) or {})
        missing = sorted(base - keys)
        extra = sorted(keys - base)
        if missing or extra:
            failed = True
            print("Language %s is out of sync." % code)
            for key in missing:
                print("  missing: " + key)
            for key in extra:
                print("  extra:   " + key)
    if failed:
        print("Translation check FAILED.")
        return 1
    print(
        "Translation check OK - %d keys x %d languages" % (len(base), len(LANGUAGES))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Sync README.md → docs/index.md for MkDocs.

Run before every `mkdocs build` or `mkdocs gh-deploy`:

    python scripts/generate_readme.py

Inspired by:
  https://github.com/arogozhnikov/einops/blob/main/scripts/convert_readme.py

Transformations applied
-----------------------
* ``](docs/`` → ``](``   — strip the docs/ prefix from in-repo links so they
  resolve correctly inside the docs/ directory.
* ``src="docs/``  → ``src="``  — same fix for HTML src attributes.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
README_PATH = PROJECT_ROOT / "README.md"
DOCS_INDEX = PROJECT_ROOT / "docs" / "index.md"


def _fix_docs_links(line: str) -> str:
    """Strip the ``docs/`` prefix from Markdown and HTML links."""
    line = re.sub(r"\]\(docs/", "](", line)
    line = re.sub(r'src="docs/', 'src="', line)
    return line


def convert(source: str) -> str:
    """Apply all README → MkDocs transformations and return the result."""
    lines = []
    for line in source.splitlines():
        line = _fix_docs_links(line)
        lines.append(line)
    return "\n".join(lines)


def main() -> None:
    """Read README.md, transform it, and write docs/index.md."""
    source = README_PATH.read_text(encoding="utf-8")
    result = convert(source)
    DOCS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    DOCS_INDEX.write_text(result, encoding="utf-8")
    print(f"Synced {README_PATH.relative_to(PROJECT_ROOT)} → {DOCS_INDEX.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

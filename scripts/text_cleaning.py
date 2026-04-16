from __future__ import annotations

import re


_MULTISPACE_RE = re.compile(r"[ \t]+")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def clean_page_text(text: str) -> str:
    """
    Apply conservative cleanup to extracted PDF text.

    This first-pass cleaner intentionally avoids aggressive logic such as
    header/footer stripping or table reconstruction.
    """
    if not text:
        return ""

    # Normalize newlines first
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix hyphenated line breaks:
    # "low-\nvision" -> "low-vision"
    text = re.sub(r"([A-Za-z])-\n([A-Za-z])", r"\1-\2", text)

    # Join lines that were broken mid-sentence/paragraph.
    # Keep paragraph breaks intact by only replacing single newlines
    # that sit between non-empty text.
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # Restore paragraph structure by collapsing large whitespace groups
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Split into lines for line-based cleanup
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        line = line.strip()

        # Skip empty lines for now; we'll normalize later
        if not line:
            cleaned_lines.append("")
            continue

        # Remove standalone artifact lines like "**"
        if re.fullmatch(r"\*+", line):
            continue

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)

    # Remove trailing standalone page number at the very end
    # e.g. "... \n\n5"
    text = re.sub(r"\n\s*\d+\s*$", "", text)

    # Clean up excessive blank lines again after removals
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
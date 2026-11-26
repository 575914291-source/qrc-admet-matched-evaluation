from __future__ import annotations

import re
from pathlib import Path

from docx import Document

from src.config import PROJECT_ROOT


OUTPUT_ROOT = PROJECT_ROOT / "outputs"


def _normalize(
    source: Path,
    *,
    language: str,
) -> None:
    text = source.read_text(encoding="utf-8").lstrip("\ufeff")
    text = re.sub(
        r'src="([^"]+)"',
        lambda match: 'src="' + match.group(1).replace("\\", "/") + '"',
        text,
    )

    docx_path = source.with_suffix(".docx")
    document = Document(docx_path)
    title = document.paragraphs[0].text.strip()
    subtitle = document.paragraphs[1].text.strip()
    text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)
    front_matter = (
        "---\n"
        f'title: "{title}"\n'
        f'subtitle: "{subtitle}"\n'
        f"lang: {language}\n"
        "---\n\n"
    )
    source.write_text(front_matter + text, encoding="utf-8")


def main() -> None:
    _normalize(OUTPUT_ROOT / "Final_Manuscript_EN.md", language="en")
    _normalize(OUTPUT_ROOT / "Final_Manuscript_ZH.md", language="zh-CN")


if __name__ == "__main__":
    main()

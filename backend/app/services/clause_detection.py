"""
clause_detection.py — rule-based clause/section segmentation for legal
documents. No ML model (per Phase 5D scope: "Do NOT train a new ML model").

Strategy: split each page's text on blank-line paragraph breaks (the most
reliable generic signal across varied document formatting), then check each
paragraph's first line against common legal-heading patterns (numbered
clauses, "Section N", "Article N") to attach a heading label when one is
present. Paragraphs are the unit of a "clause" here — short fragments
(<20 chars) are dropped as noise (page numbers, stray whitespace, etc.).
"""

import re
from dataclasses import dataclass
from typing import List, Optional

HEADING_PATTERN = re.compile(
    r'^\s*(?:\d+(?:\.\d+)*[\.\)]\s+|Section\s+\d+[:\.]?\s*|Article\s+(?:[IVXLCDM]+|\d+)[:\.]?\s*)',
    re.IGNORECASE,
)

MIN_CLAUSE_LENGTH = 20


@dataclass
class Clause:
    clause_id: str
    heading: Optional[str]
    text: str
    page_number: int


def segment_clauses(pages) -> List[Clause]:
    """
    pages: iterable of objects/dicts with .page_number/.text (or
    ["page_number"]/["text"] — accepts either PageText dataclass instances
    or plain dicts, since both appear across this codebase).
    """
    clauses: List[Clause] = []
    counter = 0

    for page in pages:
        page_number = getattr(page, "page_number", None) if not isinstance(page, dict) else page.get("page_number")
        text = getattr(page, "text", None) if not isinstance(page, dict) else page.get("text")
        if not text:
            continue

        raw_paragraphs = re.split(r'\n\s*\n', text)

        for para in raw_paragraphs:
            para = para.strip()
            if len(para) < MIN_CLAUSE_LENGTH:
                continue

            first_line = para.split('\n', 1)[0].strip()
            heading = None
            if HEADING_PATTERN.match(first_line):
                heading = first_line
            elif first_line.isupper() and 3 < len(first_line) < 100:
                heading = first_line

            counter += 1
            clauses.append(Clause(
                clause_id=f"clause_{counter}",
                heading=heading,
                text=para,
                page_number=page_number,
            ))

    return clauses

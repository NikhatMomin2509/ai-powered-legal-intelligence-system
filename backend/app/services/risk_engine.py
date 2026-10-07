"""
risk_engine.py — rule/keyword-based risk flagging for document clauses.

MVP approach, explicitly NOT a trained classifier and NOT a legal
determination (per Phase 5D scope: "Do NOT claim legal certainty"). Every
flagged clause's "reason" field says so explicitly, and the aggregate
disclaimer (added by document_service.py) reiterates it at the document
level.
"""

from dataclasses import dataclass
from typing import List

RISK_CATEGORIES = {
    "Penalty": {
        "keywords": ["penalty", "penalties", "liquidated damages", "forfeit"],
        "level": "HIGH",
    },
    "Termination": {
        "keywords": ["terminate this agreement", "right to terminate", "termination of this"],
        "level": "MEDIUM",
    },
    "Automatic Renewal": {
        "keywords": ["automatically renew", "auto-renew", "automatic renewal", "evergreen clause"],
        "level": "MEDIUM",
    },
    "Excessive Liability": {
        "keywords": ["unlimited liability", "sole liability", "liable for all", "liable for any and all"],
        "level": "HIGH",
    },
    "Indemnity": {
        "keywords": ["indemnify", "indemnification", "hold harmless"],
        "level": "HIGH",
    },
    "One-Sided Obligation": {
        "keywords": ["sole discretion", "at its sole discretion", "without cause", "non-negotiable"],
        "level": "MEDIUM",
    },
    "Payment / Default": {
        "keywords": ["event of default", "late payment", "non-payment", "interest at the rate of"],
        "level": "MEDIUM",
    },
    "Restrictive Clause": {
        "keywords": ["non-compete", "non-solicitation", "exclusivity", "shall not engage in"],
        "level": "HIGH",
    },
    "Confidentiality": {
        "keywords": ["confidential information", "non-disclosure", "trade secret"],
        "level": "LOW",
    },
    "Dispute Resolution": {
        "keywords": ["arbitration", "mediation", "dispute shall be resolved", "dispute resolution"],
        "level": "LOW",
    },
    "Jurisdiction": {
        "keywords": ["governing law", "exclusive jurisdiction", "courts of"],
        "level": "LOW",
    },
    "Unusual Obligation": {
        "keywords": ["waives all rights", "irrevocably agrees", "in perpetuity"],
        "level": "HIGH",
    },
}

LEVEL_SCORES = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}


@dataclass
class RiskFlag:
    clause_id: str
    page_number: int
    risk_level: str
    risk_category: str
    clause_text: str
    reason: str


def detect_risks(clauses) -> List[RiskFlag]:
    """clauses: list of Clause objects (or dicts) with .clause_id/.text/.page_number."""
    flagged: List[RiskFlag] = []

    for clause in clauses:
        clause_id = getattr(clause, "clause_id", None) if not isinstance(clause, dict) else clause.get("clause_id")
        text = getattr(clause, "text", None) if not isinstance(clause, dict) else clause.get("text")
        page_number = getattr(clause, "page_number", None) if not isinstance(clause, dict) else clause.get("page_number")
        text_lower = text.lower()

        for category, rule in RISK_CATEGORIES.items():
            matched_keyword = next((kw for kw in rule["keywords"] if kw in text_lower), None)
            if matched_keyword:
                flagged.append(RiskFlag(
                    clause_id=clause_id,
                    page_number=page_number,
                    risk_level=rule["level"],
                    risk_category=category,
                    clause_text=text,
                    reason=(
                        f"Rule-based flag: this clause contains language associated with "
                        f"'{category}' (matched: \"{matched_keyword}\"). This is a keyword match, "
                        f"not a legal determination — review the full clause in context."
                    ),
                ))

    return flagged


def calculate_risk_score(flagged: List[RiskFlag]):
    """
    Scoring logic (documented, intentionally simple and transparent):
      raw = sum(LEVEL_SCORES[flag.risk_level] for flag in flagged)
      max_possible = len(flagged) * 3          (if every flag had been HIGH)
      score = round(100 * raw / max_possible)  if flagged else 0

    This measures the SEVERITY MIX of what was flagged (a document with 3
    HIGH flags scores higher than one with 10 LOW flags), not raw flag
    COUNT. It does NOT account for document length or clause density —
    a short document with one HIGH-risk clause scores the same as a long
    one with the same single flag. This is a known simplification, stated
    here explicitly rather than left implicit.
    """
    if not flagged:
        return 0, "Low"

    raw = sum(LEVEL_SCORES[f.risk_level] for f in flagged)
    max_possible = len(flagged) * 3
    score = round(100 * raw / max_possible)

    if score >= 67:
        level = "High"
    elif score >= 34:
        level = "Medium"
    else:
        level = "Low"

    return score, level

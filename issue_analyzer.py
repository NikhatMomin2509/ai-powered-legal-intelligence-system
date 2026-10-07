"""
issue_analyzer.py — Module 2 orchestration: analyze_legal_issue(query) -> dict

Design for grounding (the core anti-hallucination mechanism):

  1. An LLM call extracts facts/domain from the user's own text (no legal
     claims made here, purely restating what the user said).
  2. rag_engine retrieves REAL laws/cases and assigns each a short ref_id
     (L1, L2, ... / C1, C2, ...).
  3. A second LLM call sees ONLY the retrieved content (never the raw
     internet, never its own training data) and is asked to reason using
     ref_ids as citations — it never has to reproduce a section number or
     case name from memory, because it's just pointing at something we
     already fetched.
  4. Code — not the LLM — then re-attaches the REAL metadata (act, section,
     title, case_name, source, ...) for every ref_id the LLM cited. If the
     LLM cites a ref_id that doesn't exist in what we retrieved, that
     citation is DROPPED and logged rather than trusted, because the whole
     point of ref_ids is that only ones we actually retrieved are valid.
  5. The disclaimer is a fixed string appended in code — never left to the
     LLM to remember.

This means a factual/legal claim can only reach the final output attached
to something traceable to indian_legal_acts_master.json or
case_law_master.json. Free-text fields (considerations, remedies, summary)
are still LLM-generated and should be read as reasoning over the retrieved
context, not as independently verified legal fact.
"""

import json
import re

from rag_engine import retrieve_legal_context
from llm_client import call_llm, LLMTruncatedError

STATE_LAW_SCOPE_NOTE = (
    "Tenancy and rent-control rules vary significantly by Indian state, and this "
    "system's knowledge base does not currently include any state-specific Rent "
    "Control Act. The retrieved provisions above (if any) are central/national "
    "statutes only — check applicable state legislation separately."
)

DISCLAIMER = (
    "This is an AI-generated, informational legal analysis based on retrieved "
    "Indian legal provisions and judicial precedents. It is NOT legal advice, "
    "does not constitute a legal opinion, and does not predict the outcome of "
    "any court proceeding. It is not a substitute for consultation with a "
    "qualified, licensed advocate who can review the complete facts of your "
    "situation."
)


def _strip_think_tags(text):
    """Some Groq reasoning models (per Groq's own 'raw' reasoning_format
    behavior) can emit hidden reasoning inline in message.content wrapped in
    <think>...</think>, even when we didn't ask for that format. Strip it
    defensively — cheap, and harmless if absent."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)


def _find_balanced_json_objects(text):
    """Scans `text` and returns every COMPLETE, top-level {...} substring,
    found by tracking brace nesting depth character-by-character (and
    ignoring braces that appear inside quoted strings). This is deliberately
    NOT `re.search(r"\\{.*\\}")`, which greedily spans from the first '{' to
    the LAST '}' anywhere in the text — if a reasoning model's surrounding
    prose contains any stray brace (an example, a set-notation aside, a
    JSON snippet it's reasoning about), that naive approach silently grabs
    the wrong span and produces text that looks JSON-like but doesn't parse,
    or worse, parses into a different, larger, wrong structure than the
    intended object. Proper depth tracking + string-awareness means the
    boundary of each real JSON object is found correctly regardless of what
    surrounds it (reasoning text, markdown fences, prose before/after).
    """
    objects = []
    depth = 0
    start = None
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    objects.append(text[start:i + 1])
    return objects


def _extract_json(raw_text):
    """
    Robust JSON extraction for reasoning-model output. Handles, in order:
      1. Plain JSON (the whole response is exactly the JSON object).
      2. JSON wrapped in a single markdown ```json ... ``` fence.
      3. Reasoning content before/after the JSON, including inline
         <think>...</think> blocks some Groq reasoning models emit.
      4. Nested arrays/objects inside the JSON (handled correctly because
         _find_balanced_json_objects tracks real nesting depth, not just
         brace counting from string ends).

    Strategy: try fast/simple paths first (cheap, correct for the common
    case), then fall back to scanning for every balanced top-level object in
    the text and returning the LAST one that actually parses — later blocks
    are more likely to be the model's final answer than an earlier
    example/draft it reasoned through.
    """
    if raw_text is None:
        raise ValueError("LLM returned no content at all (message.content was None) — "
                          "check whether reasoning consumed the entire token budget.")

    text = _strip_think_tags(raw_text.strip())

    # Fast path 1: strip a single leading/trailing markdown fence, try whole text.
    fenced = re.sub(r"^```(?:json)?\s*", "", text.strip())
    fenced = re.sub(r"\s*```$", "", fenced.strip())
    for candidate_text in (fenced, text):
        try:
            return json.loads(candidate_text)
        except (json.JSONDecodeError, TypeError):
            pass

    # Robust path: scan for every balanced top-level {...} object anywhere
    # in the text and try the LAST one that parses successfully.
    candidates = _find_balanced_json_objects(text)
    for candidate in reversed(candidates):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise ValueError(
        f"No valid JSON object found after stripping <think> tags/markdown fences and "
        f"scanning {len(candidates)} balanced-brace candidate(s) in the response. "
        f"This usually means either the model didn't follow the JSON-only instruction, or "
        f"the response was truncated (check for an LLMTruncatedError instead, which is "
        f"raised separately by llm_client.call_llm when finish_reason=='length'). "
        f"Raw output (first 500 chars): {raw_text[:500]!r}"
    )


def _extract_facts(user_query):
    system_prompt = (
        "You are a legal-intake assistant. Read the user's description of a "
        "legal problem and extract ONLY what they actually said — do not add "
        "facts, dates, laws, or assumptions they did not state. "
        "Respond with ONLY a JSON object, no other text, with these exact keys:\n"
        '{"legal_domain": "short label, e.g. Property/Rental Dispute, Employment, '
        'Consumer Protection, Criminal, Other",\n'
        ' "key_facts": ["short factual statement", ...],\n'
        ' "search_query": "a short phrase optimized for searching a legal database, '
        'combining the core issue and domain"}'
    )
    # max_tokens bumped 400 -> 700: gpt-oss-20b is a reasoning model and
    # hidden reasoning tokens count against this same budget, unlike the
    # old non-reasoning llama-3.1-8b-instant. 400 was tight enough to
    # truncate mid-JSON on some inputs (see Phase 4 bugfix notes).
    raw = call_llm(system_prompt, user_query, max_tokens=700, reasoning_effort="low")
    return _extract_json(raw)


def _format_context_for_prompt(context):
    law_lines = []
    for law in context["laws"]:
        law_lines.append(
            f"[{law['ref_id']}] {law['act']} Section {law['section']} — {law['title']}\n"
            f"    {law['content']}"
        )
    case_lines = []
    for case in context["cases"]:
        case_lines.append(
            f"[{case['ref_id']}] {case['case_name']} (domain: {case['domain']})\n"
            f"    {case['excerpt'][:600]}"
        )
    law_block = "\n\n".join(law_lines) if law_lines else "(no relevant law sections retrieved)"
    case_block = "\n\n".join(case_lines) if case_lines else "(no relevant case law retrieved)"
    return law_block, case_block


def _generate_assessment(user_query, facts, context):
    law_block, case_block = _format_context_for_prompt(context)

    system_prompt = f"""You are a legal-research assistant analyzing an Indian legal issue.

USER ISSUE:
{user_query}

EXTRACTED FACTS (from the user's own statement):
{json.dumps(facts.get('key_facts', []), indent=2)}

RETRIEVED LAWS:
{law_block}

RETRIEVED CASES:
{case_block}

INSTRUCTIONS:
- Analyze the issue using ONLY the retrieved laws and cases above plus the user's stated facts.
- Do NOT invent laws, sections, case names, quotations, or citations. If you refer to a
  retrieved law or case, cite it ONLY by its ref_id shown above (e.g. "L1", "C2").
- If the retrieved context does not establish something relevant, say so explicitly rather
  than filling the gap from general knowledge.
- Clearly separate: facts the user stated, what the retrieved authorities say, and your own
  reasoning/inference connecting them.
- Identify facts that are MISSING and would materially change the assessment.
- List considerations that SUPPORT the user's position and, separately, considerations that
  could WEAKEN or OPPOSE it — a real assessment must include both sides.
- Suggest possible remedies/next steps as informational possibilities only.
- Do NOT predict what a court will decide. Do NOT say the user is "right" or "will win".
- Recommend only a general lawyer SPECIALIZATION CATEGORY (e.g. "Property/Rental Dispute
  Lawyer"), never a specific named lawyer or firm.
- If a retrieved provision is the Transfer of Property Act Section 108, note that it states
  GENERAL lessor/lessee obligations — it does NOT itself guarantee return of a security
  deposit. Do not claim otherwise.
- Tenancy/rent-control rules vary by Indian state and no state-specific Rent Control Act is
  in this knowledge base — do not imply state law has been checked.

CITATION DISCIPLINE (read carefully — this is a common failure mode, do not repeat it):
- When you write why_relevant for a cited law, describe ONLY what that provision's retrieved
  text actually says — never more than that.
- A DEFINITION is not a REMEDY. A section that says "X means ..." or "deficiency means ..."
  DEFINES a term. It does NOT, by itself, "establish an obligation", "guarantee a remedy",
  "require" anything, or "entitle" anyone to anything, UNLESS the retrieved text itself
  contains that operative/obligating language. Do not write phrases like "establishes the
  seller's obligation to remedy X" when the cited text is only a definition of "deficiency"
  or a similar term — that is exactly the kind of unsupported inference you must not make.
- Concretely: if a provision only defines when a situation qualifies as a problem (e.g. what
  counts as a "deficiency of service"), say exactly that ("L1 defines 'deficiency of service',
  which may describe the situation described by the user") — do NOT continue on to assert
  what remedy follows, unless a DIFFERENT retrieved provision actually specifies that remedy.
- If the user's situation calls for a specific remedy (replacement, refund, compensation,
  etc.) and no retrieved provision explicitly establishes that remedy, do NOT assert that the
  remedy exists. Instead, say in possible_actions_or_remedies or missing_facts that the
  specific remedy could not be confirmed from the retrieved provisions and would need
  separate verification (e.g. "a specific right to replacement/refund was not established by
  the retrieved text; this would need to be verified against the full Consumer Protection Act
  provisions on remedies, which are not in the current retrieval set").
- When in doubt between stating a legal conclusion and flagging it as unverified: flag it as
  unverified. An omitted or hedged claim is far better than an unsupported one.

Respond with ONLY a JSON object, no other text, with these exact keys:
{{
  "issue_summary": "1-2 sentence neutral restatement of the issue",
  "supporting_considerations": ["...", "..."],
  "opposing_considerations": ["...", "..."],
  "missing_facts": ["...", "..."],
  "possible_actions_or_remedies": ["...", "..."],
  "lawyer_specialization": "category label",
  "laws_cited": [{{"ref_id": "L1", "why_relevant": "..."}}],
  "cases_cited": [{{"ref_id": "C1", "why_relevant": "..."}}]
}}
"""
    # max_tokens bumped 1500 -> 3000: this prompt embeds up to 5 law + 5 case
    # excerpts and asks for a multi-field structured JSON response — the old
    # budget was tight even for a non-reasoning model, and gpt-oss-20b's
    # hidden reasoning tokens draw from the same budget, making truncation
    # (finish_reason='length') far more likely. reasoning_effort="medium":
    # this is the actual legal-analysis step, worth a bit more reasoning
    # budget than the simpler fact-extraction call.
    raw = call_llm(system_prompt, "Produce the JSON assessment now.",
                    max_tokens=3000, reasoning_effort="medium")
    return _extract_json(raw)


def _merge_citations(assessment, context, key_field, cited_field, lookup_extra_fields):
    """Re-attaches REAL metadata for every ref_id the LLM cited. Drops any
    ref_id that doesn't correspond to something we actually retrieved —
    this is the enforcement point, not just a prompt instruction."""
    by_ref = {item["ref_id"]: item for item in context[key_field]}
    merged = []
    dropped = []
    for cited in assessment.get(cited_field, []):
        ref_id = cited.get("ref_id")
        if ref_id not in by_ref:
            dropped.append(ref_id)
            continue
        real = by_ref[ref_id]
        entry = {f: real.get(f) for f in lookup_extra_fields}
        entry["why_relevant"] = cited.get("why_relevant", "")
        entry["retrieval_score"] = real.get("retrieval_score")
        merged.append(entry)
    if dropped:
        print(f"[issue_analyzer] WARNING: LLM cited ref_id(s) not in retrieved context "
              f"for '{cited_field}' — dropped (not fabricated into output): {dropped}")
    return merged


def analyze_legal_issue(user_query, law_k=7, case_k=5):
    # law_k bumped 5 -> 7 (Phase 4 fix C, paired with rag_engine's widened
    # candidate_k): gives the assessment LLM a slightly larger window to
    # find TPA 106 / Contract Act 73 even if they rank just outside the old
    # top-5. Case_k left unchanged — case retrieval noise is a separate,
    # not-yet-addressed issue per your instructions (case index untouched).
    facts = _extract_facts(user_query)
    context = retrieve_legal_context(facts.get("search_query", user_query), law_k, case_k)
    assessment = _generate_assessment(user_query, facts, context)

    relevant_laws = _merge_citations(
        assessment, context, "laws", "laws_cited",
        lookup_extra_fields=["ref_id", "act", "section", "title", "category"]
    )
    relevant_cases = _merge_citations(
        assessment, context, "cases", "cases_cited",
        lookup_extra_fields=["ref_id", "case_id", "case_name", "domain", "source"]
    )

    missing_facts = list(assessment.get("missing_facts", []))
    # Code-enforced (not left to the LLM): if any cited law touches tenancy,
    # explicitly flag the state-law scope gap. This must not depend on the
    # LLM remembering to mention it.
    if any(law.get("category") == "Property / Tenancy" for law in relevant_laws):
        missing_facts.append(STATE_LAW_SCOPE_NOTE)

    return {
        "issue_summary": assessment.get("issue_summary", ""),
        "legal_domain": facts.get("legal_domain", "Unclear"),
        "key_facts": facts.get("key_facts", []),
        "missing_facts": missing_facts,
        "relevant_laws": relevant_laws,
        "relevant_cases": relevant_cases,
        "supporting_considerations": assessment.get("supporting_considerations", []),
        "opposing_considerations": assessment.get("opposing_considerations", []),
        "possible_actions_or_remedies": assessment.get("possible_actions_or_remedies", []),
        "lawyer_specialization": assessment.get("lawyer_specialization", ""),
        "disclaimer": DISCLAIMER,
        "_raw_retrieval_counts": {  # useful for the evaluation step, not user-facing
            "laws_retrieved": len(context["laws"]),
            "cases_retrieved": len(context["cases"]),
            "laws_cited": len(relevant_laws),
            "cases_cited": len(relevant_cases),
        },
    }

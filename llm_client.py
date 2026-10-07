"""
llm_client.py — thin wrapper around the Groq API.

SECURITY:
- The API key is read ONLY from the environment (via .env + python-dotenv).
- It is never hardcoded, never logged, never printed, never included in any
  exception message.
- If the key is missing, we raise a clear instruction to create .env from
  .env.example — we do not ask the user to paste the key anywhere in chat
  or in code.
"""

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # reads .env in the project root if present

DEFAULT_MODEL = "openai/gpt-oss-20b"  # llama-3.1-8b-instant was deprecated by Groq on 2026-08-16;
                                       # gpt-oss-20b verified as a current, active Groq model
                                       # (reasoning-capable, 131K context) before this change.


class LLMConfigError(RuntimeError):
    pass


class LLMTruncatedError(RuntimeError):
    """Raised when the model's response was cut off by max_tokens before it
    finished (finish_reason == 'length'). This is surfaced explicitly rather
    than being left to manifest downstream as a confusing JSON-parse failure
    — see Phase 4 bugfix notes: gpt-oss-20b is a reasoning model, and hidden
    reasoning tokens count against the same max_tokens budget as the visible
    answer, so a budget that was fine for llama-3.1-8b-instant can now be too
    small and silently truncate the JSON output mid-object."""
    pass


_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise LLMConfigError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and put your "
                "Groq API key there. This wrapper will never print the key value."
            )
        _client = Groq(api_key=api_key)
    return _client


def call_llm(system_prompt, user_prompt, model=DEFAULT_MODEL, max_tokens=2000,
             temperature=0.2, reasoning_effort="low"):
    """
    Low temperature by design: this is a grounded-extraction/analysis task,
    not creative writing — we want the model to stick closely to the
    retrieved context rather than vary its phrasing of legal claims.

    reasoning_effort: gpt-oss-20b is a reasoning model. Groq's own docs are
    inconsistent about whether reasoning_format/reasoning_effort are
    supported for this specific model (one page says reasoning_format is
    NOT supported for gpt-oss and reasoning goes to a separate `reasoning`
    field by default; another lists reasoning_effort as a general control
    for reasoning models). Rather than betting on either documented
    behavior, we TRY reasoning_effort (it reduces hidden reasoning-token
    spend, leaving more of max_tokens for the actual answer) and transparently
    fall back to a plain call without it if the API rejects the parameter —
    so this never becomes a hard dependency on an uncertain API surface.
    We do NOT rely on any particular reasoning_format for correctness: the
    caller (issue_analyzer._extract_json) is written to handle reasoning
    content whether or not it leaks into `message.content`.
    """
    client = get_client()
    base_kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    try:
        response = client.chat.completions.create(reasoning_effort=reasoning_effort, **base_kwargs)
    except Exception as e:
        # Defensive fallback: some Groq API versions/models may reject
        # reasoning_effort outright. Retry once without it rather than
        # failing the whole call over an optional optimization.
        if "reasoning_effort" in str(e).lower() or "unknown" in str(e).lower() or "unsupported" in str(e).lower():
            response = client.chat.completions.create(**base_kwargs)
        else:
            raise

    choice = response.choices[0]
    finish_reason = getattr(choice, "finish_reason", None)
    content = choice.message.content

    if finish_reason == "length":
        preview = (content or "")[:200]
        raise LLMTruncatedError(
            f"Response truncated at max_tokens={max_tokens} (finish_reason='length') — "
            f"the model did not finish before running out of budget. This is the most "
            f"likely root cause if you're seeing 'No JSON object found' downstream: the "
            f"JSON object was cut off mid-way and never closed. Increase max_tokens for "
            f"this call. Partial content received: {preview!r}"
        )

    return content

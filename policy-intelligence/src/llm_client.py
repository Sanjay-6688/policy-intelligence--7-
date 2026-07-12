"""
llm_client.py
--------------
Unified LLM client abstraction for the Policy Intelligence pipeline.

Design goal: the SAME pipeline code should run in two modes without any
branching at the call site:

  1. LIVE MODE   - a real LLM (Anthropic or OpenAI) is used for obligation
                   extraction and relationship classification, exactly as
                   described in "Option A: LLM-Powered Policy Intelligence".
  2. OFFLINE MODE - no API key is configured. A deterministic, rule-based
                   stand-in produces structurally identical JSON output so
                   the full system (extraction -> similarity -> graph ->
                   dashboard) is runnable end-to-end for demos, grading,
                   and CI, with zero external dependencies or cost.

Set ANTHROPIC_API_KEY or OPENAI_API_KEY in the environment to switch to
LIVE MODE automatically. See README.md for details.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Optional


class LLMError(Exception):
    pass


@dataclass
class LLMResponse:
    text: str
    mode: str  # "live" or "offline"


class LLMClient:
    """Thin wrapper that picks a backend based on available credentials."""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.groq_key = os.environ.get("GROQ_API_KEY")

        if provider:
            self.provider = provider
        elif self.groq_key:
            self.provider = "groq"
        elif self.anthropic_key:
            self.provider = "anthropic"
        elif self.openai_key:
            self.provider = "openai"
        elif self.gemini_key:
            self.provider = "gemini"
        else:
            self.provider = "offline"

        self.model = model or (
            "claude-sonnet-4-6" if self.provider == "anthropic" else
            "gpt-4o-mini" if self.provider == "openai" else
            os.environ.get("GEMINI_MODEL", "gemini-2.0-flash") if self.provider == "gemini" else
            os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile") if self.provider == "groq" else
            "offline-heuristic-v1"
        )

    @property
    def is_live(self) -> bool:
        return self.provider in ("anthropic", "openai", "gemini", "groq")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def complete_json(self, system: str, user: str, max_tokens: int = 1024) -> dict:
        """
        Send a prompt that MUST return a single JSON object/array, and parse it.
        Falls back to raising LLMError if the live provider fails; callers
        should catch this and decide whether to retry or degrade gracefully.
        """
        if self.provider == "anthropic":
            raw = self._call_anthropic(system, user, max_tokens)
        elif self.provider == "openai":
            raw = self._call_openai(system, user, max_tokens)
        elif self.provider == "gemini":
            raw = self._call_gemini(system, user, max_tokens)
            # Gemini's free tier is rate-limited per minute (commonly ~10 RPM
            # for Flash-class models). Pace requests so a full pipeline run
            # (extraction + classification = dozens of calls) doesn't hit 429s.
            import time
            time.sleep(9)
        elif self.provider == "groq":
            raw = self._call_groq(system, user, max_tokens)
            # Groq's free tier is generous (30 RPM / 14,400 RPD) but still
            # finite -- a small pace keeps a ~25-call pipeline run comfortably
            # under the per-minute cap.
            import time
            time.sleep(2.2)
        else:
            raise LLMError("complete_json() called in offline mode; use the "
                            "dedicated offline heuristics in extraction.py / "
                            "classifier.py instead.")
        return self._parse_json(raw)

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------
    def _call_anthropic(self, system: str, user: str, max_tokens: int) -> str:
        try:
            import anthropic
        except ImportError as e:
            raise LLMError(
                "The 'anthropic' package is not installed. Run "
                "`pip install anthropic` or unset ANTHROPIC_API_KEY to use "
                "offline mode."
            ) from e
        client = anthropic.Anthropic(api_key=self.anthropic_key)
        resp = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    def _call_openai(self, system: str, user: str, max_tokens: int) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise LLMError(
                "The 'openai' package is not installed. Run "
                "`pip install openai` or unset OPENAI_API_KEY to use "
                "offline mode."
            ) from e
        client = OpenAI(api_key=self.openai_key)
        resp = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""

    def _call_gemini(self, system: str, user: str, max_tokens: int) -> str:
        """
        Calls the Gemini API's free tier via plain HTTP (stdlib urllib only --
        no SDK install required). See https://ai.google.dev for the free
        tier: create a key at https://aistudio.google.com, no credit card
        needed, and set it as GEMINI_API_KEY (or GOOGLE_API_KEY).

        Retries on rate limits (429) AND on transient network errors
        (timeouts, connection resets) -- both are common on the free tier,
        which can be flaky under load. Every failure path raises LLMError so
        callers (extraction.py / classifier.py) can gracefully fall back to
        the offline heuristic instead of crashing the whole pipeline.
        """
        import urllib.request
        import urllib.error
        import socket
        import time

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        body = json.dumps({
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        }).encode("utf-8")

        def make_request():
            return urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.gemini_key,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "PolicyGovernanceIntelligence/1.0",
                },
                method="POST",
            )

        max_attempts = 3
        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                with urllib.request.urlopen(make_request(), timeout=45) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                last_error = None
                break
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                last_error = LLMError(f"Gemini API error {e.code}: {err_body[:400]}")
                if e.code == 429 and attempt < max_attempts:
                    wait = 20 * attempt
                    print(f"\n  [gemini] rate limited (429), waiting {wait}s before retry "
                          f"{attempt}/{max_attempts - 1}...", end=" ", flush=True)
                    time.sleep(wait)
                    continue
                raise last_error from e
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as e:
                # Transient network issue (timeout, DNS hiccup, reset, etc.)
                last_error = LLMError(f"Gemini API network error: {e}")
                if attempt < max_attempts:
                    wait = 8 * attempt
                    print(f"\n  [gemini] network error, waiting {wait}s before retry "
                          f"{attempt}/{max_attempts - 1}...", end=" ", flush=True)
                    time.sleep(wait)
                    continue
                raise last_error from e

        if last_error is not None:
            raise last_error

        try:
            candidates = data.get("candidates", [])
            if not candidates:
                # Common cause: the free-tier daily/per-minute quota was hit,
                # or the prompt was blocked by safety filters.
                reason = data.get("promptFeedback", {}).get("blockReason", "unknown")
                raise LLMError(f"Gemini returned no candidates (reason: {reason}). Raw: {data}")
            parts = candidates[0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError) as e:
            raise LLMError(f"Unexpected Gemini response shape: {data}") from e

    def _call_groq(self, system: str, user: str, max_tokens: int) -> str:
        """
        Calls Groq's free tier via plain HTTP (stdlib urllib only -- no SDK
        install required). Groq's endpoint is OpenAI-compatible. Free tier:
        no credit card, no expiration, rate-limited only (commonly ~30 RPM /
        14,400 requests per day depending on model). Get a key at
        https://console.groq.com/keys and set GROQ_API_KEY.
        """
        import urllib.request
        import urllib.error
        import socket
        import time

        url = "https://api.groq.com/openai/v1/chat/completions"
        body = json.dumps({
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }).encode("utf-8")

        def make_request():
            return urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.groq_key}",
                    "Accept": "application/json",
                    # Groq's API sits behind Cloudflare, which blocks requests
                    # carrying Python's default "Python-urllib/3.x" User-Agent
                    # as a bot signature (HTTP 403, Cloudflare error 1010).
                    # A normal-looking User-Agent avoids that entirely.
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "PolicyGovernanceIntelligence/1.0",
                },
                method="POST",
            )

        max_attempts = 3
        last_error = None
        data = None
        for attempt in range(1, max_attempts + 1):
            try:
                with urllib.request.urlopen(make_request(), timeout=45) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                last_error = None
                break
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                last_error = LLMError(f"Groq API error {e.code}: {err_body[:400]}")
                if e.code == 429 and attempt < max_attempts:
                    wait = 15 * attempt
                    print(f"\n  [groq] rate limited (429), waiting {wait}s before retry "
                          f"{attempt}/{max_attempts - 1}...", end=" ", flush=True)
                    time.sleep(wait)
                    continue
                raise last_error from e
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as e:
                last_error = LLMError(f"Groq API network error: {e}")
                if attempt < max_attempts:
                    wait = 8 * attempt
                    print(f"\n  [groq] network error, waiting {wait}s before retry "
                          f"{attempt}/{max_attempts - 1}...", end=" ", flush=True)
                    time.sleep(wait)
                    continue
                raise last_error from e

        if last_error is not None:
            raise last_error

        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as e:
            raise LLMError(f"Unexpected Groq response shape: {data}") from e

    @staticmethod
    def _parse_json(raw: str) -> Any:
        # Strip markdown code fences if the model added them despite instructions.
        cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            # last resort: grab the largest {...} or [...] span. This can
            # ALSO fail (e.g. the response was truncated mid-string because
            # it hit max_tokens) -- every failure path here must raise
            # LLMError specifically, never let a raw JSONDecodeError escape,
            # or callers' `except LLMError` graceful-fallback never triggers.
            match = re.search(r"(\{.*\}|\[.*\])", cleaned, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError as e2:
                    raise LLMError(
                        f"Could not parse JSON from LLM response even after fence-stripping "
                        f"(likely truncated by max_tokens): {e2}\nRaw (first 500 chars): {raw[:500]}"
                    ) from e2
            raise LLMError(f"Could not parse JSON from LLM response: {e}\nRaw: {raw[:500]}")

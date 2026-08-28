"""
Thin wrapper around the Anthropic SDK used by every agent in the pipeline.

Every agent call in HireLens must be:
  1. Independent (no shared conversation state between agents)
  2. Grounded (forced to quote resume/transcript text)
  3. Structured (returns clean JSON we can validate with pydantic)

This module centralises those concerns so agents.py / debate.py / judge.py
stay short and readable.
"""

import json
import re
from typing import Any, Dict, Optional

from groq import Groq

from app.config import GROQ_API_KEY, GROQ_MODEL

_client: Optional[Groq] = None


def get_client() -> Groq:
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"```$", "", text.strip())
    return text.strip()


def _extract_json_block(text: str) -> str:
    text = text.strip()

    # Remove Qwen thinking blocks if they somehow appear
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove markdown fences
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")
    text = text.strip()

    # First try the entire response
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # Find the first balanced JSON object
    start = text.find("{")

    while start != -1:
        depth = 0
        in_string = False
        escaped = False

        for i in range(start, len(text)):
            ch = text[i]

            if escaped:
                escaped = False
                continue

            if ch == "\\" and in_string:
                escaped = True
                continue

            if ch == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1

                if depth == 0:
                    candidate = text[start:i + 1]

                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        break

        start = text.find("{", start + 1)

    # Also support a top-level JSON array
    start = text.find("[")

    while start != -1:
        depth = 0
        in_string = False
        escaped = False

        for i in range(start, len(text)):
            ch = text[i]

            if escaped:
                escaped = False
                continue

            if ch == "\\" and in_string:
                escaped = True
                continue

            if ch == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1

                if depth == 0:
                    candidate = text[start:i + 1]

                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        break

        start = text.find("[", start + 1)

    raise ValueError(
        "Could not extract valid JSON from model response: "
        + text[:3000]
    )
def call_llm_json(
    system: str,
    user: str,
    max_tokens: int = 1000,
    temperature: float = 0.4,
    model: Optional[str] = None,
) -> Dict[str, Any]:

    client = get_client()

    system_full = (
        system.strip()
        + "\n\n"
        "CRITICAL OUTPUT RULE: Return ONLY one valid JSON object. "
        "No markdown fences. No preamble. No explanation. "
        "Do not output <think> tags."
    )

    last_err: Optional[Exception] = None

    for attempt in range(2):

        response = client.chat.completions.create(
            model=model or GROQ_MODEL,
            max_completion_tokens=max_tokens,
            temperature=0.0,
            reasoning_format="hidden",
            reasoning_effort="none",
            messages=[
                {
                    "role": "system",
                    "content": system_full,
                },
                {
                    "role": "user",
                    "content": user,
                },
            ],
        )

        raw_text = response.choices[0].message.content or ""

        try:
            json_str = _extract_json_block(raw_text)
            return json.loads(json_str)

        except (ValueError, json.JSONDecodeError) as e:
            last_err = e

            if attempt == 0:
                user = (
                    "Return ONLY one valid JSON object. "
                    "No markdown. No explanation. "
                    "No <think> tags. "
                    "The response must begin with { and end with }.\n\n"
                    + user
                )

                continue

    raise RuntimeError(
        f"LLM did not return parseable JSON after retries: {last_err}"
    )

"""
Step 3: Debate

After all four agents have given independent opinions (base.py guarantees they
never saw each other's output while forming those), we now show every opinion
to a single "debate orchestrator" call whose job is to simulate the panel
actually talking to each other: agreeing, disagreeing, and revising views
based on each other's specific evidence.

We deliberately do this as ONE structured LLM call (rather than many small
turn-by-turn calls) to keep hackathon latency/cost sane, but we FORCE the
model to produce multiple turns where a named agent responds directly to
another named agent's specific point — that's the actual requirement, and a
single call is perfectly capable of producing genuine cross-talk as long as
we require citations back to a specific other agent + their point.
"""

from typing import List

from app.llm_client import call_llm_json
from app.models import AgentOpinion, CandidateProfile, DebateResult, DebateTurn, RevisedOpinion

SYSTEM_PROMPT = """You are the DEBATE ORCHESTRATOR for HireLens, an AI hiring panel.

Four independent evaluators (Technical Agent, HR / Culture Agent, Hiring Manager Agent,
Skeptic Agent) have each already given their own opinion on a candidate, without seeing
each other's opinions. Your job is to run a realistic panel debate between them.

Rules for the debate you generate:
1. Produce at least 5 turns, alternating between different agents.
2. At LEAST TWO turns must have an agent directly responding to a SPECIFIC other agent's
   point (referencing that agent by name and referencing the actual point/quote they made) —
   either agreeing with it, disagreeing with it, or saying it changes their own view.
3. At least ONE agent must actually change its score/confidence because of something another
   agent said, and you must explain why in that agent's revised_opinions entry.
4. Debate turns must stay grounded — when an agent challenges another, it must reference the
   OTHER agent's specific point or quote, not a vague generality.
5. If, after the debate, some disagreement is NOT resolved (agents still meaningfully disagree
   after discussing it), list it explicitly in unresolved_disagreements. It's fine and
   expected to have at least one unresolved disagreement — real panels rarely agree on
   everything.
"""

USER_TEMPLATE = """Here are the four independent opinions on candidate "{name}" (target role: {role}).
Remember: these were formed independently; this is the FIRST time these agents are seeing
each other's views.

{opinions_block}

Now simulate the debate and return JSON with EXACTLY these keys:
{{
  "transcript": [
    {{
      "speaker": "Technical Agent" | "HR / Culture Agent" | "Hiring Manager Agent" | "Skeptic Agent",
      "addressed_to": "name of another agent this turn is responding to, or null for an opening statement",
      "stance": "agree" | "disagree" | "revise" | "clarify" | "challenge",
      "message": "what this agent says in this turn, specific and grounded, 1-3 sentences",
      "referenced_quote": "if this turn references a specific quote/point from another agent's opinion, put it here, else null"
    }}
  ],
  "revised_opinions": [
    {{
      "agent_name": "one of the four agent names",
      "original_score": integer,
      "revised_score": integer,
      "revised_confidence": integer,
      "changed": true/false,
      "change_reason": "why the score changed (or empty string if unchanged)"
    }}
  ],
  "unresolved_disagreements": ["short description of any disagreement that persisted after debate"]
}}

Include a revised_opinions entry for ALL FOUR agents (even if unchanged, set changed=false and
revised_score = original_score).
"""


def _format_opinion(op: AgentOpinion) -> str:
    strengths = "\n".join(f'    + [{s.source}] "{s.quote}" -> {s.point}' for s in op.strengths) or "    (none)"
    concerns = "\n".join(f'    - [{c.source}] "{c.quote}" -> {c.point}' for c in op.concerns) or "    (none)"
    return f"""### {op.agent_name} ({op.role})
  Score: {op.score}/100 | Confidence: {op.confidence}/100
  Verdict: {op.verdict}
  Reasoning: {op.reasoning}
  Strengths cited:
{strengths}
  Concerns cited:
{concerns}
"""


def run_debate(profile: CandidateProfile, opinions: List[AgentOpinion]) -> DebateResult:
    opinions_block = "\n".join(_format_opinion(op) for op in opinions)
    user = USER_TEMPLATE.format(
        name=profile.name,
        role=profile.target_role or "(role not specified)",
        opinions_block=opinions_block,
    )

    data = call_llm_json(SYSTEM_PROMPT, user, max_tokens=2500, temperature=0.6)

    transcript = [
        DebateTurn(
            speaker=t.get("speaker", ""),
            addressed_to=t.get("addressed_to"),
            stance=t.get("stance", "clarify"),
            message=t.get("message", ""),
            referenced_quote=t.get("referenced_quote"),
        )
        for t in data.get("transcript", [])
    ]

    revised = [
        RevisedOpinion(
            agent_name=r.get("agent_name", ""),
            original_score=int(r.get("original_score", 0)),
            revised_score=int(r.get("revised_score", r.get("original_score", 0))),
            revised_confidence=int(r.get("revised_confidence", 0)),
            changed=bool(r.get("changed", False)),
            change_reason=r.get("change_reason", ""),
        )
        for r in data.get("revised_opinions", [])
    ]

    return DebateResult(
        transcript=transcript,
        revised_opinions=revised,
        unresolved_disagreements=data.get("unresolved_disagreements", []) or [],
    )

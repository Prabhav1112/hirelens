"""
Step 4: Final Judge

Takes the independent opinions + the debate outcome and produces a final
decision. This is explicitly NOT a simple average of the four scores — the
judge must decide how much weight each agent's evidence deserves for THIS
candidate/role, and explain that weighting. E.g. if the Skeptic surfaced a
serious unresolved contradiction, that should be able to override an
otherwise-strong average even if it's a minority opinion.
"""

from typing import List

from app.llm_client import call_llm_json
from app.models import AgentOpinion, CandidateProfile, DebateResult, FinalDecision, AgentWeight

SYSTEM_PROMPT = """You are the FINAL JUDGE on the HireLens AI hiring panel — a senior decision-maker
who reviews everything the panel produced and makes the final call.

You do NOT simply average the four agents' scores. Instead you:
1. Decide how much WEIGHT each agent's evidence deserves for this specific candidate and role
   (weights should sum to roughly 1.0). Justify each weight with a concrete reason — e.g. "Skeptic
   gets extra weight because it surfaced an unresolved contradiction between resume and transcript
   that materially affects trust", or "Technical Agent gets more weight because this is a
   technical-heavy role".
2. Use those weights plus the POST-DEBATE revised scores (not the original independent scores) to
   compute a weighted_score (0-100).
3. Explicitly account for unresolved disagreements from the debate — an unresolved red flag from
   the Skeptic should be able to cap the recommendation even if the weighted number looks decent.
4. Choose a final recommendation from: "Strong Hire", "Hire", "Lean Hire", "No Hire", "Strong No Hire".
5. Give a confidence_level (0-100) for your own final decision — this may differ from any single
   agent's confidence, and should be LOWER if agents disagree a lot or evidence is thin.
6. Write clear reasoning (4-8 sentences) that a human recruiter could read and understand exactly
   WHY this decision was reached, referencing specific evidence, not vague generalities.
"""

USER_TEMPLATE = """CANDIDATE: {name} — target role: {role}

=== POST-DEBATE STATE OF EACH AGENT ===
{agents_block}

=== DEBATE TRANSCRIPT ===
{debate_block}

=== UNRESOLVED DISAGREEMENTS AFTER DEBATE ===
{unresolved_block}

Return JSON with EXACTLY these keys:
{{
  "recommendation": "Strong Hire" | "Hire" | "Lean Hire" | "No Hire" | "Strong No Hire",
  "confidence_level": integer 0-100,
  "weighted_score": number 0-100,
  "agent_weights": [
    {{"agent_name": string, "weight": number between 0 and 1, "justification": string}}
  ],
  "reasoning": "4-8 sentences explaining the final decision, citing specific evidence"
}}

The four agent_weights entries should sum to approximately 1.0.
"""


def _revised_lookup(debate: DebateResult):
    return {r.agent_name: r for r in debate.revised_opinions}


def _format_agents_block(opinions: List[AgentOpinion], debate: DebateResult) -> str:
    revised = _revised_lookup(debate)
    lines = []
    for op in opinions:
        r = revised.get(op.agent_name)
        post_score = r.revised_score if r else op.score
        post_conf = r.revised_confidence if r else op.confidence
        changed_note = f" (CHANGED during debate: {r.change_reason})" if r and r.changed else ""
        lines.append(
            f"- {op.agent_name}: independent score {op.score} -> post-debate score {post_score}, "
            f"confidence {post_conf}.{changed_note}\n"
            f"  Verdict: {op.verdict}\n"
            f"  Key strengths: {', '.join(s.point for s in op.strengths) or 'none'}\n"
            f"  Key concerns: {', '.join(c.point for c in op.concerns) or 'none'}"
        )
    return "\n".join(lines)


def _format_debate_block(debate: DebateResult) -> str:
    lines = []
    for t in debate.transcript:
        addressed = f" -> {t.addressed_to}" if t.addressed_to else ""
        lines.append(f"[{t.speaker}{addressed}] ({t.stance}): {t.message}")
    return "\n".join(lines) or "(no debate transcript)"


def run_final_judge(
    profile: CandidateProfile,
    opinions: List[AgentOpinion],
    debate: DebateResult,
) -> FinalDecision:
    user = USER_TEMPLATE.format(
        name=profile.name,
        role=profile.target_role or "(role not specified)",
        agents_block=_format_agents_block(opinions, debate),
        debate_block=_format_debate_block(debate),
        unresolved_block="\n".join(f"- {u}" for u in debate.unresolved_disagreements) or "(none)",
    )

    data = call_llm_json(SYSTEM_PROMPT, user, max_tokens=1500, temperature=0.3)

    weights = [
        AgentWeight(
            agent_name=w.get("agent_name", ""),
            weight=float(w.get("weight", 0.25)),
            justification=w.get("justification", ""),
        )
        for w in data.get("agent_weights", [])
    ]

    return FinalDecision(
        recommendation=data.get("recommendation", "Lean Hire"),
        confidence_level=int(data.get("confidence_level", 50)),
        weighted_score=float(data.get("weighted_score", 50)),
        agent_weights=weights,
        reasoning=data.get("reasoning", ""),
    )

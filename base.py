"""
Shared machinery for the four independent agents.

IMPORTANT ISOLATION GUARANTEE:
Each agent call below is a brand-new, independent LLM request. Agents never
see each other's opinions here — this module has no notion of the other
agents at all. That isolation is what makes the later debate stage meaningful.
"""

from app.llm_client import call_llm_json
from app.models import AgentOpinion, CandidateProfile, Evidence

OUTPUT_SCHEMA_INSTRUCTIONS = """Return JSON with EXACTLY these keys:
{
  "score": integer 0-100,
  "confidence": integer 0-100,
  "verdict": "one short sentence verdict",
  "strengths": [
    {"point": "short claim", "quote": "verbatim quote copied EXACTLY from the resume or transcript text given to you", "source": "resume" | "transcript"}
  ],
  "concerns": [
    {"point": "short claim", "quote": "verbatim quote copied EXACTLY from the resume or transcript text given to you", "source": "resume" | "transcript"}
  ],
  "reasoning": "2-4 sentences explaining how the evidence led to your score"
}

RULES:
- Every strength and every concern MUST include a real "quote" copied verbatim (word-for-word)
  from the RESUME or TRANSCRIPT text you were given. Never fabricate a quote.
- If you cannot find textual evidence for a point, do not include that point.
- Provide at least 1 strength and at least 1 concern if the evidence supports it. It is fine
  to have zero concerns only if the evidence is genuinely spotless.
- Do not reference or assume the opinions of any other evaluator — you have not seen them.
"""


def build_evidence_context(profile: CandidateProfile) -> str:
    return f"""JOB DESCRIPTION / TARGET ROLE:
{profile.raw_job_description or profile.target_role or "(not specified)"}

CANDIDATE PROFILE (extracted facts, for orientation only — always cite the RAW text below, not this summary):
- Name: {profile.name}
- Skills: {", ".join(profile.skills) or "(none extracted)"}
- Years of experience: {profile.years_experience or "unknown"}
- Education: {"; ".join(profile.education) or "(none extracted)"}
- Work history: {"; ".join(profile.work_history) or "(none extracted)"}
- Key claims made by candidate: {"; ".join(c.claim for c in profile.key_claims) or "(none extracted)"}

=== RAW RESUME TEXT (quote from this) ===
{profile.raw_resume_text or "(not provided)"}

=== RAW INTERVIEW TRANSCRIPT (quote from this) ===
{profile.raw_transcript_text or "(not provided)"}
"""


def run_independent_agent(
    agent_name: str,
    role: str,
    persona_system_prompt: str,
    profile: CandidateProfile,
) -> AgentOpinion:
    system = f"{persona_system_prompt}\n\n{OUTPUT_SCHEMA_INSTRUCTIONS}"
    user = build_evidence_context(profile)

    data = call_llm_json(system, user, max_tokens=1600, temperature=0.4)

    strengths = [
        Evidence(
            point=s.get("point", ""),
            quote=s.get("quote", ""),
            source=s.get("source", "resume"),
        )
        for s in data.get("strengths", [])
        if s.get("quote")
    ]
    concerns = [
        Evidence(
            point=c.get("point", ""),
            quote=c.get("quote", ""),
            source=c.get("source", "resume"),
        )
        for c in data.get("concerns", [])
        if c.get("quote")
    ]

    return AgentOpinion(
        agent_name=agent_name,
        role=role,
        score=int(data.get("score", 50)),
        confidence=int(data.get("confidence", 50)),
        verdict=data.get("verdict", ""),
        strengths=strengths,
        concerns=concerns,
        reasoning=data.get("reasoning", ""),
    )

"""
Step 5: Final Report

Pure assembly step (no LLM call needed) - stitches together everything the
pipeline produced into the FinalReport shape the frontend consumes.
"""

from typing import List, Optional

from app.models import (
    AgentOpinion,
    CandidateProfile,
    DebateResult,
    FinalDecision,
    FinalReport,
)


def build_final_report(
    profile: CandidateProfile,
    opinions: List[AgentOpinion],
    debate: DebateResult,
    decision: FinalDecision,
    voice_debate_url: Optional[str] = None,
) -> FinalReport:
    strengths_summary = []
    concerns_summary = []
    for op in opinions:
        for s in op.strengths:
            strengths_summary.append(f"[{op.agent_name}] {s.point}")
        for c in op.concerns:
            concerns_summary.append(f"[{op.agent_name}] {c.point}")

    return FinalReport(
        candidate_profile=profile,
        independent_opinions=opinions,
        debate=debate,
        final_decision=decision,
        strengths_summary=strengths_summary,
        concerns_summary=concerns_summary,
        unresolved_disagreements=debate.unresolved_disagreements,
        voice_debate_url=voice_debate_url,
    )

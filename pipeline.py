"""
Orchestrates the full HireLens flow end to end:

  Candidate Inputs
      -> Candidate Profile Builder
      -> 4 independent agents (parallel, isolated LLM calls)
      -> Debate
      -> Final Judge
      -> Final Report (+ optional bonus voice debate)
"""

import asyncio
import logging
from typing import Optional

from app.agents import ALL_AGENT_RUNNERS
from app.debate import run_debate
from app.judge import run_final_judge
from app.models import FinalReport
from app.profile_builder import build_candidate_profile
from app.report import build_final_report
from app.voice import synthesize_debate_audio

logger = logging.getLogger("hirelens.pipeline")


async def run_full_pipeline(
    resume_text: str,
    transcript_text: str,
    job_description: str = "",
    target_role: str = "",
    generate_voice: bool = False,
) -> FinalReport:
    # --- 1. Candidate Profile Builder -------------------------------------
    profile = await asyncio.to_thread(
        build_candidate_profile, resume_text, transcript_text, job_description, target_role
    )
    logger.info("Profile built for %s", profile.name)

    # --- 2. Four independent agents, run truly in parallel -----------------
    # Each runner is a fresh, isolated LLM call (see agents/base.py) — none of
    # them receive any other agent's output.
    opinions = await asyncio.gather(
        *(asyncio.to_thread(runner, profile) for runner in ALL_AGENT_RUNNERS)
    )
    opinions = list(opinions)
    logger.info("Collected %d independent opinions", len(opinions))

    # --- 3. Debate -----------------------------------------------------------
    debate = await asyncio.to_thread(run_debate, profile, opinions)
    logger.info("Debate complete: %d turns", len(debate.transcript))

    # --- 4. Final Judge (weighted reasoning, not averaging) ------------------
    decision = await asyncio.to_thread(run_final_judge, profile, opinions, debate)
    logger.info("Final decision: %s (%.1f)", decision.recommendation, decision.weighted_score)

    # --- Bonus: voice debate --------------------------------------------------
    voice_url: Optional[str] = None
    if generate_voice:
        voice_path = await asyncio.to_thread(synthesize_debate_audio, debate, profile.name)
        if voice_path:
            import os

            voice_url = f"/api/audio/{os.path.basename(voice_path)}"

    # --- 5. Final Report -------------------------------------------------------
    report = build_final_report(profile, opinions, debate, decision, voice_debate_url=voice_url)
    return report

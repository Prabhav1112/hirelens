"""
Step 1: Candidate Profile Builder

Reads the raw resume + interview transcript (+ optional job description) and
extracts the shared factual baseline every agent will work from: skills,
experience, education, work history, and explicit "claims" made by the
candidate (things they say about themselves that agents may later verify,
support, or challenge).

This is a single LLM call — it does NOT judge the candidate, it only extracts
facts. Judgement happens in the agent stage.
"""

from app.llm_client import call_llm_json
from app.models import CandidateClaim, CandidateProfile

SYSTEM_PROMPT = """You are a meticulous data-extraction engine for a hiring platform called HireLens.
Your ONLY job is to extract structured facts from a candidate's resume and interview transcript.
Do NOT evaluate, score, or judge the candidate. Do NOT invent information that isn't present.
If something isn't stated, leave it empty or null rather than guessing.

Extract:
- name (if findable, else "Unknown Candidate")
- skills: a flat list of concrete technical/soft skills explicitly mentioned
- years_experience: a short string like "4 years" if it can be inferred, else null
- education: list of degrees/institutions mentioned
- work_history: list of short strings like "Company X - Role - Duration"
- key_claims: a list of specific claims the candidate makes about themselves
  (accomplishments, ownership of projects, metrics, leadership, etc.), each tagged
  with source "resume" or "transcript"
- summary: a neutral 2-3 sentence factual summary (no opinions/judgement)
"""

USER_TEMPLATE = """JOB DESCRIPTION (context only, may be empty):
{job_description}

RESUME:
{resume}

INTERVIEW TRANSCRIPT:
{transcript}

Return JSON with EXACTLY these keys:
{{
  "name": string,
  "skills": [string],
  "years_experience": string or null,
  "education": [string],
  "work_history": [string],
  "key_claims": [{{"claim": string, "source": "resume" | "transcript"}}],
  "summary": string
}}
"""


def build_candidate_profile(
    resume_text: str,
    transcript_text: str,
    job_description: str = "",
    target_role: str = "",
) -> CandidateProfile:
    user_prompt = USER_TEMPLATE.format(
        job_description=job_description or "(none provided)",
        resume=resume_text or "(none provided)",
        transcript=transcript_text or "(none provided)",
    )

    data = call_llm_json(SYSTEM_PROMPT, user_prompt, max_tokens=2000, temperature=0.2)

    # Groq may return a JSON list instead of the expected object
    if isinstance(data, list):
        data = data[0] if data and isinstance(data[0], dict) else {}

    if not isinstance(data, dict):
        data = {}

    claims = [
        CandidateClaim(
            claim=c.get("claim", ""),
            source=c.get("source", "resume")
        )
        for c in data.get("key_claims", [])
        if isinstance(c, dict) and c.get("claim")
    ]

    return CandidateProfile(
        name=data.get("name") or "Unknown Candidate",
        target_role=target_role or None,
        skills=data.get("skills", []) or [],
        years_experience=data.get("years_experience"),
        education=data.get("education", []) or [],
        work_history=data.get("work_history", []) or [],
        key_claims=claims,
        summary=data.get("summary", ""),
        raw_resume_text=resume_text,
        raw_transcript_text=transcript_text,
        raw_job_description=job_description,
    )

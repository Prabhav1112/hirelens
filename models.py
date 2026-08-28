from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Candidate Profile
# ---------------------------------------------------------------------------

class CandidateClaim(BaseModel):
    claim: str
    source: str  # "resume" | "transcript"


class CandidateProfile(BaseModel):
    name: Optional[str] = "Unknown Candidate"
    target_role: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    years_experience: Optional[str] = None
    education: List[str] = Field(default_factory=list)
    work_history: List[str] = Field(default_factory=list)
    key_claims: List[CandidateClaim] = Field(default_factory=list)
    summary: str = ""
    # Raw source text is kept so every downstream agent can quote directly
    raw_resume_text: str = ""
    raw_transcript_text: str = ""
    raw_job_description: str = ""


# ---------------------------------------------------------------------------
# Agent Opinions (independent stage)
# ---------------------------------------------------------------------------

class Evidence(BaseModel):
    point: str
    quote: str  # verbatim quote copied from resume/transcript
    source: str  # "resume" | "transcript" | "job_description"


class AgentOpinion(BaseModel):
    agent_name: str
    role: str
    score: int  # 0-100
    confidence: int  # 0-100
    verdict: str  # one-line verdict
    strengths: List[Evidence] = Field(default_factory=list)
    concerns: List[Evidence] = Field(default_factory=list)
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Debate stage
# ---------------------------------------------------------------------------

class DebateTurn(BaseModel):
    speaker: str
    addressed_to: Optional[str] = None
    stance: str  # "agree" | "disagree" | "revise" | "clarify" | "challenge"
    message: str
    referenced_quote: Optional[str] = None


class RevisedOpinion(BaseModel):
    agent_name: str
    original_score: int
    revised_score: int
    revised_confidence: int
    changed: bool
    change_reason: str = ""


class DebateResult(BaseModel):
    transcript: List[DebateTurn] = Field(default_factory=list)
    revised_opinions: List[RevisedOpinion] = Field(default_factory=list)
    unresolved_disagreements: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Final Judge / Decision
# ---------------------------------------------------------------------------

class AgentWeight(BaseModel):
    agent_name: str
    weight: float  # 0-1, weights sum ~1.0
    justification: str


class FinalDecision(BaseModel):
    recommendation: str  # "Strong Hire" | "Hire" | "Lean Hire" | "No Hire" | "Strong No Hire"
    confidence_level: int  # 0-100
    weighted_score: float  # 0-100
    agent_weights: List[AgentWeight] = Field(default_factory=list)
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Final Report (the API's top-level response)
# ---------------------------------------------------------------------------

class FinalReport(BaseModel):
    candidate_profile: CandidateProfile
    independent_opinions: List[AgentOpinion]
    debate: DebateResult
    final_decision: FinalDecision
    strengths_summary: List[str] = Field(default_factory=list)
    concerns_summary: List[str] = Field(default_factory=list)
    unresolved_disagreements: List[str] = Field(default_factory=list)
    voice_debate_url: Optional[str] = None

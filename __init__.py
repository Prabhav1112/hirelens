from app.agents.technical import run_technical_agent
from app.agents.hr import run_hr_agent
from app.agents.hiring_manager import run_hiring_manager_agent
from app.agents.skeptic import run_skeptic_agent

ALL_AGENT_RUNNERS = [
    run_technical_agent,
    run_hr_agent,
    run_hiring_manager_agent,
    run_skeptic_agent,
]

__all__ = [
    "run_technical_agent",
    "run_hr_agent",
    "run_hiring_manager_agent",
    "run_skeptic_agent",
    "ALL_AGENT_RUNNERS",
]

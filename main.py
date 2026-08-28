import logging
import os
import traceback
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.config import CORS_ORIGINS, OUTPUT_DIR
from app.file_parser import extract_text, extract_text_from_bytes
from app.models import FinalReport
from app.pipeline import run_full_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hirelens.main")

app = FastAPI(
    title="HireLens API",
    description="Evidence-driven AI hiring panel: profile builder -> 4 independent agents -> debate -> final judge -> report.",
    version="1.0.0",
)

origins = ["*"] if CORS_ORIGINS.strip() == "*" else [o.strip() for o in CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "hirelens-backend"}


# ---------------------------------------------------------------------------
# Option A: multipart file upload (resume/transcript as actual files)
# ---------------------------------------------------------------------------

@app.post("/api/analyze", response_model=FinalReport)
async def analyze_files(
    resume: UploadFile = File(..., description="Resume file: .pdf, .docx, or .txt"),
    transcript: UploadFile = File(..., description="Interview transcript file: .pdf, .docx, or .txt"),
    job_description: Optional[str] = Form(None, description="Job description as plain text"),
    job_description_file: Optional[UploadFile] = File(None, description="Job description as a file instead of text"),
    target_role: Optional[str] = Form(None),
    generate_voice: bool = Form(False, description="If true, also synthesize a bonus voice debate mp3"),
):
    try:
        resume_text = await extract_text(resume)
        transcript_text = await extract_text(transcript)

        jd_text = job_description or ""
        if job_description_file is not None:
            jd_text = await extract_text(job_description_file) or jd_text

        if not resume_text.strip() or not transcript_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Both resume and transcript must contain extractable text.",
            )

        report = await run_full_pipeline(
            resume_text=resume_text,
            transcript_text=transcript_text,
            job_description=jd_text,
            target_role=target_role or "",
            generate_voice=generate_voice,
        )
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error("analyze_files failed: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")


# ---------------------------------------------------------------------------
# Option B: plain JSON with raw text (handy for a frontend that already has
# resume/transcript text, e.g. pasted into a textarea, or parsed client-side)
# ---------------------------------------------------------------------------

class AnalyzeTextRequest(BaseModel):
    resume_text: str
    transcript_text: str
    job_description: str = ""
    target_role: str = ""
    generate_voice: bool = False


@app.post("/api/analyze-text", response_model=FinalReport)
async def analyze_text(payload: AnalyzeTextRequest):
    try:
        if not payload.resume_text.strip() or not payload.transcript_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Both resume_text and transcript_text are required.",
            )

        report = await run_full_pipeline(
            resume_text=payload.resume_text,
            transcript_text=payload.transcript_text,
            job_description=payload.job_description,
            target_role=payload.target_role,
            generate_voice=payload.generate_voice,
        )
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error("analyze_text failed: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")


# ---------------------------------------------------------------------------
# Bonus: serve generated voice debate audio files
# ---------------------------------------------------------------------------

@app.get("/api/audio/{filename}")
def get_audio(filename: str):
    safe_name = os.path.basename(filename)
    filepath = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(filepath, media_type="audio/mpeg", filename=safe_name)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
    return JSONResponse(status_code=500, content={"detail": str(exc)})

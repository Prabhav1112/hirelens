import streamlit as st
import os

st.set_page_config(
    page_title="HireLens AI",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 HireLens AI")
st.caption("Evidence-Based Hiring")

st.header("New Candidate")

candidate_name = st.text_input(
    "Candidate name",
    placeholder="Auto-detected from resume"
)

target_role = st.text_input(
    "Target role",
    placeholder="e.g. Senior Backend Engineer"
)

job_description = st.text_area(
    "Job description",
    placeholder="Paste the job description here..."
)

resume = st.file_uploader(
    "Resume",
    type=["pdf", "docx", "txt"]
)

transcript = st.file_uploader(
    "Interview transcript",
    type=["pdf", "docx", "txt"]
)

generate_voice = st.checkbox(
    "Generate bonus voice debate audio"
)

if st.button("✨ Analyze Candidate", type="primary"):

    if resume is None:
        st.error("Please upload a resume.")
        st.stop()

    if transcript is None:
        st.error("Please upload an interview transcript.")
        st.stop()

    st.info("Analyzing candidate...")

    # Your HireLens pipeline will go here.
    st.success("Candidate analysis completed.")
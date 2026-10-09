import streamlit as st
import pandas as pd
from src.gmail_fetcher import fetch_job_emails
from src.rag_engine import ResumeRAG
from src.agent_system import analyze_email_with_agents

st.set_page_config(page_title="AI Job Mailbox Analyzer", page_icon="💼", layout="wide")

st.title("💼 AI Job Mailbox & Next Steps Tracker")
st.caption("Powered by AutoGen Multi-Agent AI, ChromaDB RAG, and Streamlit")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    if st.button("📥 Index Resume to ChromaDB"):
        with st.spinner("Indexing resume..."):
            rag = ResumeRAG()
            msg = rag.index_resume()
            st.success(msg)

    max_emails = st.slider("Number of emails to fetch", 5, 30, 10)
    fetch_btn = st.button("🔄 Sync & Analyze Mailbox", type="primary")

# Main Execution Flow
if fetch_btn:
    with st.spinner("Fetching emails from Gmail..."):
        emails = fetch_job_emails(max_results=max_emails)
        st.info(f"Fetched {len(emails)} relevant job emails after pre-filtering.")

    rag = ResumeRAG()
    results = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, em in enumerate(emails):
        current_num = idx + 1
        log_msg = f"Processing [{current_num}/{len(emails)}]: {em['subject'][:45]}..."
        
        print(f"\n[DEBUG] {log_msg}")
        status_text.text(log_msg)

        context = rag.query_resume(em["subject"] + " " + em["body"][:200])
        analysis = analyze_email_with_agents(em, context)
        
        # Only keep job-related entries
        if analysis.get("is_job_related", True):
            analysis["Date"] = em["date"]
            analysis["Subject"] = em["subject"]
            results.append(analysis)

        progress_bar.progress(current_num / len(emails))

    status_text.text("Processing complete!")
    st.session_state["analysis_results"] = results
    st.success("Analysis Complete!")

# Results Dashboard
if "analysis_results" in st.session_state and st.session_state["analysis_results"]:
    data = st.session_state["analysis_results"]
    df = pd.DataFrame(data)

    st.subheader("📊 Application Overview")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Job Applications", len(df))
    col2.metric("Action Required", len(df[df["status"].isin(["Action Required", "Assessment Sent"])]))
    col3.metric("Interviews", len(df[df["status"] == "Interview Scheduled"]))
    col4.metric("Offers", len(df[df["status"] == "Offer Received"]))
    col5.metric("Rejections", len(df[df["status"] == "Rejected"]))

    st.markdown("---")

    st.subheader("📌 Actionable Next Steps & Status")
    # Updated width='stretch' to fix Streamlit deprecation warning
    display_cols = [c for c in ["company", "job_title", "status", "next_steps", "summary", "Date"] if c in df.columns]
    st.dataframe(df[display_cols], width='stretch')

    st.subheader("🔍 Detailed Email Breakdown")
    for item in data:
        with st.expander(f"{item.get('company', 'Company')} - {item.get('job_title', 'Role')} ({item.get('status', 'Status')})"):
            st.write(f"**Subject:** {item.get('Subject', 'N/A')}")
            st.write(f"**Action Item / Next Steps:** {item.get('next_steps', 'None')}")
            st.write(f"**Summary:** {item.get('summary', 'N/A')}")
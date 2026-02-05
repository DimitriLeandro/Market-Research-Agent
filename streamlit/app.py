import streamlit as st
import subprocess
import sys
from pathlib import Path

# Import from local helper module
import helpers

st.set_page_config(layout="wide", page_title="Market Research Agent", page_icon="🤖")

# --- UI Components ---

def render_dynamic_report(data: dict):
    """
    Renders a single report based strictly on the 'sections' list structure.
    """
    # Identify the asset
    identifier = data.get("ticker", data.get("sector", "Unknown"))
    
    # Metrics
    sentiment = data.get("overall_sentiment", "N/A")
    score = data.get("sentiment_score", None)
    trend = data.get("price_trend", None)
    date_str = data.get("analysis_date", "-")
    
    emoji = helpers.get_sentiment_emoji(sentiment, score if score is not None else 0)
    
    # Collapsible Container
    label = f"{emoji} {identifier} | {sentiment}"
    
    with st.expander(label, expanded=False):
        # Header Metrics
        cols = st.columns(4)
        cols[0].metric("Sentiment", sentiment)
        if score is not None:
            cols[1].metric("Score", f"{score}")
        if trend:
            cols[2].metric("Trend", trend)
        cols[3].caption(f"Date: {date_str}")
        
        st.divider()
        
        # Dynamic Section Rendering
        sections = data.get("sections", [])
        
        if not sections:
            st.warning("No details available in report.")
        
        for section in sections:
            title = section.get("title", "Untitled Section")
            raw_content = section.get("content", "")
            sec_id = section.get("id", "")
            
            # Escape content to prevent Latex errors with currency
            content = helpers.escape_markdown_dollars(raw_content)
            
            # Styling based on section type
            if sec_id == "summary":
                st.subheader(f"📌 {title}")
                st.info(content)
            elif sec_id == "bull_thesis":
                st.subheader(f"🐂 {title}")
                st.markdown(content)
            elif sec_id == "bear_thesis":
                st.subheader(f"🐻 {title}")
                st.markdown(content)
            elif sec_id == "financials":
                st.subheader(f"📊 {title}")
                st.markdown(content)
            elif sec_id == "news":
                st.subheader(f"📰 {title}")
                st.markdown(content)
            else:
                # Generic fallback for future sections
                st.subheader(title)
                st.markdown(content)
            
            st.markdown("---")

def run_agent_process(test_mode: bool):
    """Executes the agent script using paths from helpers."""
    script_path = helpers.MAIN_SCRIPT_PATH
    
    if not script_path.exists():
        st.error(f"Critical Error: Agent script not found at {script_path}")
        return

    cmd = [sys.executable, str(script_path)]
    if test_mode:
        cmd.append("--test")
    
    mode_label = "TEST" if test_mode else "PRODUCTION"
    
    with st.spinner(f"Running Agent in {mode_label} mode..."):
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=str(helpers.PROJECT_ROOT)
            )
            
            if result.returncode == 0:
                st.success("Execution successful!")
                st.info("Refresh the page to view results.")
            else:
                st.error("Execution failed.")
                with st.expander("View Logs"):
                    st.code(result.stdout)
                    st.code(result.stderr)
        except Exception as e:
            st.error(f"Failed to launch process: {e}")

# --- Main Layout ---

st.title("Market Research Agent")

# Sidebar: Controls & Navigation
st.sidebar.header("Controls")

if st.sidebar.button("🚀 Run Full Cycle", type="primary"):
    run_agent_process(test_mode=False)

if st.sidebar.button("🧪 Run Test Mode"):
    run_agent_process(test_mode=True)

st.sidebar.markdown("---")

# Date Selection
available_dates = helpers.get_available_dates()

if not available_dates:
    st.warning("No research data found.")
    st.stop()

selected_date_str = st.sidebar.selectbox("Analysis Date", available_dates)
date_dir_path = helpers.get_dir_for_date(selected_date_str)

# Main Content Tabs
tab_stocks, tab_fiis, tab_sectors = st.tabs(["📈 Stocks", "🏢 Real Estate (FIIs)", "🏭 Sectors"])

# Render Stocks
with tab_stocks:
    reports = helpers.load_reports_by_category(date_dir_path, "stocks")
    if reports:
        for report in reports:
            render_dynamic_report(report)
    else:
        st.info("No Stock reports found for this date.")

# Render REITs (FIIs)
with tab_fiis:
    # Note: Folder name is 'reits' based on backend configuration
    reports = helpers.load_reports_by_category(date_dir_path, "reits")
    if reports:
        for report in reports:
            render_dynamic_report(report)
    else:
        st.info("No FII reports found for this date.")

# Render Sectors
with tab_sectors:
    reports = helpers.load_reports_by_category(date_dir_path, "sectors")
    if reports:
        for report in reports:
            render_dynamic_report(report)
    else:
        st.info("No Sector reports found for this date.")
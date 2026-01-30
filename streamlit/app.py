import streamlit as st
import subprocess
import sys
import time
from pathlib import Path

# Add local helpers - Use absolute resolve to be safe
current_file_path = Path(__file__).resolve()
current_dir = current_file_path.parent
sys.path.append(str(current_dir))

import helpers

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Market Research Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS STYLING (Strict Light Theme) ---
st.markdown("""
<style>
    /* Force Light Theme Backgrounds */
    .stApp {
        background-color: #FFFFFF;
        color: #000000;
    }
    
    /* Sidebar Background */
    section[data-testid="stSidebar"] {
        background-color: #F0F2F6;
    }
    
    /* Metrics Cards Styling (Light Mode) */
    .metric-card {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #E0E0E0;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Tabs Styling (Light Mode) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        display: flex; /* Garante comportamento flexível */
        width: 100%;   /* Garante que a lista ocupe tudo */
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 4px;
        padding-top: 10px;
        padding-bottom: 10px;
        color: #31333F;
        
        flex: 1;                 /* Faz a aba crescer para ocupar espaço igual */
        width: 100%;             /* Força largura total dentro da divisão flex */
        justify-content: center; /* Centraliza o texto horizontalmente */
        text-align: center;      /* Garante alinhamento do texto */
    }
    .stTabs [aria-selected="true"] {
        background-color: #E8F0FE;
        color: #1967D2;
        border-color: #1967D2;
    }
    
    /* Text Color Overrides */
    h1, h2, h3, h4, h5, h6, p, span {
        color: #31333F !important;
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: #FFFFFF;
        color: #31333F;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: CONTROLS ---
with st.sidebar:
    st.title("🤖 Agent Controls")
    
    # Run Button
    if st.button("🚀 Run Daily Analysis", use_container_width=True, type="primary"):
        with st.status("Running Market Agent...", expanded=False) as status:
            # PATH FIX: Determine absolute paths for execution
            project_root = current_dir.parent
            script_path = project_root / "market_agent" / "main.py"

            try:
                process = subprocess.Popen(
                    [sys.executable, str(script_path)], # Use absolute path
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    cwd=str(project_root) # Run from project root
                )
                process.wait()
                
                if process.returncode == 0:
                    status.update(label="Analysis Completed!", state="complete", expanded=False)
                    st.success("Data updated successfully.")
                    time.sleep(1)
                    st.rerun()
                else:
                    status.update(label="Analysis Failed", state="error", expanded=False)
                    st.error("The agent encountered an error. Please check server logs.")
            except Exception as e:
                status.update(label="Execution Error", state="error", expanded=False)
                st.error("Failed to start the analysis process.")

    st.divider()
    
    # Date Selection
    dates = helpers.get_available_dates()
    if not dates:
        st.warning("No data found.")
        selected_date_folder = None
    else:
        # Map friendly DD/MM/YYYY labels back to folder names
        date_map = {helpers.format_date_uk(d): d for d in dates}
        selected_label = st.selectbox("📅 Select Report Date", list(date_map.keys()), index=0)
        selected_date_folder = date_map[selected_label]

# --- MAIN CONTENT ---
if not selected_date_folder:
    st.info("Please run the agent to generate your first report.")
    st.stop()

# Display formatted date in title
formatted_title_date = helpers.format_date_uk(selected_date_folder)
st.title(f"📊 Market Research Report: {formatted_title_date}")

# Load Data
report_data = helpers.load_report_data(selected_date_folder)
equities = report_data["equity"]
fiis = report_data["fii"]

# Summary Metrics
col1, col2, col3 = st.columns(3)
total_assets = len(equities) + len(fiis)
bullish_count = sum(1 for x in (equities + fiis) if x["sentiment_score"] > 0)
bearish_count = sum(1 for x in (equities + fiis) if x["sentiment_score"] < 0)

with col1:
    st.metric("Total Assets Analyzed", total_assets)
with col2:
    st.metric("Bullish Sentiment", bullish_count, delta="Positive")
with col3:
    st.metric("Bearish Sentiment", bearish_count, delta="-Negative", delta_color="inverse")

st.divider()

# --- TABS FOR ASSET TYPES ---
tab_stocks, tab_fiis = st.tabs(["📈 Stocks (Ações)", "🏢 REITs (FIIs)"])

def render_asset_view(assets):
    if not assets:
        st.info("No data available for this category.")
        return

    for asset in assets:
        ticker = asset['ticker']
        score = asset['sentiment_score']
        sentiment = asset['overall_sentiment']
        trend = asset['price_trend']
        
        # Date is already formatted in load_report_data
        analysis_date = asset.get('analysis_date', 'N/A')
        
        emoji = helpers.get_sentiment_emoji(score)
        color = helpers.get_sentiment_color(score)

        with st.expander(f"{emoji} {ticker} | {sentiment} ({score})", expanded=False):
            
            # Header Metrics
            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                st.caption("Price Trend")
                st.write(f"**{trend}**")
            with c2:
                st.caption("Sentiment Score")
                st.markdown(f":{color}[{score}]")
            with c3:
                st.caption("Analysis Date")
                st.write(analysis_date)
            
            st.divider()
            
            # --- STRUCTURED MARKDOWN RENDERING ---
            # Instead of one blob, we render sections independently
            
            # 1. Summary
            st.subheader("📋 Executive Summary")
            st.markdown(helpers.escape_markdown_dollars(asset.get('summary', 'No summary available.')))
            st.divider()

            # 2. Bullish Thesis
            st.subheader("🐂 Bullish Thesis")
            st.markdown(helpers.escape_markdown_dollars(asset.get('bullish_thesis', 'N/A')))
            st.divider()

            # 3. Bearish Thesis
            st.subheader("🐻 Bearish Thesis")
            st.markdown(helpers.escape_markdown_dollars(asset.get('bearish_thesis', 'N/A')))
            st.divider()

            # 4. Financial Analysis
            st.subheader("📊 Financial Analysis")
            st.markdown(helpers.escape_markdown_dollars(asset.get('financial_analysis', 'N/A')))
            st.divider()

            # 5. News & Events
            st.subheader("📰 Recent News & Events")
            st.markdown(helpers.escape_markdown_dollars(asset.get('news_and_events', 'N/A')))
            
            # Raw Data View
            with st.expander("🛠️ View Raw JSON Data"):
                st.json(asset)

with tab_stocks:
    render_asset_view(equities)

with tab_fiis:
    render_asset_view(fiis)
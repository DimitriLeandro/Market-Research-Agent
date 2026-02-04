import streamlit as st
import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import date
import yaml

# --- Configuration ---
RESULTS_DIR = Path("results")
PORTFOLIO_PATH = Path("market_agent/config/portfolio.yaml")

st.set_page_config(layout="wide", page_title="Market Research Agent")

# --- Helpers ---
def load_available_dates():
    if not RESULTS_DIR.exists():
        return []
    dates = [d.name.replace("_", "-") for d in RESULTS_DIR.iterdir() if d.is_dir()]
    dates.sort(reverse=True)
    return dates

def get_dir_for_date(date_str):
    return RESULTS_DIR / date_str.replace("-", "_")

def load_portfolio_data():
    if not PORTFOLIO_PATH.exists():
        return []
    with open(PORTFOLIO_PATH, "r") as f:
        data = yaml.safe_load(f)
    return data.get("assets", [])

def run_agent(test_mode=False):
    """Runs the market agent as a subprocess."""
    cmd = [sys.executable, "market_agent/main.py"]
    if test_mode:
        cmd.append("--test")
        
    mode_str = "TEST" if test_mode else "PRODUCTION"
    
    with st.spinner(f"Running Agent in {mode_str} mode... This may take a while."):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                st.success(f"Execution successful in {mode_str} mode!")
                st.info("Please refresh the page to see new results.")
                with st.expander("View Logs"):
                    st.code(result.stdout)
            else:
                st.error(f"Execution failed.")
                with st.expander("View Error Logs"):
                    st.code(result.stderr)
                    st.code(result.stdout)
        except Exception as e:
            st.error(f"Failed to launch subprocess: {e}")

# --- UI Layout ---
st.title("🤖 AI Market Research Agent")

# --- Sidebar: Execution Controls ---
st.sidebar.header("Execution Control")

st.sidebar.info("Production Mode runs the full portfolio.")
if st.sidebar.button("🚀 Run Production Cycle", type="primary"):
    run_agent(test_mode=False)

st.sidebar.markdown("---")

st.sidebar.warning("Test Mode runs a small subset (2 Stocks, 2 FIIs).")
if st.sidebar.button("🧪 Run Test Mode"):
    run_agent(test_mode=True)

st.sidebar.markdown("---")

# --- Main Content: Report Viewing ---
dates = load_available_dates()
if not dates:
    st.warning("No research data found. Run the agent to generate reports.")
    st.stop()

selected_date = st.sidebar.selectbox("Select Date", dates)
date_dir = get_dir_for_date(selected_date)

# Tabs
tab_stocks, tab_fiis, tab_sectors = st.tabs(["📈 Stocks", "🏢 Real Estate (FIIs)", "🏭 Sectors"])

# --- Load Assets ---
all_assets = load_portfolio_data()
stocks = [a for a in all_assets if a['type'] == 'equity']
fiis = [a for a in all_assets if a['type'] == 'fii']

def display_asset_report(ticker):
    report_path = date_dir / "tickers" / ticker / "final" / "report.json"
    if not report_path.exists():
        st.error(f"Report not found for {ticker} on {selected_date}")
        return

    with open(report_path, "r") as f:
        data = json.load(f)

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header(f"{data['ticker']}")
        st.caption(f"Sentiment: {data['overall_sentiment']} | Score: {data['sentiment_score']}")
    with col2:
        st.metric("Trend", data['price_trend'])

    st.subheader("Executive Summary")
    st.write(data['summary'])

    with st.expander("🐂 Bull Thesis", expanded=True):
        st.markdown(data['bullish_thesis'])

    with st.expander("🐻 Bear Thesis", expanded=True):
        st.markdown(data['bearish_thesis'])

    with st.expander("📊 Financial Analysis"):
        st.markdown(data['financial_analysis'])

    with st.expander("📰 Recent News & Events"):
        st.markdown(data['news_and_events'])

# --- Stocks Tab ---
with tab_stocks:
    stock_tickers = [a['ticker'] for a in stocks]
    selected_stock = st.selectbox("Select Stock", stock_tickers)
    if selected_stock:
        display_asset_report(selected_stock)

# --- FIIs Tab ---
with tab_fiis:
    fii_tickers = [a['ticker'] for a in fiis]
    selected_fii = st.selectbox("Select FII", fii_tickers)
    if selected_fii:
        display_asset_report(selected_fii)

# --- Sectors Tab ---
with tab_sectors:
    sectors_dir = date_dir / "sectors"
    if sectors_dir.exists():
        available_sectors = [d.name for d in sectors_dir.iterdir() if d.is_dir()]
        
        selected_sector_folder = st.selectbox("Select Sector", available_sectors)
        
        if selected_sector_folder:
            sector_path = sectors_dir / selected_sector_folder
            
            # Load the 3 distinct files
            try:
                # Initialize variables to avoid unbound errors
                bull, bear, news = "", "", ""
                
                if (sector_path / "bull_thesis.md").exists():
                    with open(sector_path / "bull_thesis.md", "r") as f: bull = f.read()
                
                if (sector_path / "bear_thesis.md").exists():
                    with open(sector_path / "bear_thesis.md", "r") as f: bear = f.read()
                
                if (sector_path / "news.md").exists():
                    with open(sector_path / "news.md", "r") as f: news = f.read()

                st.header(f"Sector Analysis: {selected_sector_folder.replace('_', '/')}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🐂 Optimistic Thesis (Bull)")
                    st.markdown(bull)
                with col2:
                    st.subheader("🐻 Pessimistic Thesis (Bear)")
                    st.markdown(bear)
                
                st.divider()
                st.subheader("📰 Recent Sector News")
                st.markdown(news)

            except Exception as e:
                st.error(f"Error loading sector data: {e}")
    else:
        st.info("No sector data recorded for this date.")
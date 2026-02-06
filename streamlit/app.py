import streamlit as st
import subprocess
import sys
from pathlib import Path

import helpers

st.set_page_config(layout="wide", page_title="Agente de Pesquisa de Mercado", page_icon="🤖")


def render_dynamic_report(data: dict):
    """
    Renders a single report based strictly on the 'sections' list structure.
    """
    identifier = data.get("ticker", data.get("sector", "Desconhecido"))
    
    sentiment = data.get("overall_sentiment", "N/A")
    score = data.get("sentiment_score", None)
    trend = data.get("price_trend", None)
    date_str = data.get("analysis_date", "-")
    
    emoji = helpers.get_sentiment_emoji(sentiment, score if score is not None else 0)
    
    label = f"{emoji} {identifier} | {sentiment}"
    
    with st.expander(label, expanded=False):
        cols = st.columns(4)
        cols[0].metric("Sentimento", sentiment)
        if score is not None:
            cols[1].metric("Pontuação", f"{score}")
        if trend:
            cols[2].metric("Tendência", trend)
        cols[3].caption(f"Data: {date_str}")
        
        st.divider()
        
        sections = data.get("sections", [])
        
        if not sections:
            st.warning("Nenhum detalhe disponível no relatório.")
        
        for section in sections:
            title = section.get("title", "Seção Sem Título")
            raw_content = section.get("content", "")
            sec_id = section.get("id", "")
            
            content = helpers.escape_markdown_dollars(raw_content)
            
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
                st.subheader(title)
                st.markdown(content)
            
            st.markdown("---")

def run_agent_process(test_mode: bool):
    """Executes the agent script using paths from helpers."""
    script_path = helpers.MAIN_SCRIPT_PATH
    
    if not script_path.exists():
        st.error(f"Erro Crítico: Script do agente não encontrado em {script_path}")
        return

    cmd = [sys.executable, str(script_path)]
    if test_mode:
        cmd.append("--test")
    
    mode_label = "TESTE" if test_mode else "PRODUÇÃO"
    
    with st.spinner(f"Executando Agente em modo {mode_label}..."):
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=str(helpers.PROJECT_ROOT)
            )
            
            if result.returncode == 0:
                st.success("Execução concluída com sucesso!")
                st.info("Atualize a página para visualizar os resultados.")
            else:
                st.error("Falha na execução.")
                with st.expander("Ver Logs de Erro"):
                    st.code(result.stdout)
                    st.code(result.stderr)
        except Exception as e:
            st.error(f"Falha ao iniciar processo: {e}")


# --- Layout Principal ---

st.title("Agente de Pesquisa de Mercado")

st.sidebar.header("Controles")

if st.sidebar.button("🚀 Executar Ciclo Completo", type="primary"):
    run_agent_process(test_mode=False)

if st.sidebar.button("🧪 Modo de Teste"):
    run_agent_process(test_mode=True)

st.sidebar.markdown("---")

available_dates = helpers.get_available_dates()

if not available_dates:
    st.warning("Nenhum dado de pesquisa encontrado.")
    st.stop()

selected_date_str = st.sidebar.selectbox(
    "Data da Análise", 
    available_dates, 
    format_func=helpers.format_date_uk
)

date_dir_path = helpers.get_dir_for_date(selected_date_str)

# --- Carregamento de Dados (Para Métricas e Abas) ---
stock_reports = helpers.load_reports_by_category(date_dir_path, "stocks")
reit_reports = helpers.load_reports_by_category(date_dir_path, "reits")
sector_reports = helpers.load_reports_by_category(date_dir_path, "sectors")

# --- Cálculo de Métricas ---
total_assets = len(stock_reports) + len(reit_reports)
total_sectors = len(sector_reports)

all_assets = stock_reports + reit_reports
# Conta tendências baseadas no retorno do Enum (UpTrend/DownTrend/Sideways/Volatile)
uptrend_count = sum(1 for r in all_assets if r.get("price_trend") == "Uptrend")
downtrend_count = sum(1 for r in all_assets if r.get("price_trend") == "Downtrend")

# --- Exibição de Métricas (Dashboard) ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total de Ativos", total_assets)
m2.metric("Setores Analisados", total_sectors)
m3.metric("Tendência de Alta 📈", uptrend_count)
m4.metric("Tendência de Baixa 📉", downtrend_count)

st.divider()

# --- Abas de Conteúdo ---
tab_stocks, tab_fiis, tab_sectors = st.tabs(["📈 Ações", "🏢 Fundos Imobiliários (FIIs)", "🏭 Setores"])

with tab_stocks:
    if stock_reports:
        for report in stock_reports:
            render_dynamic_report(report)
    else:
        st.info("Nenhum relatório de Ações encontrado para esta data.")

with tab_fiis:
    if reit_reports:
        for report in reit_reports:
            render_dynamic_report(report)
    else:
        st.info("Nenhum relatório de FIIs encontrado para esta data.")

with tab_sectors:
    if sector_reports:
        for report in sector_reports:
            render_dynamic_report(report)
    else:
        st.info("Nenhum relatório Setorial encontrado para esta data.")
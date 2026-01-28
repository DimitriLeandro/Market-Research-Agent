import streamlit as st
from pathlib import Path
import re
import markdown

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="IA Stock Analyst",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DEFINIÇÃO DE CAMINHOS ---
BASE_DIR  = Path("../results")
LOGO_PATH = Path("../assets/img/logo.png")

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
    /* Fundo Geral */
    .stApp { background-color: #0E1117; }
    
    /* Cabeçalhos */
    h1 { color: #FAFAFA; margin-bottom: 0px; }
    h3 { color: #A0A0A0; font-weight: 400; font-size: 1.2rem; margin-top: 0px; }
    
    /* Cards (Expanders) */
    .stExpander {
        border: 1px solid #303030;
        border-radius: 8px;
        background-color: #161B22;
    }
    .streamlit-expanderHeader { color: #E6E6E6; font-weight: 600; }

    /* Summary Box Container */
    .summary-container {
        padding: 20px;
        border-radius: 12px;
        background-color: #1F2937;
        border-left: 6px solid #3B82F6;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    
    /* Estilos para o HTML convertido (Markdown -> HTML) */
    .summary-text {
        color: #E6E6E6 !important;
        font-family: sans-serif;
    }
    .summary-text h1, .summary-text h2, .summary-text h3 {
        color: #FFFFFF !important;
        margin-top: 15px;
        margin-bottom: 10px;
        font-weight: 600;
    }
    .summary-text h3 {
        font-size: 1.1rem;
        border-bottom: 1px solid #374151;
        padding-bottom: 5px;
    }
    .summary-text p, .summary-text li {
        color: #D1D5DB !important; /* Cinza claro */
        line-height: 1.6;
        font-size: 1rem;
    }
    .summary-text strong {
        color: #FFFFFF !important;
        font-weight: bold;
    }
    
    /* Estilo para Links de Ações (Efeito Hover) */
    a.stock-link {
        text-decoration: none;
        transition: opacity 0.3s;
    }
    a.stock-link:hover {
        opacity: 0.7;
    }
    a.stock-link h2 {
        cursor: pointer;
    }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #303030; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES AUXILIARES ---
def get_available_dates():
    if not BASE_DIR.exists(): return []
    dates = [d.name for d in BASE_DIR.iterdir() if d.is_dir()]
    return sorted(dates, reverse=True)

def load_markdown_file(path):
    if path.exists(): return path.read_text(encoding="utf-8")
    return None

def format_date_label(date_str):
    try:
        parts = date_str.split('_')
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except:
        return date_str

def get_ticker_logo_url(ticker):
    # Retorna a URL direta (usada no st.image)
    return f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{ticker.upper()}.png"

def get_investidor10_url(ticker):
    """Gera o link para o site Investidor10."""
    return f"https://investidor10.com.br/acoes/{ticker.lower()}/"

def parse_consolidated_report(text):
    """
    Fatia o relatório baseando-se nos cabeçalhos ## TICKER.
    """
    lines = text.split('\n')
    blocks = []
    
    current_ticker = None
    current_content = []
    
    # Regex ajustada para pegar "## TICKER"
    ticker_header_pattern = re.compile(r'^##\s+([A-Z0-9]{4,6})\s*$')

    for line in lines:
        match = ticker_header_pattern.match(line)
        
        if match:
            if current_content:
                blocks.append({
                    "ticker": current_ticker,
                    "content": "\n".join(current_content)
                })
            
            current_ticker = match.group(1)
            current_content = [] 
        else:
            current_content.append(line)
            
    if current_content:
        blocks.append({
            "ticker": current_ticker,
            "content": "\n".join(current_content)
        })
        
    return blocks

# --- APP PRINCIPAL ---
def main():
    with st.sidebar:

        if LOGO_PATH.exists():
            # Exibe a imagem centralizada na sidebar
            st.image(str(LOGO_PATH), width='stretch')
        else:
            # Fallback caso a imagem não exista
            st.warning("Arquivo app_logo.png não encontrado.")
            
        st.title("📊 IA Stock Analyst")
        st.markdown("---")
        
        # ---------------------------
        
        dates = get_available_dates()
        
        if not dates:
            st.error("Nenhum dado encontrado.")
            st.stop()
            
        date_map = {format_date_label(d): d for d in dates}
        selected_label = st.selectbox("📅 Selecione a Data", list(date_map.keys()))
        selected_date_dir = date_map[selected_label]
        
        st.markdown("---")
        st.caption("Developed with ❤️ by **Gemini Agent**")

    current_dir = BASE_DIR / selected_date_dir

    # Header
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.title(f"Relatório de Mercado")
        st.markdown(f"### Análise consolidada de {selected_label}")
    st.markdown("---")

    # --- 1. RELATÓRIO CONSOLIDADO ---
    final_report_path = current_dir / f"final_report_{selected_date_dir}.md"
    final_report_content = load_markdown_file(final_report_path)

    if final_report_content:
        st.subheader("📰 Highlights do Dia")
        
        with st.container():
            st.markdown('<div class="summary-container">', unsafe_allow_html=True) # Abre container cinza
            
            report_blocks = parse_consolidated_report(final_report_content)
            
            for block in report_blocks:
                ticker = block['ticker']
                raw_content = block['content']
                
                # Converter Markdown para HTML
                html_content = markdown.markdown(raw_content)
                
                if ticker:
                    # Link externo para Investidor10
                    stock_link = get_investidor10_url(ticker)
                    
                    # Bloco com Logo e Título (Linkável)
                    c_logo, c_text = st.columns([1, 12])
                    
                    with c_logo:
                        st.write("") 
                        st.image(get_ticker_logo_url(ticker), width=50)
                    
                    with c_text:
                        # Criamos um Link HTML envolvendo o Título H2
                        # target="_blank" garante que abra em nova aba
                        st.markdown(f'''
                            <a href="{stock_link}" target="_blank" class="stock-link" title="Ver fundamentos no Investidor10">
                                <h2 style="color: white; margin-top: 0;">{ticker} 🔗</h2>
                            </a>
                        ''', unsafe_allow_html=True)
                        
                        st.markdown(f'<div class="summary-text">{html_content}</div>', unsafe_allow_html=True)
                        
                    st.markdown("---") 
                    
                else:
                    # Bloco Introdutório
                    if raw_content.strip():
                        st.markdown(f'<div class="summary-text">{html_content}</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True) # Fecha container cinza
            
    else:
        st.info(f"O relatório consolidado ainda não foi gerado para {selected_label}.")

    # --- 2. DETALHES DOS ATIVOS ---
    st.markdown("### 🔎 Detalhes por Ativo")
    search_term = st.text_input("Filtrar Ativo", placeholder="Ex: PETR4, VALE3...").upper().strip()
    
    all_files = sorted([f for f in current_dir.glob("*.md") if "final_report" not in f.name])
    filtered_files = [f for f in all_files if search_term in f.name]

    if not filtered_files:
        if search_term: st.warning(f"Nenhum ativo encontrado para '{search_term}'.")
        else: st.info("Nenhum arquivo de detalhe encontrado nesta data.")
    else:
        cols = st.columns(2)
        for index, file_path in enumerate(filtered_files):
            ticker_name = file_path.name.split('_')[0]
            content = load_markdown_file(file_path)
            logo_url = get_ticker_logo_url(ticker_name)
            stock_link = get_investidor10_url(ticker_name)
            
            with cols[index % 2]:
                with st.expander(f"{ticker_name}", expanded=False):
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        st.image(logo_url, width=60) 
                    with c2:
                        # Link usando sintaxe Markdown padrão [Texto](Link)
                        st.markdown(f"### [{ticker_name} 🔗]({stock_link})")
                        st.caption("Análise Detalhada • Clique no título para ver fundamentos")
                    st.markdown("---")
                    st.markdown(content)

if __name__ == "__main__":
    main()
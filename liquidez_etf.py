import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Analisador de Liquidez ETF", layout="wide")

st.title("📊 Monitor de Liquidez de ETFs")
st.markdown("""
Este app analisa a liquidez histórica de ativos financeiros.
Faça o upload do arquivo (**XLSX, CSV ou XML**) para começar.
""")

# --- FUNÇÕES AUXILIARES ---

def extract_ticker(col_name):
    """
    Tenta extrair um ticker (ex: BOVA11) de uma string suja.
    Procura por 4 letras seguidas de 1 ou 2 números.
    """
    # Converte para string para evitar erros se o Excel ler o cabeçalho como objeto/número
    s_col = str(col_name).strip()
    
    if s_col.lower() == 'data':
        return 'Data'
    
    # Regex para encontrar padrão XXXX11 ou XXXX3 no meio da sujeira da Comdinheiro
    match = re.search(r'([A-Z]{4}\d{1,2})', s_col)
    if match:
        return match.group(1)
    
    # Se não achar nada, devolve o nome original
    return col_name

@st.cache_data
def load_data(uploaded_file):
    """
    Lê o arquivo dependendo da extensão e trata os dados.
    """
    try:
        df = None
        file_name = uploaded_file.name.lower()

        # --- ESTRATÉGIA DE LEITURA (PROTOCOLO VONDER) ---
        
        # 1. EXCEL (XLSX)
        if file_name.endswith('.xlsx'):
            # Engine openpyxl é obrigatória para xlsx modernos no Streamlit
            df = pd.read_excel(uploaded_file, engine='openpyxl')
            
        # 2. CSV
        elif file_name.endswith('.csv'):
            try:
                # Tenta padrão internacional (vírgula)
                df = pd.read_csv(uploaded_file)
            except:
                # Fallback para padrão brasileiro (ponto e vírgula)
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=';')
        
        # 3. XML
        elif file_name.endswith('.xml'):
            df = pd.read_xml(uploaded_file)
            
        # --- TRATAMENTO DOS DADOS ---
        if df is not None:
            # Limpeza dos Tickers (Headers)
            df.columns = [extract_ticker(c) for c in df.columns]
            
            # Tratamento da Data
            if 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data'])
                df = df.sort_values('Data')
            else:
                st.error("ERRO: Não encontrei a coluna 'Data'. Verifique se o cabeçalho do arquivo está na primeira linha.")
                return None
            
            return df
            
    except Exception as e:
        st.error(f"Erro crítico ao processar o arquivo: {e}")
        return None
    return None

# --- SIDEBAR (MENU LATERAL) ---

with st.sidebar:
    st.header("Upload de Dados")
    uploaded_file = st.file_uploader(
        "Arraste sua planilha aqui", 
        type=["xlsx", "csv", "xml"]
    )
    
    st.markdown("---")
    mode = st.radio("Modo de Análise", ["Análise Individual", "Duelo de Liquidez"])
    st.markdown("---")
    st.caption("Desenvolvido com Python + Streamlit")

# --- LÓGICA PRINCIPAL ---

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None:
        # Lista de ativos (todas as colunas menos a Data)
        ativos = [c for c in df.columns if c != 'Data']
        
        if not ativos:
            st.warning("Aviso: Não identifiquei nenhum código de ativo (ex: BOVA11). Verifique o cabeçalho da planilha.")
        
        # --- MODO 1: ANÁLISE INDIVIDUAL ---
        elif mode == "Análise Individual":
            st.subheader("🔍 Análise de Ativo Único")
            
            selected_asset = st.selectbox("Selecione o Ativo:", ativos)
            
            if selected_asset:
                # Cálculos Estatísticos
                series = df[selected_asset]
                media = series.mean()
                mediana = series.median()
                desvio = series.std()
                ratio = media / mediana if mediana > 0 else 0
                
                # Datas
                start_date = df['Data'].min().strftime('%d/%m/%Y')
                end_date = df['Data'].max().strftime('%d/%m/%Y')
                
                # Cartões de Métricas
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Período", f"{start_date}\na {end_date}")
                c2.metric("Volume Médio", f"R$ {media:,.2f}")
                c3.metric("Mediana", f"R$ {mediana:,.2f}")
                c4.metric("Desvio Padrão", f"R$ {desvio:,.2f}")
                
                # Alerta sobre consistência
                st.info(f"**Razão Média/Mediana:** {ratio:.2f} — (Quanto mais próximo de 1, mais consistente é a liquidez diária).")
                
                # Gráfico: Barras + Linhas de Referência
                st.markdown("### Dispersão de Volume (Média vs Mediana)")
                fig = go.Figure()
                
                # Volume Diário
                fig.add_trace(go.Bar(
                    x=df['Data'], 
                    y=df[selected_asset], 
                    name='Volume Diário',
                    marker_color='#636EFA'
                ))
                
                # Linha Média
                fig.add_trace(go.Scatter(
                    x=df['Data'], 
                    y=[media]*len(df), 
                    mode='lines', 
                    name=f'Média (R$ {media:,.0f})',
                    line=dict(color='#EF553B', dash='dash', width=2)
                ))
                
                # Linha Mediana
                fig.add_trace(go.Scatter(
                    x=df['Data'], 
                    y=[mediana]*len(df), 
                    mode='lines', 
                    name=f'Mediana (R$ {mediana:,.0f})',
                    line=dict(color='#00CC96', dash='dot', width=2)
                ))
                
                fig.update_layout(
                    title=f"Evolução do Volume: {selected_asset}",
                    xaxis_title="Data",
                    yaxis_title="Volume Financeiro (R$)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig, use_container_width=True)

        # --- MODO 2: DUELO DE LIQUIDEZ ---
        elif mode == "Duelo de Liquidez":
            st.subheader("⚔️ Duelo de Liquidez")
            
            # Seletores lado a lado
            col_sel1, col_sel2 = st.columns(2)
            asset1 = col_sel1.selectbox("Lutador 1:", ativos, index=0)
            # Tenta selecionar o segundo item da lista por padrão para facilitar
            asset2 = col_sel2.selectbox("Lutador 2:", ativos, index=1 if len(ativos) > 1 else 0)
            
            if asset1 and asset2:
                if asset1 == asset2:
                    st.warning("⚠️ Selecione dois ativos diferentes para realizar o comparativo.")
                else:
                    # Tabela Comparativa
                    m1, m2 = df[asset1].mean(), df[asset2].mean()
                    med1, med2 = df[asset1].median(), df[asset2].median()
                    std1, std2 = df[asset1].std(), df[asset2].std()
                    
                    st.markdown("### Placar Geral")
                    comp_data = {
                        "Métrica": ["Volume Médio", "Volume Mediano", "Desvio Padrão"],
                        asset1: [f"R$ {m1:,.2f}", f"R$ {med1:,.2f}", f"R$ {std1:,.2f}"],
                        asset2: [f"R$ {m2:,.2f}", f"R$ {med2:,.2f}", f"R$ {std2:,.2f}"]
                    }
                    st.table(pd.DataFrame(comp_data))
                    
                    # Gráfico de Linhas Comparativo
                    st.markdown("### Batalha Visual")
                    fig_duel = go.Figure()
                    
                    fig_duel.add_trace(go.Scatter(
                        x=df['Data'], y=df[asset1], mode='lines', name=asset1, line=dict(width=2)
                    ))
                    fig_duel.add_trace(go.Scatter(
                        x=df['Data'], y=df[asset2], mode='lines', name=asset2, line=dict(width=2)
                    ))
                    
                    fig_duel.update_layout(
                        title=f"Histórico de Volume: {asset1} vs {asset2}",
                        xaxis_title="Data",
                        yaxis_title="Volume Financeiro (R$)",
                        hovermode="x unified",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    
                    st.plotly_chart(fig_duel, use_container_width=True)
                    
else:
    # Mensagem de boas-vindas quando não há arquivo
    st.info("👈 Utilize o menu lateral para fazer o upload da planilha.")

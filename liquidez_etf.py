import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re

# Configuração da página
st.set_page_config(page_title="Analisador de Liquidez ETF", layout="wide")

st.title("📊 Monitor de Liquidez de ETFs")
st.markdown("""
Este app analisa a liquidez histórica de ativos.
Faça o upload do arquivo (CSV ou XML) para começar.
""")

# --- FUNÇÕES AUXILIARES ---

def extract_ticker(col_name):
    """
    Tenta extrair um ticker (ex: BOVA11) de uma string suja.
    Procura por 4 letras seguidas de 1 ou 2 números.
    """
    if str(col_name).strip().lower() == 'data':
        return 'Data'
    
    # Regex para encontrar padrão XXXX11 ou XXXX3
    # Convertemos para string pois XML as vezes traz nomes como objetos
    match = re.search(r'([A-Z]{4}\d{1,2})', str(col_name))
    if match:
        return match.group(1)
    return col_name

@st.cache_data
def load_data(uploaded_file):
    try:
        df = None
        # Verifica a extensão do arquivo para decidir como ler
        if uploaded_file.name.lower().endswith('.csv'):
            # Tenta ler CSV (padrão vírgula ou ponto-e-vírgula)
            try:
                df = pd.read_csv(uploaded_file)
            except:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=';')
                
        elif uploaded_file.name.lower().endswith('.xml'):
            # PROTOCOLO VONDER: Tenta ler o XML no formato tabular padrão.
            # Se o XML for muito aninhado (árvore complexa), isso pode falhar sem um parser específico.
            df = pd.read_xml(uploaded_file)
            
        if df is not None:
            # Limpeza dos nomes das colunas
            df.columns = [extract_ticker(c) for c in df.columns]
            
            # Converte Data (assume que existe uma coluna que virou 'Data' após a limpeza)
            if 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data'])
                df = df.sort_values('Data')
            else:
                st.error("Não encontrei uma coluna de data válida. Verifique o cabeçalho do arquivo.")
                return None
            
            return df
            
    except Exception as e:
        st.error(f"Erro no processamento (Protocolo Vonder - Falha de Leitura): {e}")
        return None
    return None

# --- SIDEBAR ---

with st.sidebar:
    st.header("Upload de Dados")
    # ATUALIZADO: Agora aceita csv e xml
    uploaded_file = st.file_uploader("Arraste sua planilha aqui", type=["csv", "xml"])
    
    st.markdown("---")
    mode = st.radio("Modo de Análise", ["Análise Individual", "Duelo de Liquidez"])

# --- LÓGICA PRINCIPAL ---

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None:
        # Identificar colunas de ativos (excluindo a coluna Data)
        ativos = [c for c in df.columns if c != 'Data']
        
        if not ativos:
            st.warning("Não consegui identificar nenhum Ticker (ex: BOVA11) nas colunas. Verifique o arquivo.")
        
        elif mode == "Análise Individual":
            st.subheader("🔍 Análise de Ativo Único")
            
            selected_asset = st.selectbox("Selecione o Ativo:", ativos)
            
            if selected_asset:
                # Cálculos
                series = df[selected_asset]
                media = series.mean()
                mediana = series.median()
                desvio = series.std()
                ratio = media / mediana if mediana > 0 else 0
                
                start_date = df['Data'].min().strftime('%d/%m/%Y')
                end_date = df['Data'].max().strftime('%d/%m/%Y')
                
                # Exibição de Métricas
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Período", f"{start_date}\na {end_date}")
                col2.metric("Volume Médio", f"R$ {media:,.2f}")
                col3.metric("Mediana", f"R$ {mediana:,.2f}")
                col4.metric("Desvio Padrão", f"R$ {desvio:,.2f}")
                
                st.info(f"**Razão Média/Mediana:** {ratio:.2f} (Quanto mais próximo de 1, mais constante é a liquidez).")
                
                # Gráfico de Dispersão
                st.markdown("### Dispersão de Volume (Média vs Mediana)")
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=df['Data'], 
                    y=df[selected_asset], 
                    name='Volume Diário',
                    marker_color='lightblue'
                ))
                
                fig.add_trace(go.Scatter(
                    x=df['Data'], 
                    y=[media]*len(df), 
                    mode='lines', 
                    name=f'Média (R$ {media:,.0f})',
                    line=dict(color='red', dash='dash')
                ))
                
                fig.add_trace(go.Scatter(
                    x=df['Data'], 
                    y=[mediana]*len(df), 
                    mode='lines', 
                    name=f'Mediana (R$ {mediana:,.0f})',
                    line=dict(color='green', dash='dot')
                ))
                
                fig.update_layout(
                    title=f"Evolução do Volume: {selected_asset}",
                    xaxis_title="Data",
                    yaxis_title="Volume Financeiro (R$)",
                    legend_title="Legenda",
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig, use_container_width=True)

        elif mode == "Duelo de Liquidez":
            st.subheader("⚔️ Duelo de Liquidez")
            
            col_sel1, col_sel2 = st.columns(2)
            asset1 = col_sel1.selectbox("Lutador 1:", ativos, index=0)
            asset2 = col_sel2.selectbox("Lutador 2:", ativos, index=1 if len(ativos) > 1 else 0)
            
            if asset1 and asset2:
                if asset1 == asset2:
                    st.warning("Selecione dois ativos diferentes para o duelo.")
                else:
                    m1 = df[asset1].mean()
                    m2 = df[asset2].mean()
                    med1 = df[asset1].median()
                    med2 = df[asset2].median()
                    
                    comp_data = {
                        "Métrica": ["Volume Médio", "Volume Mediano", "Desvio Padrão"],
                        asset1: [f"R$ {m1:,.2f}", f"R$ {med1:,.2f}", f"R$ {df[asset1].std():,.2f}"],
                        asset2: [f"R$ {m2:,.2f}", f"R$ {med2:,.2f}", f"R$ {df[asset2].std():,.2f}"]
                    }
                    st.table(pd.DataFrame(comp_data))
                    
                    st.markdown("### Comparativo Visual")
                    fig_duel = go.Figure()
                    
                    fig_duel.add_trace(go.Scatter(
                        x=df['Data'], y=df[asset1], mode='lines', name=asset1
                    ))
                    fig_duel.add_trace(go.Scatter(
                        x=df['Data'], y=df[asset2], mode='lines', name=asset2
                    ))
                    
                    fig_duel.update_layout(
                        title=f"Batalha de Volume: {asset1} vs {asset2}",
                        xaxis_title="Data",
                        yaxis_title="Volume Financeiro (R$)",
                        hovermode="x unified"
                    )
                    
                    st.plotly_chart(fig_duel, use_container_width=True)
                    
else:
    st.info("Aguardando upload do arquivo (CSV ou XML).")

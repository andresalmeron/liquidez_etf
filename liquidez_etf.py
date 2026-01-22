import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Analisador de Liquidez ETF", layout="wide")

st.title("📊 Monitor de Liquidez de ETFs")
st.markdown("""
Visão estrutural de liquidez.
Faça o upload do arquivo (**XLSX, CSV ou XML**) para começar.
""")

# --- FUNÇÕES AUXILIARES ---

def extract_ticker(col_name):
    """
    Limpa o nome da coluna para pegar apenas o Ticker.
    """
    s_col = str(col_name).strip()
    if s_col.lower() == 'data':
        return 'Data'
    match = re.search(r'([A-Z]{4}\d{1,2})', s_col)
    if match:
        return match.group(1)
    return col_name

@st.cache_data
def load_data(uploaded_file):
    try:
        df = None
        file_name = uploaded_file.name.lower()

        if file_name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        elif file_name.endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file)
            except:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=';')
        elif file_name.endswith('.xml'):
            df = pd.read_xml(uploaded_file)
            
        if df is not None:
            df.columns = [extract_ticker(c) for c in df.columns]
            if 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data'])
                df = df.sort_values('Data')
            else:
                st.error("ERRO: Coluna 'Data' não encontrada.")
                return None
            return df
    except Exception as e:
        st.error(f"Erro crítico: {e}")
        return None
    return None

# --- SIDEBAR ---

with st.sidebar:
    st.header("Parâmetros")
    uploaded_file = st.file_uploader("Arquivo de Dados", type=["xlsx", "csv", "xml"])
    st.markdown("---")
    mode = st.radio("Modo de Análise", ["Raio-X Individual", "Duelo de Liquidez"])

# --- LÓGICA PRINCIPAL ---

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None:
        ativos = [c for c in df.columns if c != 'Data']
        
        # --- MODO 1: RAIO-X INDIVIDUAL ---
        if mode == "Raio-X Individual":
            st.subheader("🔍 Raio-X de Liquidez")
            selected_asset = st.selectbox("Selecione o Ativo:", ativos)
            
            if selected_asset:
                series = df[selected_asset]
                
                # Cálculos
                media = series.mean()
                mediana = series.median()
                vol_max = series.max()
                vol_min = series.min()
                ratio = media / mediana if mediana > 0 else 0
                
                # Display Métricas
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Volume Médio", f"R$ {media:,.2f}")
                c2.metric("Volume Mediano", f"R$ {mediana:,.2f}")
                c3.metric("Razão Média/Mediana", f"{ratio:.2f}x")
                c4.metric("Extremos (Min/Máx)", f"R$ {vol_min:,.0f} / R$ {vol_max:,.0f}")
                
                st.markdown("---")
                
                # Layout de Gráficos (Lado a Lado)
                g1, g2 = st.columns(2)
                
                with g1:
                    # Gráfico 1: Estrutura
                    fig_struct = go.Figure()
                    fig_struct.add_trace(go.Bar(
                        x=['Média', 'Mediana'],
                        y=[media, mediana],
                        text=[f'R$ {media:,.0f}', f'R$ {mediana:,.0f}'],
                        textposition='auto',
                        marker_color=['#EF553B', '#00CC96']
                    ))
                    fig_struct.update_layout(
                        title=f"Estrutura: Média vs Mediana ({selected_asset})",
                        yaxis_title="Volume Financeiro (R$)",
                        template="plotly_white"
                    )
                    st.plotly_chart(fig_struct, use_container_width=True)

                with g2:
                    # Gráfico 2: Extremos
                    fig_ext = go.Figure()
                    fig_ext.add_trace(go.Bar(
                        x=['Mínimo Dia', 'Máximo Dia'],
                        y=[vol_min, vol_max],
                        text=[f'R$ {vol_min:,.0f}', f'R$ {vol_max:,.0f}'],
                        textposition='auto',
                        marker_color=['#FFA15A', '#636EFA']
                    ))
                    fig_ext.update_layout(
                        title=f"Stress Test: Pior Dia vs Melhor Dia",
                        yaxis_title="Volume Financeiro (R$)",
                        template="plotly_white"
                    )
                    st.plotly_chart(fig_ext, use_container_width=True)

        # --- MODO 2: DUELO ---
        elif mode == "Duelo de Liquidez":
            st.subheader("⚔️ Duelo de Liquidez")
            
            c_sel1, c_sel2 = st.columns(2)
            a1 = c_sel1.selectbox("Ativo A:", ativos, index=0)
            a2 = c_sel2.selectbox("Ativo B:", ativos, index=1 if len(ativos) > 1 else 0)
            
            if a1 and a2 and a1 != a2:
                # Cálculos
                m1, m2 = df[a1].mean(), df[a2].mean()
                med1, med2 = df[a1].median(), df[a2].median()
                ratio1 = m1 / med1 if med1 > 0 else 0
                ratio2 = m2 / med2 if med2 > 0 else 0
                
                # Insight de Texto
                fator = m1 / m2 if m2 > 0 else 0
                if fator >= 1:
                    texto_insight = f"💎 **{a1}** é **{fator:.1f} vezes** mais líquido que {a2} (na média)."
                else:
                    texto_insight = f"💎 **{a2}** é **{(1/fator):.1f} vezes** mais líquido que {a1} (na média)."
                
                st.success(texto_insight)
                
                # Tabela Resumo
                comp_data = {
                    "Métrica": ["Volume Médio", "Volume Mediano", "Razão Média/Mediana", "Pior Dia"],
                    a1: [f"R$ {m1:,.2f}", f"R$ {med1:,.2f}", f"{ratio1:.2f}x", f"R$ {df[a1].min():,.2f}"],
                    a2: [f"R$ {m2:,.2f}", f"R$ {med2:,.2f}", f"{ratio2:.2f}x", f"R$ {df[a2].min():,.2f}"]
                }
                st.table(pd.DataFrame(comp_data))
                
                # --- GRÁFICOS DO DUELO ---
                
                # Colunas para separar Volume Absoluto de Consistência
                d_col1, d_col2 = st.columns(2)
                
                with d_col1:
                    # Gráfico 1: Volume Absoluto
                    fig_duel = go.Figure()
                    fig_duel.add_trace(go.Bar(
                        name=a1, x=['Média', 'Mediana'], y=[m1, med1],
                        text=[f'{m1/1e6:.1f}M', f'{med1/1e6:.1f}M'],
                        textposition='auto', marker_color='#1f77b4'
                    ))
                    fig_duel.add_trace(go.Bar(
                        name=a2, x=['Média', 'Mediana'], y=[m2, med2],
                        text=[f'{m2/1e6:.1f}M', f'{med2/1e6:.1f}M'],
                        textposition='auto', marker_color='#ff7f0e'
                    ))
                    fig_duel.update_layout(
                        title="Quem entrega mais volume?",
                        barmode='group',
                        template="plotly_white"
                    )
                    st.plotly_chart(fig_duel, use_container_width=True)
                
                with d_col2:
                    # Gráfico 2: Consistência (Média / Mediana) - O NOVO PEDIDO
                    fig_ratio = go.Figure()
                    
                    # Barras de Ratio
                    fig_ratio.add_trace(go.Bar(
                        x=[a1, a2],
                        y=[ratio1, ratio2],
                        text=[f'{ratio1:.2f}x', f'{ratio2:.2f}x'],
                        textposition='auto',
                        marker_color=['#1f77b4', '#ff7f0e']
                    ))
                    
                    # Linha de Referência (Ideal = 1.0)
                    fig_ratio.add_shape(
                        type="line",
                        x0=-0.5, x1=1.5,
                        y0=1, y1=1,
                        line=dict(color="Red", width=2, dash="dash"),
                    )
                    
                    fig_ratio.update_layout(
                        title="Quem é mais consistente? (Ideal = 1.0)",
                        yaxis_title="Razão Média / Mediana",
                        template="plotly_white",
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig_ratio, use_container_width=True)
                    st.caption("Quanto mais alta a barra, mais distorcida é a liquidez (muitos dias vazios e poucos dias gigantes). O ideal é próximo de 1.0 (linha vermelha).")

else:
    st.info("Aguardando upload...")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from babel.numbers import format_currency # Importa a função de formatação de moeda
import locale
import calendar

# --- CONFIGURAÇÃO DA PÁGINA ---
# Define o layout da página para wide (amplo)
st.set_page_config(
    page_title="Dashboard de Análise de Água",
    page_icon=":droplet:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configura o locale para português do Brasil (pt_BR)
# Isso é crucial para que o Babel funcione corretamente na formatação da moeda e datas.
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    # Se 'pt_BR.UTF-8' falhar (comum em alguns ambientes), tenta 'pt_BR'
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR')
    except locale.Error:
        st.error("Erro: Não foi possível configurar o locale 'pt_BR'. A formatação de moeda e datas pode estar incorreta.")
        pass # Segue sem locale, mas com aviso

# --- TITULO E ESTILO ---
st.markdown(
    """
    <style>
    .big-font {
        font-size:30px !important;
        font-weight: bold;
    }
    .st-emotion-cache-18ni2p8 { /* Esconde o botão de menu e rodapé no Streamlit Cloud */
        visibility: hidden;
    }
    .st-emotion-cache-h5rgjs { /* Ajusta o tamanho da fonte do título principal */
        font-size: 2em;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title(":droplet: Dashboard de Análise de Volume e Custo de Água")

# --- FUNÇÕES DE PROCESSAMENTO DE DADOS ---

@st.cache_data
def load_data(uploaded_file):
    """Carrega e limpa os dados do arquivo Excel."""
    try:
        # Tenta ler o arquivo Excel (openpyxl é necessário para isso)
        df = pd.read_excel(uploaded_file, engine='openpyxl')
    except Exception as e:
        st.error(f"Erro ao ler o arquivo Excel: {e}")
        return None

    # Renomear colunas para uso interno
    df.columns = ['Data', 'Qtd.M³', 'Custo']

    # 1. Limpeza e conversão de tipos
    # Remove 'M³' da coluna Qtd.M³ e converte para numérico
    df['Qtd.M³'] = df['Qtd.M³'].astype(str).str.replace(r'[^\d,\.]', '', regex=True).str.replace(',', '.').astype(float)
    # Remove 'R$' e vírgulas da coluna Custo e converte para numérico
    df['Custo'] = df['Custo'].astype(str).str.replace(r'[^\d,\.]', '', regex=True).str.replace(',', '.').astype(float)
    # Converte a coluna Data para datetime
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')

    # 2. Filtrar linhas inválidas (Data ou valores nulos/zero)
    df.dropna(subset=['Data', 'Qtd.M³', 'Custo'], inplace=True)
    df = df[(df['Qtd.M³'] > 0) & (df['Custo'] > 0)]

    # 3. Engenharia de features
    df['Mês'] = df['Data'].dt.to_period('M')
    df['Dia_Semana'] = df['Data'].apply(lambda x: calendar.day_name[x.weekday()])

    # Mapeamento para nomes de dias da semana em português
    dias_semana_map = {
        'Monday': 'Segunda-feira',
        'Tuesday': 'Terça-feira',
        'Wednesday': 'Quarta-feira',
        'Thursday': 'Quinta-feira',
        'Friday': 'Sexta-feira',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    df['Dia_Semana'] = df['Dia_Semana'].map(dias_semana_map)

    # Colunas finais renomeadas para o dashboard
    df.rename(columns={'Qtd.M³': 'Volume_M3', 'Custo': 'Valor'}, inplace=True)

    return df

# --- FORMATADORES ---
def format_moeda(valor):
    """Formata um float para moeda R$ usando Babel."""
    try:
        # format_currency(valor, 'BRL', locale='pt_BR')
        return format_currency(valor, 'BRL', locale='pt_BR')
    except Exception:
        return f"R$ {valor:,.2f}".replace('.', '#').replace(',', '.').replace('#', ',')

def format_volume(volume):
    """Formata um float para volume com 'm³'."""
    return f"{volume:,.2f} m³".replace('.', '#').replace(',', '.').replace('#', ',')

def apply_formatters(df):
    """Aplica formatação a colunas de um DataFrame para visualização (sem alterar o tipo)."""
    df_formatado = df.copy()
    if 'Valor' in df_formatado.columns:
        df_formatado['Valor (R$)'] = df_formatado['Valor'].apply(format_moeda)
    if 'Volume_M3' in df_formatado.columns:
        df_formatado['Volume (m³)'] = df_formatado['Volume_M3'].apply(format_volume)
    return df_formatado

# --- SIDEBAR (UPLOAD DE ARQUIVO) ---
st.sidebar.markdown('<p class="big-font">Passo 1: Faça o upload do arquivo Excel (xlsx)</p>', unsafe_allow_html=True)
uploaded_file = st.sidebar.file_uploader("Arraste e solte o arquivo aqui.", type=['xlsx'])

df_final = None
if uploaded_file is not None:
    st.sidebar.markdown(f"**Arquivo:** `{uploaded_file.name}`", unsafe_allow_html=True)
    df_final = load_data(uploaded_file)

    if df_final is not None and not df_final.empty:
        st.sidebar.markdown(f"**Status dos Dados Diários**", unsafe_allow_html=True)
        # Verificação básica de validade
        if df_final.empty or 'Data' not in df_final.columns:
            st.sidebar.error("Nenhuma linha válida encontrada. Verifique as colunas 'Data', 'Qtd.M³' e 'Custo' no Excel.")
        else:
            total_dias = len(df_final['Data'].unique())
            total_volume = df_final['Volume_M3'].sum()
            total_valor = df_final['Valor'].sum()

            st.sidebar.success(f"Dados carregados! **{total_dias}** dias de consumo.")

            # Filtros
            st.sidebar.markdown("---")
            st.sidebar.markdown("## Filtros")
            
            min_date = df_final['Data'].min().date()
            max_date = df_final['Data'].max().date()

            date_range = st.sidebar.date_input(
                "Período de Análise:",
                [min_date, max_date],
                min_value=min_date,
                max_value=max_date
            )

            # Aplica o filtro de data
            if len(date_range) == 2:
                start_date = pd.to_datetime(date_range[0])
                end_date = pd.to_datetime(date_range[1])
                df_filtrado = df_final[(df_final['Data'] >= start_date) & (df_final['Data'] <= end_date)]
            else:
                df_filtrado = df_final.copy()
                st.sidebar.warning("Selecione um intervalo de datas.")
            
            # --- CORPO DO DASHBOARD (APENAS SE HOUVER DADOS FILTRADOS) ---
            if not df_filtrado.empty:
                
                # --- MÉTRICAS CHAVE (COLUNAS) ---
                col_metrica1, col_metrica2, col_metrica3 = st.columns(3)

                total_volume_filtrado = df_filtrado['Volume_M3'].sum()
                total_valor_filtrado = df_filtrado['Valor'].sum()
                media_m3_dia = df_filtrado['Volume_M3'].mean()
                
                col_metrica1.metric(
                    label="Volume Total Consumido",
                    value=format_volume(total_volume_filtrado),
                    delta_color="off"
                )

                col_metrica2.metric(
                    label="Custo Total",
                    value=format_moeda(total_valor_filtrado),
                    delta_color="off"
                )

                col_metrica3.metric(
                    label="Média Diária de Consumo",
                    value=format_volume(media_m3_dia),
                    delta_color="off"
                )

                st.markdown("---")
                
                # --- GRÁFICO 1: ANÁLISE DIÁRIA (Volume e Valor) ---
                st.subheader("Análise Diária de Volume (m³) e Valor Gasto (R$)")

                # Preparação dos dados para o gráfico diário
                df_long_diario = apply_formatters(df_filtrado[['Data', 'Volume_M3', 'Valor']])

                # Criação do mapa de cores para o gráfico
                COR_AZUL_VOLUME = '#40b2e8' # Azul claro/turquesa para Volume
                COR_VERDE_VALOR = '#69b04f' # Verde para Valor
                cor_mapa = {'Volume_M3': COR_AZUL_VOLUME, 'Valor': COR_VERDE_VALOR}

                # Criação do gráfico de barras agrupadas
                fig_diario_agrupado = px.bar(
                    df_long_diario.melt(id_vars='Data', value_vars=['Volume_M3', 'Valor'], var_name='Variável', value_name='Valor_Real'),
                    x='Data',
                    y='Valor_Real',
                    color='Variável',
                    barmode='group',
                    color_discrete_map=cor_mapa,
                    title="Comparativo Diário de Consumo (m³) vs. Custo (R$)",
                    labels={'Data': 'Data', 'Valor_Real': 'Valor (R$ / m³)', 'Variável': 'Tipo'}
                )

                # Customização dos traços (rótulos de dados e tooltips)
                fig_diario_agrupado.update_traces(
                    texttemplate='%{customdata[0]}', # Exibe o valor formatado como texto no topo da barra
                    textposition='outside',
                    hovertemplate="<br>Data: %{x|%d/%m/%Y}<br>Volume: %{customdata[1]}<br>Valor: %{customdata[0]}<extra></extra>",
                    customdata=df_long_diario[['Valor (R$)', 'Volume (m³)', 'Valor']].values, # Dados para o hover
                    marker_line_width=0, # Remove bordas
                )
                
                # Customização do Layout (Remoção de Ticks e Grades)
                fig_diario_agrupado.update_layout(
                    template="plotly_dark",
                    showlegend=True,
                    legend_title_text='Métrica',
                    xaxis=dict(showgrid=False, tickformat="%d/%b/%Y", title='Data'), # Formato de data amigável
                    yaxis=dict(showgrid=False, zeroline=False, title='Volume / Valor (Escala não-comparável)'),
                    height=500
                )

                st.plotly_chart(fig_diario_agrupado, use_container_width=True)

                st.markdown("---")

                # --- GRÁFICO 2: ANÁLISE POR DIA DA SEMANA ---
                st.subheader("Análise de Consumo por Dia da Semana")

                # Agrupamento e cálculo das médias
                df_agrupado_dia_semana = df_filtrado.groupby('Dia_Semana')[['Volume_M3', 'Valor']].sum().reset_index()

                # Adiciona linha de Total Geral
                total_geral = df_agrupado_dia_semana[['Volume_M3', 'Valor']].sum()
                df_total = pd.DataFrame([['Total Geral', total_geral['Volume_M3'], total_geral['Valor']]], columns=['Dia_Semana', 'Volume_M3', 'Valor'])
                df_agrupado_dia_semana = pd.concat([df_agrupado_dia_semana, df_total], ignore_index=True)

                # Ordem correta dos dias da semana
                ordem_dias = ['Sábado', 'Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Total Geral']
                df_agrupado_dia_semana['Dia_Semana'] = pd.Categorical(df_agrupado_dia_semana['Dia_Semana'], categories=ordem_dias, ordered=True)
                df_agrupado_dia_semana.sort_values('Dia_Semana', inplace=True)
                
                # Aplica a formatação para o tooltip
                df_long_dia_semana = apply_formatters(df_agrupado_dia_semana)

                # Derrete (melt) o DataFrame para criar o gráfico agrupado
                df_long_dia_semana_melt = df_long_dia_semana.melt(
                    id_vars=['Dia_Semana'],
                    value_vars=['Volume_M3', 'Valor'],
                    var_name='Variável',
                    value_name='Valor_Real'
                )

                # Criação do gráfico de barras agrupadas por Dia da Semana
                fig_dia_semana = px.bar(
                    df_long_dia_semana_melt,
                    x='Dia_Semana',
                    y='Valor_Real',
                    color='Variável',
                    barmode='group',
                    color_discrete_map=cor_mapa, # Usa o mesmo mapa de cores
                    title="Volume e Valor por Dia da Semana",
                    labels={'Dia_Semana': 'Dia da Semana', 'Valor_Real': 'Total Acumulado (Escala não-comparável)', 'Variável': 'Métrica'}
                )

                # Customização dos rótulos de dados
                # O problema é que o rótulo de texto tem que vir da coluna formatada
                # Vamos criar o rótulo antes de derreter
                df_agrupado_dia_semana['Rotulo_Volume'] = df_agrupado_dia_semana['Volume_M3'].apply(lambda x: format_volume(x).replace(' m³', ''))
                df_agrupado_dia_semana['Rotulo_Valor'] = df_agrupado_dia_semana['Valor'].apply(lambda x: format_moeda(x).replace('R$', '').strip())

                # Re-derrete com os rótulos
                df_dia_semana_melt_com_rotulo = df_agrupado_dia_semana.melt(
                    id_vars=['Dia_Semana', 'Rotulo_Volume', 'Rotulo_Valor'],
                    value_vars=['Volume_M3', 'Valor'],
                    var_name='Variável',
                    value_name='Valor_Real'
                )
                
                # Cria a coluna final de texto a ser exibida
                df_dia_semana_melt_com_rotulo['Texto_Rotulo'] = np.where(
                    df_dia_semana_melt_com_rotulo['Variável'] == 'Volume_M3',
                    'Volume: ' + df_dia_semana_melt_com_rotulo['Rotulo_Volume'] + ' m³',
                    'Custo: R$ ' + df_dia_semana_melt_com_rotulo['Rotulo_Valor']
                )

                fig_dia_semana_final = px.bar(
                    df_dia_semana_melt_com_rotulo,
                    x='Dia_Semana',
                    y='Valor_Real',
                    color='Variável',
                    barmode='group',
                    color_discrete_map=cor_mapa,
                    text='Texto_Rotulo', # Usa a nova coluna de texto formatado
                    title="Volume e Valor por Dia da Semana",
                    labels={'Dia_Semana': 'Dia da Semana', 'Valor_Real': 'Total Acumulado (Escala não-comparável)', 'Variável': 'Métrica'}
                )

                fig_dia_semana_final.update_traces(
                    textposition='outside',
                    hovertemplate="<b>Dia: %{x}</b><br>%{text}<extra></extra>",
                    marker_line_width=0,
                )

                fig_dia_semana_final.update_layout(
                    template="plotly_dark",
                    xaxis=dict(showgrid=False, title='Dia da Semana'),
                    yaxis=dict(showgrid=False, zeroline=False, title='Volume / Valor (Escala não-comparável)'),
                    height=500,
                    showlegend=True,
                    legend_title_text='Métrica',
                )

                st.plotly_chart(fig_dia_semana_final, use_container_width=True)

                # --- INSPEÇÃO DE DADOS ---
                with st.expander("Inspeção de Dados Brutos Lidos (Para Validação)"):
                    st.dataframe(apply_formatters(df_filtrado))
            else:
                st.warning("Dados insuficientes para os gráficos. Verifique o período selecionado ou a validade dos dados.")

    else:
        st.info("Por favor, faça o upload de um arquivo Excel (.xlsx) com as colunas 'Data', 'Qtd.M³' e 'Custo'.")

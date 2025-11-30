import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from babel.numbers import format_currency # Importa a função de formatação de moeda

# ===================================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E VARIÁVEIS GLOBAIS
# ===================================================================================

st.set_page_config(
    page_title="Dashboard Análise de Água",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Definir a formatação da moeda brasileira (RS) para o Babel
CURRENCY_LOCALE = 'pt_BR'
CURRENCY_SYMBOL = 'R$'
CURRENCY_CODE = 'BRL'

# Definir cores
COR_AZUL_VOLUME = '#29C5F6'
COR_VERDE_VALOR = '#6AD44D'

# Dicionário de tradução para os dias da semana (para evitar erro de locale no Streamlit Cloud)
TRADUCAO_DIAS = {
    'Monday': 'Segunda-feira',
    'Tuesday': 'Terça-feira',
    'Wednesday': 'Quarta-feira',
    'Thursday': 'Quinta-feira',
    'Friday': 'Sexta-feira',
    'Saturday': 'Sábado',
    'Sunday': 'Domingo'
}
ORDEM_DIAS = list(TRADUCAO_DIAS.values()) # Usada para ordenação de gráficos

# ===================================================================================
# 2. FUNÇÕES DE PROCESSAMENTO
# ===================================================================================

# Cache para evitar recarregar o arquivo Excel toda vez
@st.cache_data
def carregar_e_processar_dados(uploaded_file):
    """
    Carrega o arquivo Excel, limpa e processa os dados brutos.
    Retorna o DataFrame processado e uma lista de colunas faltantes.
    """
    if uploaded_file is not None:
        try:
            # Tenta ler o arquivo Excel (openpyxl é usado por baixo dos panros)
            df_bruto = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Erro ao ler o arquivo Excel: Verifique se o arquivo está no formato XLSX e não está corrompido. Detalhe: {e}")
            return pd.DataFrame(), ["Erro de Leitura"], []

        # Colunas esperadas e suas alternativas mais prováveis
        colunas_esperadas = {
            'Data': ['Data', 'DATE', 'ROTULOS DE LINHA'],
            'Volume_M3': ['VOLUME_M3', 'QTD.M3', 'METROS CUBICOS', 'M3'],
            'Valor': ['VALOR', 'CUSTO', 'TOTAL', 'REAIS']
        }
        
        df = df_bruto.copy()
        
        # Lista de nomes de colunas originais do arquivo (para diagnóstico)
        colunas_originais = list(df.columns)

        colunas_faltantes = []
        colunas_mapeadas = {}

        # Mapeamento robusto: normaliza nomes de colunas para facilitar a busca
        
        # 1. Normaliza as colunas do DataFrame para buscar (uppercase, sem espaços/pontos/acento)
        colunas_df_normalizadas = {
            col.upper().replace(' ', '').replace('.', '').replace('³', '3'): col 
            for col in df.columns
        }
        
        # 2. Tenta mapear as colunas
        for coluna_padrao, alternativas in colunas_esperadas.items():
            encontrado = False
            for alt in alternativas:
                # Normaliza a alternativa para busca
                alt_norm = alt.upper().replace(' ', '').replace('.', '').replace('³', '3')
                
                if alt_norm in colunas_df_normalizadas:
                    # Encontrou: Renomeia a coluna original no DataFrame
                    nome_original = colunas_df_normalizadas[alt_norm]
                    df.rename(columns={nome_original: coluna_padrao}, inplace=True)
                    colunas_mapeadas[coluna_padrao] = nome_original
                    encontrado = True
                    break
            
            if not encontrado:
                colunas_faltantes.append(coluna_padrao)

        if colunas_faltantes:
            return pd.DataFrame(), colunas_faltantes, colunas_originais

        # 1. Limpeza de dados
        # Converte 'Data' para o formato datetime, ignorando erros
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        # Remove linhas onde a data é inválida (NaN)
        df.dropna(subset=['Data'], inplace=True)
        
        # Converte 'Volume_M3' e 'Valor' para números, ignorando erros
        df['Volume_M3'] = pd.to_numeric(df['Volume_M3'], errors='coerce')
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
        # Remove linhas onde Volume_M3 ou Valor são NaN ou zero (dados irrelevantes)
        df.dropna(subset=['Volume_M3', 'Valor'], inplace=True)
        df = df[(df['Volume_M3'] > 0) & (df['Valor'] > 0)]

        # 2. Criação de Colunas Auxiliares
        
        # Solução robusta para locale: GERA o nome do dia em INGLÊS e depois TRADUZ manualmente.
        df['Dia da Semana'] = df['Data'].dt.day_name().map(TRADUCAO_DIAS)
        
        df['Mês/Ano'] = df['Data'].dt.to_period('M').astype(str)
        df['Ano'] = df['Data'].dt.year

        # 3. Ordenação (necessária para os gráficos)
        df.sort_values(by='Data', inplace=True)

        return df, [], []
    
    return pd.DataFrame(), ["Arquivo não enviado"], []

# ===================================================================================
# 3. FUNÇÕES DE VISUALIZAÇÃO
# ===================================================================================

def criar_grafico_dia_semana(df):
    """Cria um gráfico de barras agrupadas de Volume e Valor por Dia da Semana."""
    
    # Usa a ordem global definida na seção 1
    global ORDEM_DIAS
    
    # Agrupa por 'Dia da Semana'
    df_agrupado = df.groupby('Dia da Semana').agg(
        {'Volume_M3': 'sum', 'Valor': 'sum'}
    ).reindex(ORDEM_DIAS).reset_index().fillna(0) # Reordena e preenche NaNs com 0

    # Adiciona a coluna de Total Geral
    df_agrupado.loc[len(df_agrupado)] = {
        'Dia da Semana': 'Total Geral',
        'Volume_M3': df_agrupado['Volume_M3'].sum(),
        'Valor': df_agrupado['Valor'].sum()
    }

    # Conversão de Valor para string formatada
    df_agrupado['Valor formatado'] = df_agrupado['Valor'].apply(
        lambda x: format_currency(x, CURRENCY_CODE, locale=CURRENCY_LOCALE)
    )

    # Cores
    cor_mapa = {'Volume_M3': COR_AZUL_VOLUME, 'Valor': COR_VERDE_VALOR}

    # Criação do gráfico
    fig_dia_semana = px.bar(
        df_agrupado,
        x='Dia da Semana',
        y=['Volume_M3', 'Valor'],
        title='Volume (m³) e Valor (R$) por Dia da Semana',
        color_discrete_map=cor_mapa,
        height=500
    )

    # Personalização dos traços
    fig_dia_semana.update_traces(
        # Rótulos de dados fora das barras
        textposition='outside', 
        # Aumenta o tamanho da fonte para 14
        textfont=dict(size=14, color='white'), 
        # Customiza o texto hover
        hovertemplate='Dia: %{x}<br>Volume: %{customdata[0]:,.2f} m³<br>Valor: %{customdata[1]}<extra></extra>',
        # Dados para o hover
        customdata=np.stack((df_agrupado['Volume_M3'], df_agrupado['Valor formatado']), axis=-1)
    )

    # Personalização do layout
    fig_dia_semana.update_layout(
        # Remove título do eixo Y
        yaxis_title=None, 
        # Remove o grid e tick labels do eixo Y
        yaxis=dict(showgrid=False, showticklabels=False, title='Volume (m³) / Valor (R$)'), 
        # Remove o grid e tick labels do eixo X
        xaxis=dict(showgrid=False, showticklabels=True),
        # Cor de fundo do gráfico
        plot_bgcolor='rgba(0, 0, 0, 0)', 
        # Cor do papel
        paper_bgcolor='rgba(0, 0, 0, 0)', 
        # Cor do título
        title_font_color='white',
        # Cor da legenda
        legend_title_font_color='white',
        # Posição da legenda
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Ajusta o eixo Y para o Volume_M3
    # A segunda coluna ('Valor') será exibida no eixo Y secundário (já que 'Valor' é muito maior que 'Volume_M3')
    fig_dia_semana.update_yaxes(
        # Volume_M3 (primeira série)
        title_text="Volume (m³)", secondary_y=False, 
        showgrid=False, showticklabels=False
    )
    
    # Ajusta o eixo Y para o Valor
    fig_dia_semana.update_yaxes(
        # Valor (segunda série)
        title_text="Valor (R$)", secondary_y=True, 
        showgrid=False, showticklabels=False
    )

    st.plotly_chart(fig_dia_semana, use_container_width=True)


def criar_grafico_longo_diario(df):
    """Cria um gráfico de barras com o histórico Volume vs Valor ao longo do tempo."""

    # Agrupamento diário
    df_long_diario = df.groupby('Data').agg(
        {'Volume_M3': 'sum', 'Valor': 'sum'}
    ).reset_index()

    # Conversão de Data para string formatada
    df_long_diario['Data formatada'] = df_long_diario['Data'].dt.strftime('%d/%m/%Y')
    
    # Conversão de Valor para string formatada
    df_long_diario['Valor formatado'] = df_long_diario['Valor'].apply(
        lambda x: format_currency(x, CURRENCY_CODE, locale=CURRENCY_LOCALE)
    )

    # Cores
    cor_mapa = {'Volume_M3': COR_AZUL_VOLUME, 'Valor': COR_VERDE_VALOR}

    # Criação do gráfico
    fig_longo_agrupado = px.bar(
        df_long_diario,
        x='Data',
        y=['Volume_M3', 'Valor'],
        title='Análise Diária de Volume (m³) e Valor Gasto (R$)',
        color_discrete_map=cor_mapa,
        height=500
    )

    # Personalização dos traços
    fig_longo_agrupado.update_traces(
        # Posição do texto, tamanho da fonte e cor (fora das barras)
        textposition='outside', 
        textfont=dict(size=14, color='white'), 
        # Customiza o texto hover
        hovertemplate='Data: %{customdata[0]}<br>Volume: %{customdata[1]:,.2f} m³<br>Valor: %{customdata[2]}<extra></extra>',
        # Dados para o hover
        customdata=np.stack((df_long_diario['Data formatada'], df_long_diario['Volume_M3'], df_long_diario['Valor formatado']), axis=-1)
    )

    # Personalização do layout
    fig_longo_agrupado.update_layout(
        # Remove título do eixo Y
        yaxis_title=None, 
        # Remove o grid e tick labels do eixo Y
        yaxis=dict(showgrid=False, showticklabels=False), 
        # Remove o grid do eixo X
        xaxis=dict(showgrid=False),
        # Cor de fundo do gráfico
        plot_bgcolor='rgba(0, 0, 0, 0)', 
        # Cor do papel
        paper_bgcolor='rgba(0, 0, 0, 0)',
        # Cor do título
        title_font_color='white',
        # Cor da legenda
        legend_title_font_color='white',
        # Posição da legenda
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig_longo_agrupado, use_container_width=True)

# ===================================================================================
# 4. LAYOUT DO DASHBOARD (Streamlit)
# ===================================================================================

st.title("💧 Análise de Volume e Custo de Água (m³ vs. R$)")

# --- Barra Lateral (Sidebar) ---
st.sidebar.header("Passo 1: Faça o upload do arquivo")
uploaded_file = st.sidebar.file_uploader(
    "Excel (xlsx)", 
    type=['xlsx', 'xls'],
    help="O arquivo deve conter as colunas 'Data', 'Volume_M3' (ou 'Qtd.M³') e 'Valor' (ou 'Custo')."
)

# Inicializa o DataFrame vazio e a lista de erros
df_processado = pd.DataFrame()
colunas_faltantes = ["Nenhum dado processado"]
colunas_originais_lidas = []
dados_carregados = False

# Processamento condicional após o upload do arquivo
if uploaded_file is not None:
    # Chama a função de processamento
    df_processado, colunas_faltantes, colunas_originais_lidas = carregar_e_processar_dados(uploaded_file)
    
    # Verifica se o DataFrame tem dados e se não há colunas faltantes
    if not df_processado.empty and not colunas_faltantes:
        dados_carregados = True
    else:
        dados_carregados = False


# --- Seção Principal ---

if not uploaded_file:
    st.info("Aguardando o upload de um arquivo Excel para iniciar a análise.")

elif not dados_carregados:
    st.error(f"Erro ao carregar ou processar os dados. Verifique a estrutura do seu arquivo.")
    
    # Mensagem específica para colunas faltantes
    if "Erro de Leitura" in colunas_faltantes:
        st.warning("Não foi possível ler o arquivo. Certifique-se de que é um arquivo Excel (.xlsx) válido e não está protegido por senha.")
    elif colunas_faltantes and colunas_faltantes[0] != "Arquivo não enviado":
        st.warning(f"O arquivo foi carregado, mas as colunas necessárias estão faltando ou não foram reconhecidas. Colunas esperadas: Data, Volume_M3, Valor. Nomes de colunas lidas no seu arquivo: {', '.join(colunas_originais_lidas)}")
    elif df_processado.empty:
        st.warning("O arquivo foi carregado, mas o DataFrame está vazio após o processamento (filtros de data/valor). Verifique se as colunas 'Data', 'Volume_M3' e 'Valor' (ou equivalentes) estão preenchidas corretamente e contêm valores maiores que zero.")
    
    # Se houver dados brutos (após erro), exibe a inspeção
    if not df_processado.empty:
        with st.expander("Inspeção de Dados Brutos Lidos (Para Validação)"):
            st.dataframe(df_processado.head(20))

else:
    # --- FILTROS ---
    st.sidebar.header("Passo 2: Filtros de Período")

    # Mês/Ano único
    meses_disponiveis = df_processado['Mês/Ano'].unique()
    mes_ano_selecionado = st.sidebar.selectbox(
        "Selecione o Mês/Ano para a Análise Diária:",
        options=meses_disponiveis,
        index=len(meses_disponiveis) - 1 # Padrão para o último mês
    )
    
    # Filtra o DataFrame
    df_filtrado_diario = df_processado[df_processado['Mês/Ano'] == mes_ano_selecionado]

    # --- MÉTRICAS (KPIs) ---
    col1, col2, col3, col4 = st.columns(4)

    # Cálculo dos KPIs
    total_volume = df_processado['Volume_M3'].sum()
    total_valor = df_processado['Valor'].sum()
    volume_medio_diario = df_processado['Volume_M3'].mean()
    valor_medio_diario = df_processado['Valor'].mean()
    
    # Formatação dos KPIs
    valor_formatado_total = format_currency(total_valor, CURRENCY_CODE, locale=CURRENCY_LOCALE)
    valor_formatado_medio = format_currency(valor_medio_diario, CURRENCY_CODE, locale=CURRENCY_LOCALE)
    
    col1.metric("Volume Total (m³)", f"{total_volume:,.2f} m³")
    col2.metric("Custo Total (R$)", valor_formatado_total)
    col3.metric("Volume Médio Diário (m³)", f"{volume_medio_diario:,.2f} m³")
    col4.metric("Custo Médio Diário (R$)", valor_formatado_medio)

    st.markdown("---")
    
    # --- GRÁFICOS ---
    
    # Gráfico 1: Análise Diária (Filtrada por Mês)
    st.subheader(f"Comparativo Diário de Consumo no Mês: {mes_ano_selecionado}")
    if not df_filtrado_diario.empty:
        criar_grafico_longo_diario(df_filtrado_diario)
    else:
        st.warning("Dados insuficientes para o gráfico diário no mês selecionado.")

    st.markdown("---")

    # Gráfico 2: Análise por Dia da Semana (Total do Período)
    st.subheader("Volume e Valor por Dia da Semana (Total do Período)")
    criar_grafico_dia_semana(df_processado)

    st.markdown("---")

    # Tabela de Inspeção Final
    with st.expander("Inspeção de Dados Processados (Para Validação)"):
        st.dataframe(df_processado.head())
        st.dataframe(df_processado.describe())
        st.dataframe(df_processado) # Tabela completa no final

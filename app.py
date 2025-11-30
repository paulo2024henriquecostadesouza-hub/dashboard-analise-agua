# Importa bibliotecas essenciais
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re # Importa a biblioteca de expressões regulares
import locale # Importa para configurar a localidade

# Configura a localidade para português do Brasil para formatação de datas
# Isso é importante para que os meses apareçam em português
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')


# --- INJEÇÃO DE CSS PERSONALIZADO (Design Azul) ---
st.markdown("""
<style>
/* 1. Sidebar (Fundo Azul, Texto Branco) */
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {
    background-color: #00AFEF;
    color: white; /* Garante que o texto da sidebar seja branco */
}
/* Garante que todos os elementos de texto na sidebar sejam brancos */
.st-sidebar .st-header, .st-sidebar h1, .st-sidebar h2, .st-sidebar h3, .st-sidebar label,
div[data-testid="stMultiSelect"] label, div[data-testid="stSidebarHeader"] h1 {
    color: white !important;
}

/* 2. Fundo Principal (Main Page) - Fundo Azul, Texto Branco */
[data-testid="stAppViewBlockContainer"] {
    background-color: #00AFEF;
}
/* Garante que o texto principal (incluindo títulos, subtítulos e métricas) seja branco */
h1, h2, h3, .stMarkdown, .st-metric-label, .st-metric-value, .st-metric-delta {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# --- Configuração da Página e Título ---
st.set_page_config(page_title="Dashboard de Análise de Água", page_icon="💧", layout="wide")
st.title("💧 Dashboard de Análise de Abastecimento de Água")
st.markdown("---")

# Nome da aba que contém os dados agregados/cálculos
SHEET_NAME = 'Dados Dashboard' 

# Função para formatação de moeda
def format_currency(value):
    # Formatação brasileira: R$ X.XXX,XX
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Função para formatação de volume
def format_volume(value):
    # Formatação brasileira: X.XXX,XX m³
    return f"{value:,.2f} m³".replace(",", "X").replace(".", ",").replace("X", ".")

# Cores Padrão
COR_VERDE_VALOR = '#4CAF50' 
COR_AZUL_VOLUME = '#00AFEF'
COR_AZUL_ESCURO = '#002C5E' # Para contraste no gráfico de pizza

# --- 1. Componente de Upload e Leitura de Dados ---
uploaded_file = st.sidebar.file_uploader(
    "Passo 1: Faça o upload do arquivo Excel (.xlsx)", 
    type=['xlsx']
)

# Bloco principal de processamento
if uploaded_file is not None:
    st.info(f"Processando arquivo '{uploaded_file.name}' da aba '{SHEET_NAME}'...")
    
    try:
        # --- 1. LEITURA DE MÚLTIPLAS TABELAS ---
        
        # TABELA 1: Mês, M³ e Custo (A4:C17)
        df_mes = pd.read_excel(uploaded_file, sheet_name=SHEET_NAME, header=3, nrows=14, usecols='A:C')
        df_mes = df_mes.rename(columns={
            df_mes.columns[0]: 'Mês',
            df_mes.columns[1]: 'Volume_M3',
            df_mes.columns[2]: 'Valor'
        }).dropna(subset=['Mês'])
        # Conversão robusta
        df_mes['Valor'] = pd.to_numeric(df_mes['Valor'], errors='coerce') 
        df_mes['Volume_M3'] = pd.to_numeric(df_mes['Volume_M3'], errors='coerce')
        
        # TABELA 2: M³ por Fornecedor (A22:B25)
        df_fornecedor_m3 = pd.read_excel(uploaded_file, sheet_name=SHEET_NAME, header=21, nrows=4, usecols='A:B')
        df_fornecedor_m3 = df_fornecedor_m3.rename(columns={
            df_fornecedor_m3.columns[0]: 'Fornecedor',
            df_fornecedor_m3.columns[1]: 'Volume_M3'
        }).dropna(subset=['Fornecedor'])
        df_fornecedor_m3['Volume_M3'] = pd.to_numeric(df_fornecedor_m3['Volume_M3'], errors='coerce')
        
        # TABELA 3: Valor por Fornecedor (G22:H25)
        df_fornecedor_valor = pd.read_excel(uploaded_file, sheet_name=SHEET_NAME, header=21, nrows=4, usecols='G:H')
        df_fornecedor_valor = df_fornecedor_valor.rename(columns={
            df_fornecedor_valor.columns[0]: 'Fornecedor',
            df_fornecedor_valor.columns[1]: 'Valor'
        }).dropna(subset=['Fornecedor'])
        df_fornecedor_valor['Valor'] = pd.to_numeric(df_fornecedor_valor['Valor'], errors='coerce')
        
        # TABELA 4: Valor e M³ por Dia da Semana (G5:I12) - CORRIGIDO header=3 e nrows=9
        df_dia_semana = pd.read_excel(uploaded_file, sheet_name=SHEET_NAME, header=3, nrows=9, usecols='G:I')
        df_dia_semana = df_dia_semana.rename(columns={
            df_dia_semana.columns[0]: 'Dia_Semana',
            df_dia_semana.columns[1]: 'Volume_M3',
            df_dia_semana.columns[2]: 'Valor'
        }).dropna(subset=['Dia_Semana'])
        # Conversão robusta
        df_dia_semana['Valor'] = pd.to_numeric(df_dia_semana['Valor'], errors='coerce')
        df_dia_semana['Volume_M3'] = pd.to_numeric(df_dia_semana['Volume_M3'], errors='coerce')

        # TABELA 5: Valor e M³ Diário (Q5:S505) - LENDO ATÉ 501 LINHAS DE DADOS
        # Lendo com o header=3 (Linha 4 do Excel) e forçando a primeira coluna como string (dtype={'Q': str})
        df_diario_bruto = pd.read_excel(
            uploaded_file, 
            sheet_name=SHEET_NAME, 
            header=3, 
            nrows=502, 
            usecols='Q:S', 
            dtype={'Rótulos de Linha': str} # Garante que a coluna de data seja lida como texto
        )
        df_diario = df_diario_bruto.rename(columns={
            df_diario_bruto.columns[0]: 'Data',
            df_diario_bruto.columns[1]: 'Volume_M3_Diario',
            df_diario_bruto.columns[2]: 'Valor_Diario'
        })
        
        # --- CORREÇÃO DA LEITURA DE DATA E CONVERSÃO ---
        
        # 1. Limpa a coluna de data, removendo possíveis prefixos de formatação (ex: ^)
        if df_diario['Data'].dtype == 'object':
            df_diario['Data'] = df_diario['Data'].astype(str).str.replace(r'[\^,]', '', regex=True)
            
        # 2. Tenta converter para data, usando 'coerce' para NaN em caso de erro
        try:
            df_diario['Data'] = pd.to_datetime(
                df_diario['Data'], 
                format='%d/%b', # Tenta formato com mês abreviado, como '02/jan'
                errors='coerce',
                dayfirst=True 
            )
        except ValueError:
            # Caso a primeira tentativa falhe
             df_diario['Data'] = pd.to_datetime(
                df_diario['Data'], 
                errors='coerce',
                dayfirst=True
            )

        # 3. CORREÇÃO DE ANO: Se o ano for 1900, altera para 2025.
        ANO_CORRIGIDO = 2025
        df_diario['Data'] = df_diario['Data'].apply(
            lambda dt: dt.replace(year=ANO_CORRIGIDO) if pd.notna(dt) and dt.year == 1900 else dt
        )


        df_diario['Volume_M3_Diario'] = pd.to_numeric(df_diario['Volume_M3_Diario'], errors='coerce')
        df_diario['Valor_Diario'] = pd.to_numeric(df_diario['Valor_Diario'], errors='coerce')

        # Dropa NaNs, garantindo que só linhas com Data E Volume/Valor estejam presentes
        df_diario_plot = df_diario.dropna(subset=['Data', 'Volume_M3_Diario', 'Valor_Diario'])

        # --- FEEDBACK PARA O USUÁRIO ---
        st.sidebar.subheader("Status dos Dados Diários")
        num_rows_diario = len(df_diario_plot)
        if num_rows_diario == 0:
            st.sidebar.error("❌ Nenhuma linha válida encontrada. Verifique as colunas Q, R, S na linha 5 do Excel.")
        else:
            st.sidebar.success(f"✅ {num_rows_diario} linhas de dados diários válidos prontas (Ano fixado em {ANO_CORRIGIDO}).")

        
        # --- PREPARAÇÃO DE DADOS COMBINADOS PARA FORNECEDOR (COM FILTRAGEM) ---
        
        # Filtrar a linha "Total Geral"
        # Aplicar filtro para remover linhas com 'total' ou NaN em 'Fornecedor'
        filtro_fornecedor_m3 = ~df_fornecedor_m3['Fornecedor'].astype(str).str.contains('total|nan', case=False, na=False)
        df_fornecedor_m3_filtrado = df_fornecedor_m3[filtro_fornecedor_m3].copy().dropna(subset=['Fornecedor'])

        filtro_fornecedor_valor = ~df_fornecedor_valor['Fornecedor'].astype(str).str.contains('total|nan', case=False, na=False)
        df_fornecedor_valor_filtrado = df_fornecedor_valor[filtro_fornecedor_valor].copy().dropna(subset=['Fornecedor'])
        
        # Combina volume e valor na mesma tabela para o gráfico de barras lateral
        df_fornecedor_combinado = pd.merge(
            df_fornecedor_m3_filtrado, 
            df_fornecedor_valor_filtrado, 
            on='Fornecedor',
            how='inner' # Garante que só fornecedores presentes em ambas sejam usados
        )
        
        # --- 2. CÁLCULO E EXIBIÇÃO DE KPIS GERAIS ---
        st.header("Métricas Globais de Abastecimento")
        col1, col2, col3, col4 = st.columns(4)

        # Agora usamos a tabela FILTRADA (df_diario_plot) para os Totais
        total_valor_geral = df_diario_plot['Valor_Diario'].sum()
        total_volume_geral = df_diario_plot['Volume_M3_Diario'].sum()
        
        # Usa a Tabela Mensal para médias (ignorando NaNs criados pela coerção)
        media_mensal_valor = df_mes['Valor'].mean()
        media_mensal_volume = df_mes['Volume_M3'].mean()
        

        col1.metric(label="Valor Total Gasto (Período)", value=format_currency(total_valor_geral))
        col2.metric(label="Volume Total Consumido (m³)", value=format_volume(total_volume_geral))
        col3.metric(label="Média Mensal de Gasto", value=format_currency(media_mensal_valor))
        col4.metric(label="Média Mensal de Volume (m³)", value=format_volume(media_mensal_volume))

        st.markdown("---")

        # --- 3. GRÁFICOS DE ANÁLISE ---
        
        # Análise Mensal
        st.header("Análise de Custo (R$) e Volume (m³) por Mês")
        
        ordem_dos_meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                          'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        
        # Garante que apenas meses válidos (não NaN) sejam plotados
        df_mes_plot = df_mes.dropna(subset=['Volume_M3', 'Valor'])

        fig_agrupado = go.Figure()

        fig_agrupado.add_trace(go.Bar(
            x=df_mes_plot['Mês'],
            y=df_mes_plot['Volume_M3'],
            name='Volume (m³)',
            marker_color=COR_AZUL_VOLUME,
            # Rótulo de Dados (Volume)
            text=df_mes_plot['Volume_M3'].apply(format_volume),
            textposition='outside',
            textfont=dict(size=10, color='white')
        ))

        fig_agrupado.add_trace(go.Bar(
            x=df_mes_plot['Mês'],
            y=df_mes_plot['Valor'],
            name='Valor (R$)',
            marker_color=COR_VERDE_VALOR,
            # Rótulo de Dados (Valor)
            text=df_mes_plot['Valor'].apply(lambda x: format_currency(x)), # Mantido R$ no rótulo
            textposition='outside',
            textfont=dict(size=10, color='white')
        ))

        fig_agrupado.update_layout(
            barmode='group',
            xaxis={'categoryorder':'array', 'categoryarray':ordem_dos_meses},
            # Remove eixo Y, linhas de grade e título
            yaxis={'showgrid': False, 'showline': False, 'showticklabels': False, 'title': ''}, 
            title_text='Comparativo Mensal de Volume e Custo',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # Remove grade e título do Eixo X
        fig_agrupado.update_xaxes(title_text="Mês", showgrid=False) 
        
        st.plotly_chart(fig_agrupado, use_container_width=True)

        st.markdown("---")

        # --- Análise por Fornecedor ---
        st.header("Análise de Volume e Valor por Fornecedor")
        col_f1, col_f2 = st.columns([1, 2])

        
        # 1. Gráfico de Pizza (Donut) - Sem alteração de eixo/rótulo
        with col_f1:
            st.subheader("Percentual de Abastecimento (m³)")
            
            # Usa a tabela filtrada e garante que não há NaNs em Volume_M3
            df_fornecedor_pie = df_fornecedor_m3_filtrado.dropna(subset=['Volume_M3'])
            if not df_fornecedor_pie.empty:
                fig_volume_pie = px.pie(
                    df_fornecedor_pie, 
                    names='Fornecedor', 
                    values='Volume_M3', 
                    hole=.6, # Transforma em Donut
                    title='Distribuição de Volume (m³)',
                    color='Fornecedor',
                    color_discrete_map={'ACQUAMEL': COR_AZUL_ESCURO, 'SABESP': COR_AZUL_VOLUME}, 
                )
                
                fig_volume_pie.update_traces(
                    textinfo='percent', 
                    hovertemplate='%{label}<br>Volume: %{value} m³<extra></extra>',
                    marker=dict(line=dict(color='#000000', width=1))
                )
                
                fig_volume_pie.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', 
                    paper_bgcolor='rgba(0,0,0,0)', 
                    font_color='white',
                    showlegend=True,
                    margin=dict(t=50, b=0, l=0, r=0)
                )
                st.plotly_chart(fig_volume_pie, use_container_width=True)
            else:
                st.warning("Dados de volume por fornecedor insuficientes para o gráfico de pizza.")


        # 2. Gráfico de Colunas Laterais (Barra Horizontal) - Custo (R$) e Volume (m³)
        with col_f2:
            st.subheader("Comparativo Custo (R$) e Volume (m³)") 
            
            df_forn_plot = df_fornecedor_combinado.dropna(subset=['Volume_M3', 'Valor'])

            if not df_forn_plot.empty:
                # Gráfico de barras horizontais
                fig_bar_forn = go.Figure()

                # Adiciona as barras de Volume (m³)
                fig_bar_forn.add_trace(go.Bar(
                    y=df_forn_plot['Fornecedor'],
                    x=df_forn_plot['Volume_M3'],
                    name='Volume (m³)',
                    orientation='h',
                    marker_color=COR_AZUL_VOLUME,
                    # Rótulo de Dados (Volume)
                    text=df_forn_plot['Volume_M3'].apply(lambda x: f"{x:,.0f} m³".replace(",", ".")),
                    textposition='outside',
                    textfont=dict(size=12, color='white')
                ))

                # Adiciona as barras de Custo (R$)
                fig_bar_forn.add_trace(go.Bar(
                    y=df_forn_plot['Fornecedor'],
                    x=df_forn_plot['Valor'],
                    name='Custo (R$)',
                    orientation='h',
                    marker_color=COR_VERDE_VALOR,
                    # Rótulo de Dados (Valor)
                    text=df_forn_plot['Valor'].apply(lambda x: format_currency(x)),
                    textposition='outside',
                    textfont=dict(size=12, color='white')
                ))

                fig_bar_forn.update_layout(
                    barmode='group',
                    height=350,
                    yaxis=dict(autorange="reversed", showgrid=False), # Retira grade do Eixo Y
                    # Remove eixo X, linhas de grade e título
                    xaxis=dict(showgrid=False, showline=False, showticklabels=False, title=''), 
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=0, r=100, t=50, b=0)
                )
                
                # Remove título do Eixo Y (o nome do fornecedor permanece)
                fig_bar_forn.update_yaxes(title_text="", showgrid=False)
                
                st.plotly_chart(fig_bar_forn, use_container_width=True)
            else:
                st.warning("Dados combinados de volume e valor por fornecedor insuficientes para o gráfico de barras.")


        st.markdown("---")
        
        # Análise Semanal 
        st.header("Análise de Consumo por Dia da Semana")
        
        ordem_semanal = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
        
        # Garante que apenas dias válidos (não NaN) sejam plotados
        df_dia_plot = df_dia_semana.dropna(subset=['Volume_M3', 'Valor'])

        if not df_dia_plot.empty:
            # Reorganiza o DataFrame para o Plotly Express para facilitar a adição de rótulos
            df_long = pd.melt(df_dia_plot, id_vars=['Dia_Semana'], value_vars=['Volume_M3', 'Valor'], 
                              var_name='Variável', value_name='Valor_Real')
            
            # Adiciona rótulos formatados para display (R$ e m³)
            def format_label(row):
                if row['Variável'] == 'Valor':
                    return format_currency(row['Valor_Real'])
                return format_volume(row['Valor_Real'])
                
            df_long['Rótulo'] = df_long.apply(format_label, axis=1)

            fig_dia_semana = px.bar(
                df_long,
                x='Dia_Semana',
                y='Valor_Real',
                color='Variável',
                text='Rótulo', # Usa a coluna de rótulos formatados
                title='Volume e Valor por Dia da Semana',
                barmode='group',
                category_orders={"Dia_Semana": ordem_semanal},
                color_discrete_map={'Volume_M3': COR_AZUL_VOLUME, 'Valor': COR_VERDE_VALOR} 
            )
            
            fig_dia_semana.update_traces(
                textposition='outside',
                textfont=dict(size=10, color='white')
            )

            fig_dia_semana.update_layout(
                # Remove eixo Y, linhas de grade e título
                yaxis=dict(showgrid=False, showline=False, showticklabels=False, title=''), 
                xaxis=dict(showgrid=False, title_text="Dia da Semana"), # Remove grade do Eixo X
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)', 
                font_color='white',
                legend_title_text=''
            )
            st.plotly_chart(fig_dia_semana, use_container_width=True)
        else:
            st.warning("Dados de consumo por dia da semana insuficientes para o gráfico.")

        
        st.markdown("---")

        # Análise Diária (Volume e Valor por Data) - NOVO GRÁFICO DE BARRA AGRUPADA
        st.header("Análise Diária de Volume (m³) e Valor Gasto (R$)")
        
        # Garante que apenas dias válidos (não NaN) sejam plotados
        # df_diario_plot JÁ FOI CRIADO E FILTRADO NO INÍCIO DO CÓDIGO!
        

        if not df_diario_plot.empty:
            
            # Prepara a estrutura para o Plotly
            df_long_diario = pd.melt(
                df_diario_plot, 
                id_vars=['Data'], 
                value_vars=['Volume_M3_Diario', 'Valor_Diario'], 
                var_name='Variável', 
                value_name='Valor_Real'
            )
            
            # Adiciona rótulos formatados para display (R$ e m³)
            def format_daily_label(row):
                if row['Variável'] == 'Valor_Diario':
                    return format_currency(row['Valor_Real'])
                return format_volume(row['Valor_Real'])
                
            df_long_diario['Rótulo'] = df_long_diario.apply(format_daily_label, axis=1)

            # Mapeamento de cores
            cor_mapa = {'Volume_M3_Diario': COR_AZUL_VOLUME, 'Valor_Diario': COR_VERDE_VALOR}
            
            # Criação do gráfico de barras agrupadas
            fig_diario_agrupado = px.bar(
                df_long_diario,
                x='Data',
                y='Valor_Real',
                color='Variável',
                text='Rótulo', # Usa a coluna de rótulos formatados
                title='Comparativo Diário de Consumo (m³) vs. Custo (R$)',
                barmode='group',
                color_discrete_map=cor_mapa 
            )
            
            # Customização dos traços
            fig_diario_agrupado.update_traces(
                textposition='outside', # Rótulos de dados fora das barras
                textfont=dict(size=14, color='white'), # *** Aumentado o tamanho da fonte para 14 ***
                hovertemplate="Data: %{x|%d/%m/%Y}<br>Volume: %{customdata[0]} m³<br>Valor: R$ %{customdata[1]}<extra></extra>",
                customdata=df_diario_plot[['Volume_M3_Diario', 'Valor_Diario']].values # Dados para o hover
            )

            # Customização do Layout (Remoção de Eixos e Grades)
            fig_diario_agrupado.update_layout(
                # Remove eixo Y, linhas de grade e tick labels
                yaxis=dict(showgrid=False, showline=False, showticklabels=False, title=''), 
                # Remove linhas de grade e título do Eixo X
                xaxis=dict(
                    showgrid=False, 
                    title_text="",
                    # *** Força a exibição de todos os ticks e formata para dd/MMM em pt-BR ***
                    tickmode='array',
                    tickvals=df_diario_plot['Data'], # Todas as datas válidas
                    tickformat='%d/%b', # Formato Dia/Mês abreviado (jan, fev, etc.)
                    tickangle=-45, # Inclina os rótulos para melhor leitura
                    showline=False,
                    showticklabels=True
                ), 
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)', 
                font_color='white',
                legend_title_text='',
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=1.02, 
                    xanchor="right", 
                    x=1,
                    traceorder='normal'
                )
            )
            
            # Renomeia os itens da legenda manualmente após a criação do gráfico
            fig_diario_agrupado.for_each_trace(lambda t: t.update(name = 'Volume (m³)' if t.name == 'Volume_M3_Diario' else 'Valor (R$)'))

            st.plotly_chart(fig_diario_agrupado, use_container_width=True)
            
        else:
            st.warning("Dados diários insuficientes para o gráfico. Verifique a coluna 'Data' na tabela de Inspeção.")

        
        # --- Seção para inspeção (MANTIDA) ---
        with st.expander("Inspeção de Dados Brutos Lidos (Para Validação)"):
            st.subheader("Tabela Mensal (A4:C17)")
            st.dataframe(df_mes)
            st.subheader("Tabela Fornecedor M³ (A22:B25) - Filtrada")
            st.dataframe(df_fornecedor_m3_filtrado)
            st.subheader("Tabela Fornecedor Valor (G22:H25) - Filtrada")
            st.dataframe(df_fornecedor_valor_filtrado)
            st.subheader("Tabela Dia da Semana (G5:I12)")
            st.dataframe(df_dia_semana)
            st.subheader("Tabela Diária Bruta e Filtrada (Q5:S505) - Olhe a coluna 'Data'!")
            st.caption("A tabela bruta mostra o que foi lido. A tabela filtrada é usada nos gráficos (se vazia, o erro é na leitura/conversão de dados).")
            st.dataframe(df_diario_bruto)
            st.dataframe(df_diario_plot)
        
    except Exception as e:
        st.error(f"ERRO CRÍTICO ao construir o Dashboard. Verifique se o formato das tabelas (cabeçalhos e colunas) está consistente com o esperado. Mensagem de erro: {e}")
        st.info("Se o erro persistir, por favor, copie e cole a mensagem de erro completa.")

else:
    st.info("Aguardando o upload do arquivo Excel para visualizar o dashboard completo.")
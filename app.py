import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from babel.numbers import format_currency # Importa a função de formatação de moeda

# --- Funções de Ajuda ---

@st.cache_data
def load_data(uploaded_file):
    """Carrega o arquivo Excel e faz um pré-processamento básico."""
    try:
        df = pd.read_excel(uploaded_file)
        
        # Renomear as colunas para facilitar o uso
        df.columns = ['Data', 'FORNECEDOR', 'Volume_M3', 'Valor']
        
        # Limpeza e conversão de tipos
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)
        df['Volume_M3'] = pd.to_numeric(df['Volume_M3'], errors='coerce')
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
        
        df = df.dropna(subset=['Data', 'Volume_M3', 'Valor'])
        df['Dia_Semana'] = df['Data'].dt.day_name(locale='pt_BR') # Tenta usar pt_BR para nomes de dias
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar os dados: {e}")
        return pd.DataFrame()

# Função de formatação para Real (R$) usando Babel
def format_real(value):
    """Formata um número como moeda brasileira (R$)."""
    # Usa 'pt_BR' para formatação e 'BRL' para o símbolo da moeda
    return format_currency(value, 'BRL', locale='pt_BR')

# --- Constantes de Cores ---
COR_VOLUME = '#1f77b4'  # Azul
COR_VALOR = '#2ca02c'   # Verde
COR_VERDE_VALOR = '#2ca02c'
COR_AZUL_VOLUME = '#1f77b4'

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Dashboard Análise de Água")
st.title("💧 Análise de Volume e Custo de Água (m³ vs. R$)")

# --- Upload do Arquivo ---
uploaded_file = st.sidebar.file_uploader("Passo 1: Faça o upload do arquivo Excel (xlsx)", type=["xlsx"])

df_full = pd.DataFrame()
if uploaded_file:
    df_full = load_data(uploaded_file)
    
    if df_full.empty:
        st.warning("O arquivo foi carregado, mas o DataFrame está vazio após o processamento. Verifique se as colunas 'Data', 'Volume_M3' e 'Valor' (ou equivalentes) estão preenchidas corretamente.")
    else:
        st.sidebar.success("Arquivo carregado com sucesso!")
        
        # Filtrar o DataFrame apenas para os dados processados válidos
        df_valid = df_full.dropna(subset=['Data', 'Volume_M3', 'Valor'])
        
        # --- Cálculo de Resumo ---
        total_volume = df_valid['Volume_M3'].sum()
        total_valor = df_valid['Valor'].sum()
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        # O número é formatado manualmente aqui para evitar dependência de locale
        col1.metric("Volume Total (m³)", f"{total_volume:,.2f}".replace(",", "_").replace(".", ",").replace("_", "."), help="Soma total do consumo em metros cúbicos.")
        col2.metric("Valor Total (R$)", format_real(total_valor), help="Soma total do valor gasto.")
        
        st.markdown("---")
        
        # --- Análise Mensal ---
        
        st.header("Análise de Custo (R$) e Volume (m³) por Meses")
        df_mensal = df_valid.set_index('Data').resample('M').agg({
            'Volume_M3': 'sum',
            'Valor': 'sum'
        }).reset_index()
        df_mensal['Mês'] = df_mensal['Data'].dt.strftime('%B').str.capitalize()
        
        # Mapeamento para garantir a ordem correta dos meses
        meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        df_mensal['Mês'] = pd.Categorical(df_mensal['Mês'], categories=meses_ordem, ordered=True)
        df_mensal = df_mensal.sort_values('Mês')

        # Preparar dados para o gráfico (melt)
        df_mensal_melt = df_mensal.melt(id_vars='Mês', value_vars=['Volume_M3', 'Valor'],
                                        var_name='Métrica', value_name='Valor_Métrica')
        
        # Criar o gráfico
        fig_mensal = px.bar(
            df_mensal_melt,
            x='Mês',
            y='Valor_Métrica',
            color='Métrica',
            barmode='group',
            title='Comparativo Mensal de Volume e Custo',
            color_discrete_map={'Volume_M3': COR_AZUL_VOLUME, 'Valor': COR_VERDE_VALOR},
            height=500,
            
        )
        
        # Customização: Adicionar rótulos de dados
        fig_mensal.update_traces(texttemplate='%{y:,.2f}', textposition='outside')
        fig_mensal.update_layout(
            xaxis_title='Mês',
            yaxis_title='Volume/Valor (Escala Dupla, Aprox.)',
            uniformtext_minsize=8, 
            uniformtext_mode='hide',
            legend_title_text='Métrica'
        )
        
        st.plotly_chart(fig_mensal, use_container_width=True)

        # --- Análise por Fornecedor ---
        st.markdown("---")
        st.header("Análise de Volume e Valor por Fornecedor")
        
        df_fornecedor = df_valid.groupby('FORNECEDOR').agg({
            'Volume_M3': 'sum',
            'Valor': 'sum'
        }).reset_index()

        col_left, col_right = st.columns(2)

        # Gráfico 1: Volume (m³) por Fornecedor - Donut Chart
        fig_volume_forn = px.pie(
            df_fornecedor,
            values='Volume_M3',
            names='FORNECEDOR',
            hole=.3,
            title='Distribuição de Volume (m³) por Fornecedor',
            color_discrete_sequence=px.colors.qualitative.Dark24,
        )
        # Customização: Mostrar Volume (m³) na formatação correta
        fig_volume_forn.update_traces(
            textinfo='percent+label',
            hovertemplate="Fornecedor: %{label}<br>Volume (m³): %{value:,.2f}<br>Percentual: %{percent}<extra></extra>"
        )
        col_left.plotly_chart(fig_volume_forn, use_container_width=True)

        # Gráfico 2: Valor (R$) por Fornecedor - Donut Chart
        fig_valor_forn = px.pie(
            df_fornecedor,
            values='Valor',
            names='FORNECEDOR',
            hole=.3,
            title='Distribuição de Valor (R$) por Fornecedor',
            color_discrete_sequence=px.colors.qualitative.Dark24,
        )
        # Customização: Mostrar Valor (R$) na formatação correta
        # Nota: O hover do Plotly é complexo para formatar R$ diretamente com Babel dentro dele. 
        # A formatação básica é usada, o usuário verá o R$ na métrica geral.
        fig_valor_forn.update_traces(
            textinfo='percent+label',
            hovertemplate="Fornecedor: %{label}<br>Valor (R$): %{value:,.2f}<br>Percentual: %{percent}<extra></extra>"
        )
        col_right.plotly_chart(fig_valor_forn, use_container_width=True)

        # --- Análise Diária (Volume e Valor) ---
        st.markdown("---")
        st.header("Análise Diária de Volume (m³) e Valor Gasto (R$)")

        # Dados diários agregados
        df_diario = df_valid.groupby('Data').agg({
            'Volume_M3': 'sum',
            'Valor': 'sum'
        }).reset_index()
        
        # Preparar dados para o gráfico (melt)
        df_diario_long = df_diario.melt(id_vars='Data', value_vars=['Volume_M3', 'Valor'],
                                        var_name='Métrica', value_name='Valor_Métrica')
        
        # Criar o gráfico
        fig_diario = px.bar(
            df_diario_long,
            x='Data',
            y='Valor_Métrica',
            color='Métrica',
            barmode='group',
            title='Comparativo Diário de Consumo (m³) vs. Custo (R$)',
            color_discrete_map={'Volume_M3': COR_AZUL_VOLUME, 'Valor': COR_VERDE_VALOR},
            height=550,
        )
        
        # Customização dos traços
        fig_diario.update_traces(
            texttemplate='%{y:,.2f}', # Rótulos de dados para barras
            textposition='outside',
            textfont_size=12
        )
        
        # Customização do layout
        fig_diario.update_layout(
            xaxis_title='Data',
            yaxis_title='Volume/Valor (Escala Dupla, Aprox.)',
            uniformtext_minsize=8,
            uniformtext_mode='hide',
            legend_title_text='Métrica',
            hovermode="x unified"
        )
        
        st.plotly_chart(fig_diario, use_container_width=True)

        
        # --- Análise por Dia da Semana ---
        st.markdown("---")
        st.header("Análise de Consumo por Dia da Semana")

        # Tabela dinâmica
        pivot_diario = pd.pivot_table(
            df_valid,
            values=['Volume_M3', 'Valor'],
            index=['Dia_Semana'],
            aggfunc='sum'
        ).reset_index()

        # Ordenar os dias da semana corretamente
        dias_ordem = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
        pivot_diario['Dia_Semana'] = pd.Categorical(pivot_diario['Dia_Semana'], categories=dias_ordem, ordered=True)
        pivot_diario = pivot_diario.sort_values('Dia_Semana')
        
        # Linha Total
        total_row = pd.DataFrame([['Total Geral', total_volume, total_valor]], columns=['Dia_Semana', 'Volume_M3', 'Valor'])
        df_diario_semana = pd.concat([pivot_diario, total_row], ignore_index=True)

        # Preparar dados para o gráfico (melt)
        df_diario_semana_long = df_diario_semana.melt(id_vars='Dia_Semana', value_vars=['Volume_M3', 'Valor'],
                                                     var_name='Métrica', value_name='Valor_Métrica')

        # Criar o gráfico
        fig_dia_semana = px.bar(
            df_diario_semana_long,
            x='Dia_Semana',
            y='Valor_Métrica',
            color='Métrica',
            barmode='group',
            title='Volume e Valor por Dia da Semana',
            color_discrete_map={'Volume_M3': COR_AZUL_VOLUME, 'Valor': COR_VERDE_VALOR},
            height=500
        )

        # Customização: Adicionar rótulos de dados
        fig_dia_semana.update_traces(
            texttemplate='%{y:,.2f}',
            textposition='outside'
        )
        fig_dia_semana.update_layout(
            xaxis_title='Dia da Semana',
            yaxis_title='Volume/Valor (Escala Dupla, Aprox.)',
            uniformtext_minsize=8,
            uniformtext_mode='hide',
            legend_title_text='Métrica'
        )

        st.plotly_chart(fig_dia_semana, use_container_width=True)

        # --- Tabela de Inspeção de Dados ---
        with st.expander("Inspeção de Dados Brutos Lidos (Para Validação)"):
            st.dataframe(df_valid)

else:
    st.info("Aguardando o upload do arquivo de dados para iniciar a análise.")

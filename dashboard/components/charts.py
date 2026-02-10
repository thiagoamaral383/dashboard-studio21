import streamlit as st
import altair as alt
import pandas as pd
from utils.formatters import format_currency

def render_financial_evolution(df, start_date, end_date):
    """
    Renderiza o gráfico de evolução financeira com granularidade dinâmica.
    
    Args:
        df: DataFrame contendo as colunas 'data' e 'valor'.
        start_date: Data inicial do filtro.
        end_date: Data final do filtro.
    """
    if df.empty:
        st.info("Não há dados suficientes para exibir o gráfico de evolução neste período.")
        return

    # 1. Definição de Granularidade
    # Garantir que start_date e end_date sejam datetime.date ou datetime
    # Se forem strings, converter. Assumindo que vêm do st.date_input (datetime.date)
    
    # Calcular delta em dias
    if hasattr(start_date, 'date'): # É datetime
        sd = start_date.date()
    else:
        sd = start_date
        
    if hasattr(end_date, 'date'):
        ed = end_date.date()
    else:
        ed = end_date
        
    delta = (ed - sd).days
    
    if delta <= 60:
        granularidade = 'D'
        granularidade_texto = 'Diário'
        fmt_data = '%d/%m'
    elif delta <= 180:
        granularidade = 'W-MON'
        granularidade_texto = 'Semanal'
        fmt_data = '%d/%m'
    else:
        granularidade = 'MS'
        granularidade_texto = 'Mensal'
        fmt_data = '%b/%Y'

    # 2. Processamento dos Dados
    df_proc = df.copy()
    
    # Garantir datetime
    if not pd.api.types.is_datetime64_any_dtype(df_proc['data']):
        df_proc['data'] = pd.to_datetime(df_proc['data'])
        
    # Agrupamento (Resample)
    # Primeiro definimos o índice como data para usar resample
    df_proc = df_proc.set_index('data')
    
    # Agrupar pela granularidade
    grouped = df_proc.resample(granularidade)
    
    data_points = []
    
    # Dicionário de meses em português para formatação manual se necessário
    meses_pt = {
        1: 'jan', 2: 'fev', 3: 'mar', 4: 'abr', 5: 'mai', 6: 'jun',
        7: 'jul', 8: 'ago', 9: 'set', 10: 'out', 11: 'nov', 12: 'dez'
    }
    
    for data_periodo, group in grouped:
        # Se o grupo estiver vazio, pulamos (ou podermos preencher com 0)
        # O resample cria buckets para todos os períodos.
        # Se quisermos mostrar zeros, mantemos. 
        
        # Regras de Negócio:
        # Receitas: Soma de valor > 0
        receitas = group[group['valor'] > 0]['valor'].sum()
        
        # Despesas: Soma absoluta de valor < 0
        despesas = abs(group[group['valor'] < 0]['valor'].sum())
        
        # Lucro Líquido: Soma aritmética (Receitas - |Despesas| = Soma real, pois despesas são negativas no banco)
        lucro_liquido = group['valor'].sum()
        
        # Formatar Data
        if granularidade == 'MS':
            mes_nome = meses_pt.get(data_periodo.month, '')
            data_formatada = f"{mes_nome}/{data_periodo.year}"
        else:
            data_formatada = data_periodo.strftime(fmt_data)
            
        data_points.append({
            'Data_Sort': data_periodo, # Para ordenação
            'Data_Formatada': data_formatada,
            'Receitas': receitas,
            'Despesas': despesas,
            'Lucro Líquido': lucro_liquido
        })
        
    df_chart = pd.DataFrame(data_points)
    
    if df_chart.empty or df_chart['Receitas'].sum() == 0 and df_chart['Despesas'].sum() == 0:
         st.info("Sem movimentação financeira no período agrupado.")
         return

    # 3. Preparação para Altair (Melt)
    df_melted = df_chart.melt(
        id_vars=['Data_Sort', 'Data_Formatada'],
        value_vars=['Receitas', 'Despesas', 'Lucro Líquido'],
        var_name='Tipo',
        value_name='Valor'
    )
    
    # Format currency for tooltip
    df_melted['Valor_Formatado'] = df_melted['Valor'].apply(lambda x: format_currency(x))
    
    # 4. Renderização Visual (Altair)
    domain = ["Receitas", "Despesas", "Lucro Líquido"]
    range_ = ["#27AE60", "#E74C3C", "#2C3E50"]
    
    chart = alt.Chart(df_melted).mark_line(point=True).encode(
        x=alt.X('Data_Formatada', 
                sort=alt.SortField(field="Data_Sort"), 
                title=f"Período ({granularidade_texto})"),
        y=alt.Y('Valor', title="Valor (R$)", axis=alt.Axis(format=",.2f")),
        color=alt.Color('Tipo', 
                        scale=alt.Scale(domain=domain, range=range_),
                        legend=alt.Legend(title="", orient="top")),
        tooltip=[
            alt.Tooltip('Data_Formatada', title='Período'),
            alt.Tooltip('Tipo', title='Tipo'),
            alt.Tooltip('Valor_Formatado', title='Valor')
        ]
    ).properties(
        title="",
        height=400
    )
    
    st.altair_chart(chart, width='stretch')


def render_top_expenses(df):
    """
    Renderiza o gráfico de Top 10 Despesas por Categoria.
    
    Args:
        df: DataFrame detalhado contendo 'categoria', 'valor' e 'grupo_metrica'.
    """
    if df.empty:
        st.info("Sem dados para exibir Top Despesas.")
        return

    # 1. Filtragem e Processamento
    # Filtrar apenas saídas (valor < 0)
    # Excluir Comissões e Taxas (focar em Despesas Operacionais)
    # Assumindo que 'Comissões' e 'Taxas' podem ser identificadas pelo grupo_metrica ou nome da categoria
    # O usuário sugeriu: df[(df['valor'] < 0) & (~df['categoria'].str.contains('COMISSÕES', case=False))]
    
    # Criar cópia para não alterar o original
    df_chart = df.copy()
    
    # Filtrar despesas
    df_chart = df_chart[df_chart['valor'] < 0]
    
    if df_chart.empty:
        st.info("Sem despesas registradas no período.")
        return

    # Excluir Comissões e Taxas se possível
    # Vamos tentar filtrar por grupo_metrica se disponível, ou por string na categoria
    if 'grupo_metrica' in df_chart.columns:
        # Manter apenas Despesas Operacionais se possível, ou excluir os outros
        # Grupos comuns: 'Receita Bruta', 'Comissões', 'Despesas Financeiras', 'Despesas Operacionais', 'Impostos'
        # Vamos excluir Comissões e Despesas Financeiras para focar no operacional
        grupos_excluir = ['Comissões', 'Despesas Financeiras', 'Impostos', 'Custos Variáveis']
        df_chart = df_chart[~df_chart['grupo_metrica'].isin(grupos_excluir)]
    else:
        # Fallback por string na categoria
        termos_excluir = ['COMISSÃO', 'COMISSAO', 'TAXA', 'IMPOSTO']
        pattern = '|'.join(termos_excluir)
        df_chart = df_chart[~df_chart['categoria'].str.upper().str.contains(pattern, na=False)]
        
    if df_chart.empty:
        st.info("Sem despesas operacionais para exibir.")
        return

    # Converter para positivo para o gráfico
    df_chart['valor_abs'] = df_chart['valor'].abs()
    
    # Agrupar por categoria
    df_grouped = df_chart.groupby('categoria')['valor_abs'].sum().reset_index()
    
    # Ordenar e pegar Top 10
    df_grouped = df_grouped.sort_values('valor_abs', ascending=False).head(10)
    
    # Format currency for tooltip
    df_grouped['valor_fmt'] = df_grouped['valor_abs'].apply(lambda x: format_currency(x))
    
    # 2. Renderização Visual (Altair)
    chart = alt.Chart(df_grouped).mark_bar().encode(
        x=alt.X('valor_abs', title='Valor (R$)', axis=alt.Axis(format=",.2f")),
        y=alt.Y('categoria', sort='-x', title='Categoria'),
        color=alt.value('#E74C3C'), # Vermelho Coral fixo para despesas
        tooltip=[
            alt.Tooltip('categoria', title='Categoria'),
            alt.Tooltip('valor_fmt', title='Valor')
        ]
    ).properties(
        title="Top 10 Despesas Operacionais",
        height=400
    )
    
    st.altair_chart(chart, width='stretch')

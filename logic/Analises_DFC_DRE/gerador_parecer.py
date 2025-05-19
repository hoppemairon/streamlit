import pandas as pd
import streamlit as st
import os
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Tuple, Dict
import numpy as np
from datetime import datetime

def formatar_brl(valor: float) -> str:
    """Formata um valor para o formato de moeda brasileira."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def carregar_dados(path_fluxo: str) -> Optional[pd.DataFrame]:
    """Carrega os dados do arquivo de fluxo e realiza o pré-processamento básico."""
    if not os.path.exists(path_fluxo):
        st.error("Arquivo de fluxo não encontrado.")
        return None
    
    try:
        df = pd.read_excel(path_fluxo, index_col=0)
        
        # Remove linhas de separadores
        df = df[~df.index.str.startswith("🟦")]
        df = df[~df.index.str.startswith("🟥")]
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

def extrair_metricas_principais(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """Extrai as principais métricas do DataFrame."""
    metricas = {
        "total_receita": df.loc["🔷 Total de Receitas"],
        "total_despesa": df.loc["🔻 Total de Despesas"],
        "resultado": df.loc["🏦 Resultado do Período"]
    }
    
    if "📦 Estoque Final" in df.index:
        metricas["estoque"] = df.loc["📦 Estoque Final"]
    
    return metricas

def calcular_indicadores(metricas):
    indicadores = {}

    # Médias
    indicadores["receita_media"] = metricas["total_receita"].mean()
    indicadores["despesa_media"] = metricas["total_despesa"].mean()
    indicadores["resultado_medio"] = metricas["resultado"].mean()

    # Margem média
    if indicadores["receita_media"] != 0:
        indicadores["margem_media"] = (indicadores["resultado_medio"] / indicadores["receita_media"]) * 100
    else:
        indicadores["margem_media"] = 0

    # Volatilidade
    if indicadores["resultado_medio"] != 0:
        indicadores["volatilidade_resultado"] = metricas["resultado"].std() / abs(indicadores["resultado_medio"])
    else:
        indicadores["volatilidade_resultado"] = 0

    # Tendências
    for key, name in [("total_receita", "tendencia_receita"),
                       ("total_despesa", "tendencia_despesa"),
                       ("resultado", "tendencia_resultado")]:
        try:
            x = np.arange(len(metricas[key]))
            y = np.array(metricas[key], dtype=np.float64)
            if len(y) >= 2 and np.isfinite(y).all():
                indicadores[name] = np.polyfit(x, y, 1)[0]
            else:
                indicadores[name] = np.nan
        except Exception:
            indicadores[name] = np.nan

    # Estoque (se existir)
    if "estoque" in metricas:
        indicadores["estoque_medio"] = metricas["estoque"].mean()
        if indicadores["estoque_medio"] != 0:
            indicadores["giro_estoque"] = metricas["total_receita"].sum() / indicadores["estoque_medio"]
        else:
            indicadores["giro_estoque"] = np.nan

    return indicadores

def exibir_metricas_principais(metricas: Dict[str, pd.Series], indicadores: Dict[str, float]):
    """Exibe as métricas principais em cards."""
    col1, col2, col3 = st.columns(3)
    
    # Primeira linha de métricas
    with col1:
        st.metric(
            "🔷 Receita Média", 
            formatar_brl(indicadores["receita_media"]),
            f"{indicadores['tendencia_receita']:.2f}" if indicadores['tendencia_receita'] != 0 else None,
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            "🔻 Despesa Média", 
            formatar_brl(indicadores["despesa_media"]),
            f"{indicadores['tendencia_despesa']:.2f}" if indicadores['tendencia_despesa'] != 0 else None,
            delta_color="inverse"  # Crescimento de despesa é negativo
        )
    
    with col3:
        st.metric(
            "🏦 Resultado Médio", 
            formatar_brl(indicadores["resultado_medio"]),
            f"{indicadores['tendencia_resultado']:.2f}" if indicadores['tendencia_resultado'] != 0 else None,
            delta_color="normal"
        )
    
    # Segunda linha de métricas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "📊 Margem Média", 
            f"{indicadores['margem_media']:.2f}%",
            help="Resultado médio dividido pela receita média"
        )
    
    with col2:
        st.metric(
            "📈 Volatilidade", 
            f"{indicadores['volatilidade_resultado']:.2f}",
            help="Desvio padrão do resultado dividido pela média. Quanto maior, mais volátil."
        )
    
    if "estoque" in metricas:
        with col3:
            st.metric(
                "🔄 Giro de Estoque", 
                f"{indicadores['giro_estoque']:.2f}",
                help="Receita total dividida pelo estoque médio. Indica quantas vezes o estoque 'girou' no período."
            )

def criar_grafico_resultado(metricas: Dict[str, pd.Series]) -> go.Figure:
    """Cria um gráfico da evolução do resultado."""
    resultado = metricas["resultado"]
    
    fig = go.Figure()
    
    # Adiciona linha de resultado
    fig.add_trace(go.Scatter(
        x=resultado.index,
        y=resultado.values,
        mode='lines+markers',
        name='Resultado',
        line=dict(color='#2E86C1', width=3),
        marker=dict(size=8),
        fill='tozeroy',
        fillcolor='rgba(46, 134, 193, 0.2)'
    ))
    
    # Adiciona linha de tendência
    x_range = list(range(len(resultado)))
    y = resultado.values

    if len(y) >= 2 and np.isfinite(y).all():
        z = np.polyfit(x_range, y, 1)
        p = np.poly1d(z)
        fig.add_trace(go.Scatter(
            x=resultado.index,
            y=p(x_range),
            mode='lines',
            name='Tendência',
            line=dict(color='#E74C3C', width=2, dash='dash')
        ))
    else:
        st.warning("Não foi possível calcular a tendência do resultado (dados insuficientes ou inválidos).")
    
    # Adiciona linha de zero
    fig.add_shape(
        type="line",
        x0=resultado.index[0],
        y0=0,
        x1=resultado.index[-1],
        y1=0,
        line=dict(color="black", width=1, dash="dot"),
    )
    
    fig.update_layout(
        title="Evolução do Resultado Mensal",
        xaxis_title="Mês",
        yaxis_title="Valor (R$)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white"
    )
    
    return fig

def criar_grafico_receita_despesa(metricas: Dict[str, pd.Series]) -> go.Figure:
    """Cria um gráfico comparativo entre receita e despesa."""
    receita = metricas["total_receita"]
    despesa = metricas["total_despesa"]
    
    fig = go.Figure()
    
    # Adiciona barras de receita
    fig.add_trace(go.Bar(
        x=receita.index,
        y=receita.values,
        name='Receitas',
        marker_color='#27AE60',
        opacity=0.8
    ))
    
    # Adiciona barras de despesa (valores negativos para visualização)
    fig.add_trace(go.Bar(
        x=despesa.index,
        y=despesa.values * -1,  # Inverte para visualização
        name='Despesas',
        marker_color='#C0392B',
        opacity=0.8
    ))
    
    # Adiciona linha de resultado
    resultado = metricas["resultado"]
    fig.add_trace(go.Scatter(
        x=resultado.index,
        y=resultado.values,
        mode='lines+markers',
        name='Resultado',
        line=dict(color='#2E86C1', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title="Receitas vs Despesas",
        xaxis_title="Mês",
        yaxis_title="Valor (R$)",
        barmode='relative',
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white"
    )
    
    return fig

def criar_grafico_estoque(metricas: Dict[str, pd.Series]) -> Optional[go.Figure]:
    """Cria um gráfico da evolução do estoque, se disponível."""
    if "estoque" not in metricas:
        return None
    
    estoque = metricas["estoque"]
    
    fig = go.Figure()
    
    # Adiciona barras de estoque
    fig.add_trace(go.Bar(
        x=estoque.index,
        y=estoque.values,
        name='Estoque Final',
        marker_color='#8E44AD',
        opacity=0.8
    ))
    
    # Adiciona linha de média
    media_estoque = estoque.mean()
    fig.add_shape(
        type="line",
        x0=estoque.index[0],
        y0=media_estoque,
        x1=estoque.index[-1],
        y1=media_estoque,
        line=dict(color="#E67E22", width=2, dash="dash"),
    )
    
    # Adiciona anotação da média
    fig.add_annotation(
        x=estoque.index[-1],
        y=media_estoque,
        text=f"Média: {formatar_brl(media_estoque)}",
        showarrow=True,
        arrowhead=1,
        ax=50,
        ay=-30,
        bgcolor="#E67E22",
        font=dict(color="white")
    )
    
    fig.update_layout(
        title="Evolução do Estoque Final",
        xaxis_title="Mês",
        yaxis_title="Valor (R$)",
        hovermode="x unified",
        template="plotly_white"
    )
    
    return fig

def gerar_insights(metricas: Dict[str, pd.Series], indicadores: Dict[str, float]) -> Dict[str, Dict]:
    """Gera insights baseados nos dados financeiros."""
    insights = {
        "positivos": {},
        "negativos": {},
        "neutros": {}
    }
    
    # Análise de resultado
    if indicadores["resultado_medio"] > 0:
        insights["positivos"]["resultado"] = "✅ A empresa está com resultado positivo médio de " + formatar_brl(indicadores["resultado_medio"]) + "."
    else:
        insights["negativos"]["resultado"] = "🚨 A empresa apresenta resultado médio negativo de " + formatar_brl(indicadores["resultado_medio"]) + ". Atenção aos custos operacionais."
    
    # Análise de tendência
    if indicadores["tendencia_resultado"] > 0:
        insights["positivos"]["tendencia"] = "📈 O resultado apresenta tendência de crescimento de " + formatar_brl(indicadores["tendencia_resultado"]) + " por período."
    elif indicadores["tendencia_resultado"] < 0:
        insights["negativos"]["tendencia"] = "📉 O resultado apresenta tendência de queda de " + formatar_brl(abs(indicadores["tendencia_resultado"])) + " por período."
    
    # Análise de receita vs despesa
    if indicadores["tendencia_receita"] > 0 and indicadores["tendencia_despesa"] > 0:
        if indicadores["tendencia_receita"] > indicadores["tendencia_despesa"]:
            insights["positivos"]["crescimento"] = "📊 As receitas estão crescendo mais rapidamente que as despesas, o que é positivo para a margem."
        else:
            insights["negativos"]["crescimento"] = "⚠️ As despesas estão crescendo mais rapidamente que as receitas, o que pode comprometer a margem futura."
    
    # Análise de volatilidade
    if indicadores["volatilidade_resultado"] > 0.5:
        insights["neutros"]["volatilidade"] = "🔄 O resultado apresenta alta volatilidade (" + f"{indicadores['volatilidade_resultado']:.2f}" + "), o que pode dificultar o planejamento financeiro."
    
    # Análise de estoque
    if "estoque" in metricas:
        ultimo_estoque = metricas["estoque"].iloc[-1]
        if ultimo_estoque > indicadores["estoque_medio"] * 1.2:
            insights["negativos"]["estoque"] = "📦 O estoque atual está " + f"{(ultimo_estoque/indicadores['estoque_medio']-1)*100:.1f}%" + " acima da média. Isso pode indicar compras acima da demanda."
        elif ultimo_estoque < indicadores["estoque_medio"] * 0.8:
            insights["neutros"]["estoque"] = "📦 O estoque atual está " + f"{(1-ultimo_estoque/indicadores['estoque_medio'])*100:.1f}%" + " abaixo da média. Verifique se há risco de desabastecimento."
        
        if indicadores["giro_estoque"] < 3:
            insights["negativos"]["giro"] = "🔄 O giro de estoque está baixo (" + f"{indicadores['giro_estoque']:.2f}" + "). Considere estratégias para aumentar as vendas ou reduzir o estoque."
        elif indicadores["giro_estoque"] > 10:
            insights["positivos"]["giro"] = "🔄 O giro de estoque está excelente (" + f"{indicadores['giro_estoque']:.2f}" + "), indicando boa eficiência na gestão de inventário."
    
    return insights

def exibir_insights(insights: Dict[str, Dict]):
    """Exibe os insights gerados de forma organizada."""
    st.subheader("🧠 Análise Automática")
    
    # Exibe insights positivos
    if insights["positivos"]:
        st.success("**Pontos Positivos:**")
        for key, insight in insights["positivos"].items():
            st.markdown(f"- {insight}")
    
    # Exibe insights negativos
    if insights["negativos"]:
        st.error("**Pontos de Atenção:**")
        for key, insight in insights["negativos"].items():
            st.markdown(f"- {insight}")
    
    # Exibe insights neutros
    if insights["neutros"]:
        st.info("**Observações Adicionais:**")
        for key, insight in insights["neutros"].items():
            st.markdown(f"- {insight}")

def exibir_recomendacoes(insights: Dict[str, Dict], indicadores: Dict[str, float]):
    """Exibe recomendações baseadas nos insights gerados."""
    st.subheader("🎯 Recomendações")
    
    recomendacoes = []
    
    # Recomendações baseadas no resultado
    if "resultado" in insights["negativos"]:
        recomendacoes.append("**Redução de Custos:** Identifique as principais despesas e avalie possibilidades de redução sem comprometer a operação.")
        recomendacoes.append("**Revisão de Preços:** Considere ajustar os preços dos produtos/serviços para melhorar a margem.")
    
    # Recomendações baseadas na tendência
    if "tendencia" in insights["negativos"]:
        recomendacoes.append("**Plano de Ação:** Desenvolva um plano específico para reverter a tendência de queda no resultado.")
    
    # Recomendações baseadas no crescimento
    if "crescimento" in insights["negativos"]:
        recomendacoes.append("**Controle de Despesas:** Implemente controles mais rigorosos para evitar que as despesas cresçam mais que as receitas.")
    
    # Recomendações baseadas no estoque
    if "estoque" in insights["negativos"]:
        recomendacoes.append("**Gestão de Estoque:** Reavalie a política de compras e considere promoções para reduzir o estoque excedente.")
    
    if "giro" in insights["negativos"]:
        recomendacoes.append("**Aumento do Giro:** Implemente estratégias de marketing para aumentar as vendas ou reduza o volume de estoque mantido.")
    
    # Recomendações gerais
    if indicadores["volatilidade_resultado"] > 0.5:
        recomendacoes.append("**Planejamento Financeiro:** Estabeleça um fundo de reserva para lidar com a volatilidade do resultado.")
    
    # Exibe as recomendações
    if recomendacoes:
        for rec in recomendacoes:
            st.markdown(f"- {rec}")
    else:
        st.markdown("- Continue monitorando os indicadores financeiros e mantenha as boas práticas de gestão.")

def gerar_parecer_automatico(df):
    """Função principal que gera o parecer financeiro automático."""
    st.header("📄 Diagnóstico Financeiro Interativo")
    
    # Adiciona seletor de período
    hoje = datetime.now()
    periodo_options = ["Últimos 3 meses", "Últimos 6 meses", "Último ano", "Todo o período"]
    periodo_selecionado = st.selectbox("Selecione o período para análise:", periodo_options, index=3)
    
    # Filtrar por período selecionado
    if periodo_selecionado != "Todo o período":
        num_meses = 3 if "3" in periodo_selecionado else (6 if "6" in periodo_selecionado else 12)
        if len(df.columns) > num_meses:
            df = df.iloc[:, -num_meses:]
    
    # Extrair métricas principais
    metricas = extrair_metricas_principais(df)
    
    # Calcular indicadores
    indicadores = calcular_indicadores(metricas)
    
    # Exibir métricas principais
    exibir_metricas_principais(metricas, indicadores)
    
    # Criar abas para diferentes visualizações
    tab1, tab2 = st.tabs(["📊 Gráficos", "🧠 Análise"])
    
    with tab1:
        # Gráfico de evolução do resultado
        fig_resultado = criar_grafico_resultado(metricas)
        st.plotly_chart(fig_resultado, use_container_width=True)
        
        # Gráfico de receita vs despesa
        fig_rec_desp = criar_grafico_receita_despesa(metricas)
        st.plotly_chart(fig_rec_desp, use_container_width=True)
        
        # Gráfico de estoque, se disponível
        if "estoque" in metricas:
            fig_estoque = criar_grafico_estoque(metricas)
            if fig_estoque:
                st.plotly_chart(fig_estoque, use_container_width=True)
    
    with tab2:
        # Gerar insights
        insights = gerar_insights(metricas, indicadores)
        
        # Exibir insights
        exibir_insights(insights)
        
        # Exibir recomendações
        exibir_recomendacoes(insights, indicadores)
        
        # Adicionar opção para download do relatório
        st.markdown("---")
        st.markdown("### 📥 Exportar Relatório")
        st.markdown("Baixe o relatório completo para compartilhar ou arquivar.")
        
        if st.button("Gerar Relatório PDF"):
            st.info("Funcionalidade de exportação para PDF em desenvolvimento. Em breve estará disponível!")
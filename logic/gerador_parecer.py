import pandas as pd
import streamlit as st
import os

def gerar_parecer_automatico(path_fluxo="./logic/transacoes_numericas.xlsx"):
    st.header("📄 Diagnóstico Financeiro Interativo")

    if not os.path.exists(path_fluxo):
        st.error("Arquivo de fluxo não encontrado.")
        return

    df = pd.read_excel(path_fluxo, index_col=0)

    # Remove linhas de separadores
    df = df[~df.index.str.startswith("🟦")]
    df = df[~df.index.str.startswith("🟥")]

    # Extrai totais
    total_receita = df.loc["🔷 Total de Receitas"]
    total_despesa = df.loc["🔻 Total de Despesas"]
    resultado = df.loc["🏦 Resultado do Período"]
    estoque = df.loc["📦 Estoque Final"] if "📦 Estoque Final" in df.index else pd.Series(dtype="float")

    # KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("🔷 Receita Média", f"R$ {total_receita.mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col2.metric("🔻 Despesa Média", f"R$ {total_despesa.mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col3.metric("🏦 Resultado Médio", f"R$ {resultado.mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # Gráficos
    st.subheader("📈 Evolução do Resultado")
    st.line_chart(resultado)

    st.subheader("📊 Receita vs Despesa")
    char_data = pd.DataFrame(
            {"Receitas": total_receita, 
            "Despesas": total_despesa*-1
            }
        )
    st.line_chart(
        char_data,
        color=["#FF0000", "#0000FF"]
    )

    if not estoque.empty:
        st.subheader("📦 Estoque Final por Mês")
        st.bar_chart(estoque)

    # Insights simples
    st.subheader("🧠 Análise Automática")

    if resultado.mean() < 0:
        st.error("🚨 A empresa apresenta resultado médio negativo. Atenção aos custos operacionais.")
    else:
        st.success("✅ A empresa está com resultado positivo médio. Ainda assim, atenção ao controle de despesas.")

    if not estoque.empty and estoque.iloc[-1] > estoque.mean():
        st.info("📦 O estoque aumentou nos últimos meses. Isso pode indicar compras acima da demanda.")
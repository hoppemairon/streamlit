import pandas as pd
import streamlit as st
import os

def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def exibir_dre(path_fluxo="./logic/transacoes_numericas.xlsx", path_plano="./logic/plano_de_contas.csv"):
    st.markdown("## 📊 Demonstrativo de Resultados (DRE)")

    if not os.path.exists(path_fluxo) or not os.path.exists(path_plano):
        st.error("Dados necessários não encontrados.")
        return

    df_fluxo = pd.read_excel(path_fluxo, index_col=0)
    plano = pd.read_csv(path_plano)

    meses = df_fluxo.columns.tolist()

    def soma_por_grupo(grupo):
        cats = plano[plano["Grupo"] == grupo]["Categoria"].tolist()
        valores = df_fluxo.loc[df_fluxo.index.isin(cats)].sum()
        # Se for despesa, inverter o sinal para positivo
        if "Despesas" in grupo or "Investimentos" in grupo or "Retiradas" in grupo or "Extra Operacional" in grupo:
            valores = valores.abs()
        return valores

    def soma_por_categoria(*categorias):
        valores = df_fluxo.loc[df_fluxo.index.isin(categorias)].sum()
        return valores

    def linha(nome, serie):
        return pd.DataFrame([serie], index=[nome])

    dre = pd.concat([
        linha("FATURAMENTO", df_fluxo.loc["💰 Faturamento Bruto"]),
        linha("RECEITA", soma_por_categoria("Receita de Vendas", "Receita de Serviços")),
        linha("IMPOSTOS", soma_por_grupo("Despesas Impostos")),
        linha("DESPESA OPERACIONAL", soma_por_grupo("Despesas Operacionais")),
    ])

    dre.loc["MARGEM CONTRIBUIÇÃO"] = dre.loc["RECEITA"] - dre.loc["IMPOSTOS"] - dre.loc["DESPESA OPERACIONAL"]

    dre = pd.concat([
        dre,
        linha("DESPESAS COM PESSOAL", soma_por_grupo("Despesas RH")),
        linha("DESPESA ADMINISTRATIVA", soma_por_grupo("Despesas Administrativas")),
    ])

    dre.loc["LUCRO OPERACIONAL"] = dre.loc["MARGEM CONTRIBUIÇÃO"] - dre.loc["DESPESAS COM PESSOAL"] - dre.loc["DESPESA ADMINISTRATIVA"]

    dre = pd.concat([
        dre,
        linha("INVESTIMENTOS", soma_por_grupo("Investimentos / Aplicações")),
        linha("DESPESA EXTRA OPERACIONAL", soma_por_grupo("Extra Operacional")),
    ])

    dre.loc["LUCRO LIQUIDO"] = dre.loc["LUCRO OPERACIONAL"] - dre.loc["INVESTIMENTOS"] - dre.loc["DESPESA EXTRA OPERACIONAL"]
    dre = pd.concat([
        dre,
        linha("RETIRADAS SÓCIOS", soma_por_grupo("Retiradas")),
        linha("RECEITA EXTRA OPERACIONAL", soma_por_categoria("Juros Recebidos", "Outros Recebimentos")),
    ])

    dre.loc["RESULTADO"] = dre.loc["LUCRO LIQUIDO"] - dre.loc["RETIRADAS SÓCIOS"] + dre.loc["RECEITA EXTRA OPERACIONAL"]

    if "📦 Estoque Final" in df_fluxo.index:
        dre.loc["ESTOQUE"] = df_fluxo.loc["📦 Estoque Final"]

    dre.loc["SALDO"] = 0  # TODO: puxar saldo dos relatórios
    dre.loc["RESULTADO GERENCIAL"] = dre.loc["RESULTADO"] + dre.loc["ESTOQUE"] + dre.loc["SALDO"]

    dre["TOTAL"] = dre[meses].sum(axis=1)
    total_receita = dre.loc["RECEITA", "TOTAL"]
    dre["%"] = dre["TOTAL"] / total_receita * 100

    # Formata dados
    dre_formatado = dre.copy()
    for col in meses + ["TOTAL"]:
        dre_formatado[col] = dre_formatado[col].apply(formatar_brl)
    dre_formatado["%"] = dre["%"].apply(lambda x: f"{x:.1f}%")

    # Resetando índice para que a primeira coluna seja exibida normalmente
    dre_formatado = dre_formatado.reset_index()
    dre_formatado.columns.values[0] = "Descrição"

    # Estilo por linha
    row_styles = {
        "FATURAMENTO": ("#5d65c8", "white"),
        "RECEITA": ("#152357", "white"),
        "MARGEM CONTRIBUIÇÃO": ("#39b79c", "black"),
        "LUCRO OPERACIONAL": ("#39b79c", "black"),
        "LUCRO LIQUIDO": ("#39b79c", "black"),
        "RESULTADO": ("#216a5a", "black"),
        "RESULTADO GERENCIAL": ("#216a5a", "white"),
    }

    def highlight_rows(row):
        bg_color, text_color = row_styles.get(row["Descrição"], ("", "black"))
        return [f"background-color: {bg_color}; color: {text_color}; font-weight: bold;" if bg_color else "" for _ in row]

    st.dataframe(
        dre_formatado.style.apply(highlight_rows, axis=1).hide(axis="index"),
        use_container_width=True
    )

    return dre

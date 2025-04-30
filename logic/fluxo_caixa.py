import pandas as pd
import streamlit as st
from datetime import datetime
import io
import os


def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def exibir_fluxo_caixa(df_transacoes, path_faturamento="./logic/faturamentos.csv", path_estoque="./logic/estoques.csv"):
    st.markdown("## 📊 Fluxo de Caixa (por Categoria e Mês)")

    df_filtrado = df_transacoes[df_transacoes["Considerar"].str.lower() == "sim"].copy()

    df_filtrado["Valor (R$)"] = pd.to_numeric(
        df_filtrado["Valor (R$)"].astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce"
    )
    df_filtrado["Data"] = pd.to_datetime(df_filtrado["Data"], format="%d/%m/%Y", errors="coerce")
    df_filtrado = df_filtrado.dropna(subset=["Data"])
    df_filtrado["Mes"] = df_filtrado["Data"].dt.to_period("M").astype(str)

    df_pivot = pd.pivot_table(
        df_filtrado,
        values="Valor (R$)",
        index="Categoria",
        columns="Mes",
        aggfunc="sum",
        fill_value=0
    )

    try:
        plano = pd.read_csv("./logic/plano_de_contas.csv")
        ordem_map = plano.set_index("Categoria")["Ordem"].to_dict()
        tipo_map = plano.set_index("Categoria")["Tipo"].to_dict()
    except Exception as e:
        ordem_map = {}
        tipo_map = {}
        st.warning(f"Erro ao carregar plano de contas: {e}")

    df_pivot["__ordem__"] = df_pivot.index.map(ordem_map).fillna(999)
    df_pivot["__tipo__"] = df_pivot.index.map(tipo_map).fillna("")
    df_pivot = df_pivot.sort_values("__ordem__")

    meses = df_pivot.columns.drop(["__ordem__", "__tipo__"])
    receitas = df_pivot[df_pivot["__tipo__"] == "Crédito"][meses].sum()
    despesas = df_pivot[df_pivot["__tipo__"] == "Débito"][meses].sum()
    resultado = receitas + despesas

    if os.path.exists(path_faturamento):
        df_fat = pd.read_csv(path_faturamento)
        linha_fat = df_fat.set_index("Mes").T.reindex(columns=meses).fillna(0)
        linha_fat.index = ["💰 Faturamento Bruto"]
    else:
        linha_fat = pd.DataFrame(columns=meses)

    if os.path.exists(path_estoque):
        df_estoque = pd.read_csv(path_estoque)
        linha_estoque = df_estoque.set_index("Mes").T.reindex(columns=meses).fillna(0)
        linha_estoque.index = ["📦 Estoque Final"]
    else:
        linha_estoque = pd.DataFrame(columns=meses)

    df_receitas = df_pivot[df_pivot["__tipo__"] == "Crédito"].drop(columns=["__ordem__", "__tipo__"])
    df_despesas = df_pivot[df_pivot["__tipo__"] == "Débito"].drop(columns=["__ordem__", "__tipo__"])

    linha_div_receitas = pd.DataFrame([[None]*len(meses)], index=["🟦 Receitas"], columns=meses)
    linha_div_despesas = pd.DataFrame([[None]*len(meses)], index=["🟥 Despesas"], columns=meses)

    linha_total_receitas = pd.DataFrame([receitas], index=["🔷 Total de Receitas"])
    linha_total_despesas = pd.DataFrame([despesas], index=["🔻 Total de Despesas"])
    linha_resultado = pd.DataFrame([resultado], index=["🏦 Resultado do Período"])

    # Concatena tudo na ordem:
    df_final = pd.concat([
        linha_fat,
        linha_div_receitas,
        df_receitas,
        linha_div_despesas,
        df_despesas,
        linha_total_receitas,
        linha_total_despesas,
        linha_resultado,
        linha_estoque
    ])

    df_formatado = df_final.applymap(lambda x: formatar_brl(x) if pd.notnull(x) else "")
    st.dataframe(df_formatado, use_container_width=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_formatado.to_excel(writer, sheet_name="Fluxo de Caixa")
    output.seek(0)

    st.download_button(
        label="📄 Baixar Fluxo de Caixa (Excel)",
        data=output,
        file_name="fluxo_caixa.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    # Salva também na pasta logic
    # Salva a versão formatada para download
    df_formatado.to_excel("./logic/transacoes_categorizadas.xlsx", index=True)

    # Salva também os dados numéricos para o parecer
    df_final.to_excel("./logic/transacoes_numericas.xlsx", index=True)

import streamlit as st
import pandas as pd
import re
import os

def parse_brl(valor):
    valor = str(valor)
    if valor:
        valor = re.sub(r"[^\d,]", "", valor)
        try:
            return float(valor.replace(".", "").replace(",", "."))
        except:
            return 0.0
    return 0.0

def format_brl(valor):
    try:
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00"

def coletar_estoques(df_transacoes, path_csv="./logic/CSVs/estoques.csv"):
    st.markdown("## 📦 Cadastro de Estoque Final por Mês")
    st.markdown("#### 🧾 Informe o valor do estoque no fim de cada mês:")

    # Garante que datas estejam OK
    df_transacoes["Data"] = pd.to_datetime(df_transacoes["Data"], format="%d/%m/%Y", errors="coerce")
    df_transacoes = df_transacoes.dropna(subset=["Data"])
    meses = sorted(df_transacoes["Data"].dt.to_period("M").astype(str).unique())

    df_estoques = pd.DataFrame(columns=["Mes", "Estoque"])

    valores_input = {}

    for mes in meses:
        valor_antigo = df_estoques[df_estoques["Mes"] == mes]["Estoque"]
        valor_float = float(valor_antigo.values[0]) if not valor_antigo.empty else 0.0
        valor_formatado = format_brl(valor_float)

        col1, col2 = st.columns([1.5, 3])
        with col1:
            st.markdown(f"**Estoque para {mes}**")
        with col2:
            input_valor = st.text_input(
                label="",
                value=valor_formatado,
                key=f"estoque_{mes}",
                label_visibility="collapsed",
                placeholder="Ex: 50.000,00"
            )
            valores_input[mes] = input_valor

    if st.button("💾 Salvar Estoques"):
        novos = []
        for mes, valor_str in valores_input.items():
            valor_float = parse_brl(valor_str)
            novos.append({"Mes": mes, "Estoque": valor_float})

        df_salvo = pd.DataFrame(novos)
        df_salvo.to_csv(path_csv, index=False)

        st.success("✅ Valores de estoque salvos com sucesso!")
        st.dataframe(df_salvo)
import streamlit as st
import pandas as pd
import re
import os

def parse_brl(valor):
    """Converte string BRL ex: '1.234,56' -> 1234.56 (float)"""
    valor = str(valor)
    if valor:
        valor = re.sub(r"[^\d,]", "", valor)
        try:
            return float(valor.replace(".", "").replace(",", "."))
        except:
            return 0.0
    return 0.0

def format_brl(valor):
    """Converte float -> BRL formatado como 150.000,00"""
    try:
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00"

def coletar_faturamentos(df_transacoes, path_csv="./logic/CSVs/faturamentos.csv"):
    st.markdown("## 🧾 Cadastro de Faturamento por Mês")
    st.markdown("#### 💵 Preencha o faturamento bruto mensal:")

    # Garante que a data está em datetime
    df_transacoes["Data"] = pd.to_datetime(df_transacoes["Data"], format="%d/%m/%Y", errors="coerce")
    df_transacoes = df_transacoes.dropna(subset=["Data"])

    meses = sorted(df_transacoes["Data"].dt.to_period("M").astype(str).unique())

    # Sempre começa com um DataFrame vazio
    df_faturamentos = pd.DataFrame(columns=["Mes", "Faturamento"])

    valores_input = {}

    for mes in meses:
        valor_antigo = df_faturamentos[df_faturamentos["Mes"] == mes]["Faturamento"]
        valor_float = float(valor_antigo.values[0]) if not valor_antigo.empty else 0.0
        valor_formatado = format_brl(valor_float)

        col1, col2 = st.columns([1.5, 3])
        with col1:
            st.markdown(f"**Faturamento para {mes}**")
        with col2:
            input_valor = st.text_input(
                label="",
                value=valor_formatado,
                key=f"faturamento_{mes}",
                label_visibility="collapsed",
                placeholder="Ex: 150.000,00"
            )
            valores_input[mes] = input_valor

    if st.button("💾 Salvar Faturamentos"):
        novos = []
        for mes, valor_str in valores_input.items():
            valor_float = parse_brl(valor_str)
            novos.append({"Mes": mes, "Faturamento": valor_float})

        df_salvo = pd.DataFrame(novos)

        # 🔄 Substitui completamente o conteúdo do CSV
        df_salvo.to_csv(path_csv, index=False)

        st.success("✅ Faturamentos salvos com sucesso!")
        st.dataframe(df_salvo)

    return None
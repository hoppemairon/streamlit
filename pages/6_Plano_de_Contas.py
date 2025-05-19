import streamlit as st
import pandas as pd
import os

def exibir_pagina():
    st.title("📘 Plano de Contas Padrão")
    caminho = "./logic/CSVs/plano_de_contas.csv"

    if os.path.exists(caminho):
        df = pd.read_csv(caminho)
    else:
        st.warning("Arquivo não encontrado.")
        return

    st.dataframe(df, use_container_width=True)

    st.markdown("### ✍️ Adicionar nova categoria")

    # Garantir que colunas essenciais existam
    if not {"Grupo", "Categoria", "Tipo", "Considerar", "Ordem"}.issubset(df.columns):
        st.error("⚠️ O arquivo plano_de_contas.csv está com colunas incompletas.")
        return

    df["Grupo"] = df["Grupo"].astype(str).str.strip()

    # Ordena os grupos conforme a coluna 'Ordem' (prefixo)
    df["Ordem"] = df["Ordem"].astype(str).str.strip()
    grupos_ordenados = (
        df[["Grupo", "Ordem"]]
        .drop_duplicates(subset=["Grupo"])
        .assign(OrdemNum=lambda d: d["Ordem"].str.extract(r"^(\d+)").astype(float))
        .sort_values("OrdemNum")
        .reset_index(drop=True)
    )
    grupos_opcoes = grupos_ordenados["Grupo"].tolist()

    grupo = st.selectbox("Grupo", grupos_opcoes)
    categoria = st.text_input("Categoria")
    tipo = st.selectbox("Tipo", ["Crédito", "Débito"])
    considerar = st.selectbox("Considerar", ["Sim", "Não"])

    if st.button("➕ Adicionar"):
        if grupo and categoria:
            try:
                # Prefixo do grupo
                ordem_grupo = df[df["Grupo"] == grupo]["Ordem"].dropna().astype(str)
                if not ordem_grupo.empty:
                    prefixo_grupo = ordem_grupo.iloc[0].split(".")[0]
                else:
                    st.error("❌ Grupo sem numeração definida na coluna 'Ordem'.")
                    return

                # Busca último sufixo numérico
                ordens_do_grupo = df[df["Grupo"] == grupo]["Ordem"].dropna().astype(str)
                sufixos = [
                    float(o.split(".")[1]) for o in ordens_do_grupo
                    if "." in o and o.split(".")[0] == prefixo_grupo and o.split(".")[1].isdigit()
                ]
                novo_sufixo = max(sufixos) + 1 if sufixos else 1
                nova_ordem = f"{prefixo_grupo}.{int(novo_sufixo)}"
            except Exception as e:
                st.error(f"Erro ao gerar ordem automática: {e}")
                return

            nova_linha = pd.DataFrame([{
                "Grupo": grupo,
                "Categoria": categoria,
                "Tipo": tipo,
                "Considerar": considerar,
                "Ordem": nova_ordem
            }])
            df = pd.concat([df, nova_linha], ignore_index=True)
            df.to_csv(caminho, index=False)
            st.success(f"Categoria adicionada com sucesso com ordem {nova_ordem}!")
        else:
            st.error("⚠️ Preencha todos os campos.")

    st.markdown("### 🗑️ Excluir uma categoria")
    categoria_excluir = st.selectbox("Escolha a categoria para excluir", df["Categoria"].unique())

    if st.button("❌ Excluir Categoria"):
        df = df[df["Categoria"] != categoria_excluir]
        df.to_csv(caminho, index=False)
        st.success("Categoria excluída com sucesso!")

exibir_pagina()
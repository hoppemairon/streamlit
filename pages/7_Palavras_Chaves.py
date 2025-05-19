import streamlit as st
import pandas as pd
import os

def exibir_pagina():
    st.title("🔑 Palavras-Chave para Categorização Automática")

    caminho_palavras = "./logic/CSVs/palavras_chave.csv"
    caminho_plano = "./logic/CSVs/plano_de_contas.csv"

    # Carrega o plano de contas
    if os.path.exists(caminho_plano):
        try:
            plano = pd.read_csv(caminho_plano)
        except Exception as e:
            st.warning(f"Erro ao carregar plano de contas: {e}")
            plano = pd.DataFrame(columns=["Grupo", "Categoria", "Tipo"])
    else:
        st.warning("⚠️ Arquivo plano_de_contas.csv não encontrado.")
        plano = pd.DataFrame(columns=["Grupo", "Categoria", "Tipo"])

    # Carrega o CSV de palavras-chave
    if os.path.exists(caminho_palavras):
        df = pd.read_csv(caminho_palavras)
    else:
        df = pd.DataFrame(columns=["PalavraChave", "Tipo", "Categoria"])

    st.dataframe(df, use_container_width=True)

    st.markdown("### ✍️ Adicionar nova palavra-chave")
    palavra = st.text_input("Palavra-chave")
    tipo = st.selectbox("Tipo", ["Crédito", "Débito"])

    # Filtra categorias com base no tipo selecionado
    if not plano.empty:
        plano_filtrado = plano[plano["Tipo"] == tipo]
        plano_filtrado["Opcao"] = plano_filtrado["Grupo"] + " :: " + plano_filtrado["Categoria"]
        categorias_disponiveis = plano_filtrado["Opcao"].dropna().unique().tolist()
    else:
        categorias_disponiveis = []

    categoria_opcao = st.selectbox("Categoria", [""] + categorias_disponiveis)

    if st.button("➕ Adicionar Palavra-Chave"):
        if palavra and categoria_opcao:
            categoria_limpa = plano_filtrado.set_index("Opcao").loc[categoria_opcao, "Categoria"]
            nova_linha = pd.DataFrame([{
                "PalavraChave": palavra,
                "Tipo": tipo,
                "Categoria": categoria_limpa
            }])
            df = pd.concat([df, nova_linha], ignore_index=True)
            df.to_csv(caminho_palavras, index=False)
            st.success("Palavra-chave adicionada com sucesso!")
        else:
            st.error("⚠️ Preencha todos os campos.")

    st.markdown("### 🗑️ Excluir uma palavra-chave")
    if not df.empty:
        palavra_excluir = st.selectbox("Escolha a palavra para excluir", df["PalavraChave"].unique())

        if st.button("❌ Excluir Palavra-Chave"):
            df = df[df["PalavraChave"] != palavra_excluir]
            df.to_csv(caminho_palavras, index=False)
            st.success("Palavra-chave excluída com sucesso!")

exibir_pagina()
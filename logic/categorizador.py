import pandas as pd
import streamlit as st
import os

def categorizar_transacoes(
    df_transacoes,
    plano_path="./logic/plano_de_contas.csv",
    categorias_salvas_path="./logic/categorias_salvas.csv",
    prefixo_key="cat",
    tipo_lancamento=""
):
    if os.path.exists(categorias_salvas_path):
        df_categorias = pd.read_csv(categorias_salvas_path)
    else:
        df_categorias = pd.DataFrame(columns=["Descricao", "Tipo", "Categoria"])

    df_desc = (
        df_transacoes
        .groupby("Descrição", as_index=False)
        .agg(Quantidade=("Valor (R$)", "count"), Total=("Valor (R$)", "sum"))
    )
    df_desc["Categoria"] = ""

    try:
        df_plano = pd.read_csv(plano_path)
    except FileNotFoundError:
        st.error("⚠️ Arquivo plano_de_contas.csv não encontrado.")
        return df_transacoes, pd.DataFrame()

    df_plano = df_plano[df_plano["Tipo"] == tipo_lancamento].copy()
    df_plano["Opcao"] = df_plano["Grupo"] + " :: " + df_plano["Categoria"]

    opcoes_categorias = df_plano["Opcao"].tolist()
    mapa_opcao_categoria = dict(zip(df_plano["Opcao"], df_plano["Categoria"]))

    try:
        df_palavras = pd.read_csv("./logic/palavras_chave.csv")
    except:
        df_palavras = pd.DataFrame(columns=["PalavraChave", "Tipo", "Categoria"])

    st.markdown("### 🧠 Categorize as Descrições")
    st.info("Para cada descrição, selecione uma categoria do plano de contas.")

    with st.expander("📘 Visualizar Plano de Contas"):
        st.dataframe(df_plano[["Grupo", "Categoria"]], use_container_width=True)

    registros_categorizados = []
    registros_nao_categorizados = []

    for idx, row in df_desc.iterrows():
        desc = row["Descrição"]
        if pd.notnull(row["Categoria"]) and row["Categoria"] != "":
            continue

        categoria_salva = df_categorias[
            (df_categorias["Descricao"] == desc) &
            (df_categorias["Tipo"] == tipo_lancamento)
        ]["Categoria"].values

        if len(categoria_salva) > 0:
            categoria_padrao = categoria_salva[0]
        else:
            categoria_padrao = ""
            for _, row_palavra in df_palavras.iterrows():
                if row_palavra["Tipo"] == tipo_lancamento and row_palavra["PalavraChave"].lower() in desc.lower():
                    categoria_padrao = row_palavra["Categoria"]
                    break

        if categoria_padrao:
            registros_categorizados.append((row, categoria_padrao))
        else:
            registros_nao_categorizados.append(row)

    for row in registros_nao_categorizados:
        desc = row["Descrição"]
        valores = df_transacoes[df_transacoes["Descrição"] == desc]["Valor (R$)"].tolist()
        valores_formatados = " - ".join(str(v) for v in valores)
        label = f"📌 {desc} — {row['Quantidade']}x — Total: {valores_formatados}"

        categoria_escolhida = st.selectbox(
            label,
            options=[""] + opcoes_categorias,
            key=f"{prefixo_key}_{desc}"
        )

        categoria_limpa = mapa_opcao_categoria.get(categoria_escolhida, "")
        df_desc.loc[df_desc["Descrição"] == desc, "Categoria"] = categoria_limpa

    with st.expander("✅ Descrições já categorizadas automaticamente"):
        for row, categoria in registros_categorizados:
            desc = row["Descrição"]
            valores = df_transacoes[df_transacoes["Descrição"] == desc]["Valor (R$)"].tolist()
            valores_formatados = " - ".join(str(v) for v in valores)
            st.markdown(f"**📌 {desc}** — {row['Quantidade']}x — Total: {valores_formatados}")
            st.markdown(f"✔️ Categoria aplicada: {categoria}")
            df_desc.loc[df_desc["Descrição"] == desc, "Categoria"] = categoria

    st.markdown("### 🧩 Categorização em Lote")
    coluna1, coluna2 = st.columns([3, 2])
    with coluna1:
        palavras_chave = st.text_input("🔍 Procurar descrições por palavra:", key=f"busca_palavra_{prefixo_key}")
        descricoes_disponiveis = df_desc[df_desc["Categoria"].isnull() | (df_desc["Categoria"] == "")]["Descrição"].tolist()
        if palavras_chave:
            descricoes_filtradas = [d for d in descricoes_disponiveis if palavras_chave.lower() in d.lower()]
        else:
            descricoes_filtradas = descricoes_disponiveis

        selecionadas = st.multiselect("✅ Descrições para categorizar:", descricoes_filtradas, key=f"multi_{prefixo_key}")

    with coluna2:
        opcao_lote = st.selectbox("📂 Categoria para aplicar:", [""] + opcoes_categorias, key=f"lote_{prefixo_key}")
        if st.button("📌 Aplicar Categoria em Lote", key=f"btn_lote_{prefixo_key}"):
            if opcao_lote and selecionadas:
                categoria_escolhida = mapa_opcao_categoria.get(opcao_lote, "")
                df_desc.loc[df_desc["Descrição"].isin(selecionadas), "Categoria"] = categoria_escolhida
                st.success(f"✅ Categoria '{categoria_escolhida}' aplicada em {len(selecionadas)} descrições.")

    # 🚨 NOVO: Corrigir itens sem categoria automaticamente
    faltantes = df_desc[df_desc["Categoria"].isnull() | (df_desc["Categoria"].str.strip() == "")]
    if not faltantes.empty:
        df_desc.loc[faltantes.index, "Categoria"] = "Sem Identificação"
        st.warning(f"⚠️ {len(faltantes)} descrições foram categorizadas como **Sem Identificação**.")

    mapa = dict(zip(df_desc["Descrição"], df_desc["Categoria"]))
    df_transacoes["Categoria"] = df_transacoes["Descrição"].map(mapa)

    if st.button("💾 Salvar Categorias no CSV", key=f"btn_salvar_{prefixo_key}"):
        novas = pd.DataFrame({
            "Descricao": df_desc["Descrição"],
            "Tipo": tipo_lancamento,
            "Categoria": df_desc["Categoria"]
        })
        novas = novas[novas["Categoria"].notna() & (novas["Categoria"].str.strip() != "")]
        df_categorias = (
            pd.concat([df_categorias, novas])
            .drop_duplicates(subset=["Descricao", "Tipo"], keep="last")
            .reset_index(drop=True)
        )
        df_categorias.to_csv(categorias_salvas_path, index=False)
        st.success("✅ Categorias salvas com sucesso!")

    try:
        plano = pd.read_csv(plano_path)
        mapa_considerar = dict(zip(plano["Categoria"], plano["Considerar"]))
        df_transacoes["Considerar"] = df_transacoes["Categoria"].map(mapa_considerar).fillna("Sim")
    except Exception as e:
        st.warning(f"Erro ao carregar plano de contas: {e}")
        df_transacoes["Considerar"] = "Sim"

    return df_transacoes, df_desc

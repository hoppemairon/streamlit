import pandas as pd
import streamlit as st
import os

def categorizar_transacoes(
    df_transacoes,
    plano_path="./logic/CSVs/plano_de_contas.csv",
    categorias_salvas_path="./logic/CSVs/categorias_salvas.csv",
    prefixo_key="cat",
    tipo_lancamento=""
):
    # Verificar se o arquivo de categorias salvas existe
    if os.path.exists(categorias_salvas_path):
        df_categorias = pd.read_csv(categorias_salvas_path)
    else:
        df_categorias = pd.DataFrame(columns=["Descricao", "Tipo", "Categoria"])

    # Agrupar descrições únicas
    df_desc = (
        df_transacoes
        .groupby("Descrição", as_index=False)
        .agg(Quantidade=("Valor (R$)", "count"), Total=("Valor (R$)", "sum"))
    )
    df_desc["Categoria"] = ""

    # Verificar se o plano de contas existe
    try:
        df_plano = pd.read_csv(plano_path)
        # Verificar se o plano está vazio
        if df_plano.empty:
            st.error("⚠️ Arquivo plano_de_contas.csv está vazio.")
            return df_transacoes, pd.DataFrame()
    except FileNotFoundError:
        st.error("⚠️ Arquivo plano_de_contas.csv não encontrado.")
        return df_transacoes, pd.DataFrame()
    except Exception as e:
        st.error(f"⚠️ Erro ao ler o arquivo plano_de_contas.csv: {e}")
        return df_transacoes, pd.DataFrame()

    # Mapear o tipo de lançamento para o formato do plano de contas
    # Se tipo_lancamento for "Despesa", usar "Débito"
    # Se tipo_lancamento for "Receita", usar "Crédito"
    tipo_mapeado = tipo_lancamento
    if tipo_lancamento == "Despesa":
        tipo_mapeado = "Débito"
    elif tipo_lancamento == "Receita":
        tipo_mapeado = "Crédito"

    # Filtrar plano pelo tipo de lançamento
    if tipo_mapeado:
        df_plano_filtrado = df_plano[df_plano["Tipo"] == tipo_mapeado].copy()
        if df_plano_filtrado.empty:
            st.warning(f"Nenhuma categoria encontrada para o tipo '{tipo_mapeado}'. Usando todas as categorias.")
            df_plano_filtrado = df_plano.copy()
    else:
        df_plano_filtrado = df_plano.copy()

    # Verificar se há categorias após a filtragem
    if df_plano_filtrado.empty:
        st.error("⚠️ Plano de contas vazio após filtragem.")
        return df_transacoes, df_desc

    # Criar opções de categorias
    df_plano_filtrado["Opcao"] = df_plano_filtrado["Grupo"] + " :: " + df_plano_filtrado["Categoria"]
    opcoes_categorias = df_plano_filtrado["Opcao"].tolist()
    mapa_opcao_categoria = dict(zip(df_plano_filtrado["Opcao"], df_plano_filtrado["Categoria"]))

    # Carregar palavras-chave
    try:
        df_palavras = pd.read_csv("./logic/CSVs/palavras_chave.csv")
    except:
        df_palavras = pd.DataFrame(columns=["PalavraChave", "Tipo", "Categoria"])

    st.markdown("### 🧠 Categorize as Descrições")
    st.info("Para cada descrição, selecione uma categoria do plano de contas.")

    with st.expander("📘 Visualizar Plano de Contas"):
        st.dataframe(df_plano_filtrado[["Grupo", "Categoria"]], use_container_width=True)

    # MOVIDO PARA CIMA: Categorização em Lote
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

    # Preparar registros para categorização
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

    # Categorização manual individual
    st.markdown("### 📝 Categorização Manual Individual")
    for row in registros_nao_categorizados:
        desc = row["Descrição"]
        valores = df_transacoes[df_transacoes["Descrição"] == desc]["Valor (R$)"].tolist()
        
        # Formatar valores para exibição
        valores_formatados = []
        for v in valores:
            if isinstance(v, (int, float)):
                valores_formatados.append(f"R$ {abs(v):.2f}".replace(".", ","))
            else:
                valores_formatados.append(str(v))
        
        valores_texto = " - ".join(valores_formatados)
        label = f"📌 {desc} — {row['Quantidade']}x — Total: {valores_texto}"

        categoria_escolhida = st.selectbox(
            label,
            options=[""] + opcoes_categorias,
            key=f"{prefixo_key}_{desc}"
        )

        categoria_limpa = mapa_opcao_categoria.get(categoria_escolhida, "")
        df_desc.loc[df_desc["Descrição"] == desc, "Categoria"] = categoria_limpa

    # Exibir descrições já categorizadas
    with st.expander("✅ Descrições já categorizadas automaticamente"):
        for row, categoria in registros_categorizados:
            desc = row["Descrição"]
            valores = df_transacoes[df_transacoes["Descrição"] == desc]["Valor (R$)"].tolist()
            
            # Formatar valores para exibição
            valores_formatados = []
            for v in valores:
                if isinstance(v, (int, float)):
                    valores_formatados.append(f"R$ {abs(v):.2f}".replace(".", ","))
                else:
                    valores_formatados.append(str(v))
            
            valores_texto = " - ".join(valores_formatados)
            st.markdown(f"**📌 {desc}** — {row['Quantidade']}x — Total: {valores_texto}")
            st.markdown(f"✔️ Categoria aplicada: {categoria}")
            df_desc.loc[df_desc["Descrição"] == desc, "Categoria"] = categoria

    # Corrigir itens sem categoria automaticamente
    faltantes = df_desc[df_desc["Categoria"].isnull() | (df_desc["Categoria"].str.strip() == "")]
    if not faltantes.empty:
        df_desc.loc[faltantes.index, "Categoria"] = "Sem Identificação"
        st.warning(f"⚠️ {len(faltantes)} descrições foram categorizadas como **Sem Identificação**.")

    # Aplicar categorias ao DataFrame original
    mapa = dict(zip(df_desc["Descrição"], df_desc["Categoria"]))
    df_transacoes["Categoria"] = df_transacoes["Descrição"].map(mapa)

    # Botão para salvar categorias
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

    # Aplicar flag "Considerar"
    try:
        plano = pd.read_csv(plano_path)
        mapa_considerar = dict(zip(plano["Categoria"], plano["Considerar"]))
        df_transacoes["Considerar"] = df_transacoes["Categoria"].map(mapa_considerar).fillna("Sim")
    except Exception as e:
        st.warning(f"Erro ao carregar plano de contas: {e}")
        df_transacoes["Considerar"] = "Sim"

    return df_transacoes, df_desc
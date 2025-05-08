import pandas as pd
import streamlit as st
import os
import re
from typing import Tuple, List, Dict

def categorizar_emprestimos(
    df_emprestimos,
    categorias_path="./logic/categorias_emprestimos.csv",
    categorias_salvas_path="./logic/categorias_emprestimos_salvas.csv",
    prefixo_key="emp"
):
    """
    Categoriza transações de empréstimos usando um arquivo específico de categorias.
    
    Args:
        df_emprestimos: DataFrame com as transações de empréstimos
        categorias_path: Caminho para o arquivo CSV de categorias de empréstimos
        categorias_salvas_path: Caminho para salvar/carregar categorizações anteriores
        prefixo_key: Prefixo para as chaves do session_state
        
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: DataFrame categorizado e DataFrame de descrições únicas
    """
    # Verificar se o DataFrame está vazio
    if df_emprestimos.empty:
        st.warning("Nenhuma transação de empréstimo para categorizar.")
        return df_emprestimos, pd.DataFrame()
    
    # Carregar categorias salvas
    if os.path.exists(categorias_salvas_path):
        df_categorias_salvas = pd.read_csv(categorias_salvas_path)
    else:
        df_categorias_salvas = pd.DataFrame(columns=["Descricao", "Categoria"])
    
    # Agrupar descrições únicas
    df_desc = (
        df_emprestimos
        .groupby("Descrição", as_index=False)
        .agg(Quantidade=("Valor (R$)", "count"), Total=("Valor (R$)", "sum"))
    )
    df_desc["Categoria"] = ""
    
    # Carregar ou criar arquivo de categorias de empréstimos
    if not os.path.exists(categorias_path):
        st.info("Criando arquivo de categorias de empréstimos...")
        
        # Criar estrutura básica de categorias de empréstimos
        categorias_emp = pd.DataFrame({
            "Grupo": ["Empréstimos"] * 8,
            "Categoria": [
                "CDC", 
                "Consignado", 
                "Crédito Pessoal", 
                "Financiamento Imobiliário",
                "Financiamento Veículos",
                "Cartão de Crédito",
                "Cheque Especial",
                "Outros Empréstimos"
            ],
            "Tipo": ["Despesa"] * 8,
            "Palavras_Chave": [
                "cdc,financiamento,credito direto",
                "consignado,folha,desconto em folha",
                "credito pessoal,emprestimo pessoal",
                "financiamento imobiliario,habitacional,casa,apartamento",
                "financiamento veiculo,carro,moto",
                "fatura,cartao,parcelamento fatura",
                "cheque especial,limite",
                "emprestimo,financiamento,contrato,parcela"
            ]
        })
        
        # Salvar arquivo
        categorias_emp.to_csv(categorias_path, index=False)
        df_categorias = categorias_emp
    else:
        # Carregar arquivo existente
        df_categorias = pd.read_csv(categorias_path)
    
    # Criar opções de categorias
    df_categorias["Opcao"] = df_categorias["Grupo"] + " :: " + df_categorias["Categoria"]
    opcoes_categorias = df_categorias["Opcao"].tolist()
    mapa_opcao_categoria = dict(zip(df_categorias["Opcao"], df_categorias["Categoria"]))
    
    # Interface principal
    st.markdown("### 🏦 Categorize os Empréstimos")
    st.info("Classifique cada empréstimo detectado em uma categoria específica.")
    
    # Exibir categorias disponíveis
    with st.expander("📘 Categorias de Empréstimos Disponíveis"):
        st.dataframe(df_categorias[["Grupo", "Categoria", "Palavras_Chave"]], use_container_width=True)
    
    # Categorização automática
    with st.expander("🤖 Categorização Automática", expanded=True):
        if st.button("Executar Categorização Automática", key=f"{prefixo_key}_auto_cat"):
            total_categorizadas = 0
            
            # Aplicar categorias salvas
            for idx, row in df_desc.iterrows():
                desc = row["Descrição"]
                if pd.isnull(row["Categoria"]) or row["Categoria"] == "":
                    # Verificar nas categorias salvas
                    categoria_salva = df_categorias_salvas[
                        df_categorias_salvas["Descricao"] == desc
                    ]["Categoria"].values
                    
                    if len(categoria_salva) > 0:
                        df_desc.at[idx, "Categoria"] = categoria_salva[0]
                        total_categorizadas += 1
            
            # Aplicar palavras-chave
            for idx, row in df_desc.iterrows():
                desc = row["Descrição"].lower()
                if pd.isnull(row["Categoria"]) or row["Categoria"] == "":
                    for _, cat_row in df_categorias.iterrows():
                        if pd.notna(cat_row["Palavras_Chave"]):
                            palavras = [p.strip().lower() for p in cat_row["Palavras_Chave"].split(",")]
                            if any(palavra in desc for palavra in palavras if palavra):
                                df_desc.at[idx, "Categoria"] = cat_row["Categoria"]
                                total_categorizadas += 1
                                break
            
            st.success(f"✅ {total_categorizadas} empréstimos categorizados automaticamente!")
    
    # Interface de busca
    with st.expander("🔍 Busca por Palavra-Chave", expanded=True):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            termo_busca = st.text_input(
                "Buscar descrições contendo:",
                key=f"{prefixo_key}_busca"
            )
        
        with col2:
            opcao_busca = st.selectbox(
                "Aplicar categoria:",
                [""] + opcoes_categorias,
                key=f"{prefixo_key}_opcao_busca"
            )
        
        if termo_busca:
            # Buscar descrições que contêm o termo
            descricoes_encontradas = df_desc[
                df_desc["Descrição"].str.contains(termo_busca, case=False, na=False)
            ]
            
            if not descricoes_encontradas.empty:
                st.success(f"✅ Encontrados {len(descricoes_encontradas)} empréstimos contendo '{termo_busca}'")
                st.dataframe(descricoes_encontradas, use_container_width=True)
                
                if opcao_busca and st.button("Aplicar Categoria aos Resultados", key=f"{prefixo_key}_aplicar_busca"):
                    categoria_escolhida = mapa_opcao_categoria.get(opcao_busca, "")
                    df_desc.loc[df_desc["Descrição"].isin(descricoes_encontradas["Descrição"]), "Categoria"] = categoria_escolhida
                    st.success(f"✅ Categoria '{categoria_escolhida}' aplicada a {len(descricoes_encontradas)} empréstimos")
            else:
                st.warning(f"Nenhum empréstimo encontrado contendo '{termo_busca}'")
    
    # Categorização manual
    st.subheader("📝 Categorização Manual")
    
    # Separar itens já categorizados e não categorizados
    itens_nao_categorizados = df_desc[df_desc["Categoria"].isnull() | (df_desc["Categoria"] == "")]
    
    if not itens_nao_categorizados.empty:
        st.info(f"{len(itens_nao_categorizados)} empréstimos aguardando categorização manual")
        
        for idx, row in itens_nao_categorizados.iterrows():
            desc = row["Descrição"]
            valores = df_emprestimos[df_emprestimos["Descrição"] == desc]["Valor (R$)"].tolist()
            
            # Formatar valores para exibição
            valores_formatados = []
            for v in valores:
                if isinstance(v, (int, float)):
                    valores_formatados.append(f"R$ {abs(v):.2f}".replace(".", ","))
                else:
                    valores_formatados.append(str(v))
            
            valores_texto = " - ".join(valores_formatados)
            
            # Exibir informações do contrato, se disponível
            contrato = ""
            if "Contrato" in df_emprestimos.columns:
                contratos = df_emprestimos[df_emprestimos["Descrição"] == desc]["Contrato"].unique()
                if len(contratos) > 0 and pd.notna(contratos[0]):
                    contrato = f" | Contrato: {contratos[0]}"
            
            label = f"📌 {desc}{contrato} — {row['Quantidade']}x — Total: {valores_texto}"
            
            categoria_escolhida = st.selectbox(
                label,
                options=[""] + opcoes_categorias,
                key=f"{prefixo_key}_{idx}"
            )
            
            categoria_limpa = mapa_opcao_categoria.get(categoria_escolhida, "")
            df_desc.at[idx, "Categoria"] = categoria_limpa
    else:
        st.success("✅ Todos os empréstimos já estão categorizados!")
    
    # Categorização em lote
    st.markdown("### 🧩 Categorização em Lote")
    coluna1, coluna2 = st.columns([3, 2])
    
    with coluna1:
        palavras_chave = st.text_input("🔍 Procurar descrições por palavra:", key=f"busca_lote_{prefixo_key}")
        descricoes_disponiveis = df_desc["Descrição"].tolist()
        
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
    
    # Aplicar categorias ao DataFrame original
    mapa = dict(zip(df_desc["Descrição"], df_desc["Categoria"]))
    df_emprestimos["Categoria"] = df_emprestimos["Descrição"].map(mapa)
    
    # Salvar categorias
    if st.button("💾 Salvar Categorias", key=f"btn_salvar_{prefixo_key}"):
        novas = pd.DataFrame({
            "Descricao": df_desc["Descrição"],
            "Categoria": df_desc["Categoria"]
        })
        novas = novas[novas["Categoria"].notna() & (novas["Categoria"].str.strip() != "")]
        
        df_categorias_salvas = (
            pd.concat([df_categorias_salvas, novas])
            .drop_duplicates(subset=["Descricao"], keep="last")
            .reset_index(drop=True)
        )
        
        df_categorias_salvas.to_csv(categorias_salvas_path, index=False)
        st.success("✅ Categorias salvas com sucesso!")
    
    return df_emprestimos, df_desc
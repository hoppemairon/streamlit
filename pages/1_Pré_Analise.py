import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime

# Módulos do projeto
from extractors.pdf_extractor import extrair_lancamentos_pdf
from extractors.txt_extractor import extrair_lancamentos_txt
from extractors.ofx_extractor import extrair_lancamentos_ofx
from logic.Analises_DFC_DRE.deduplicator import remover_duplicatas
from logic.Analises_DFC_DRE.categorizador import categorizar_transacoes
from logic.Analises_DFC_DRE.fluxo_caixa import exibir_fluxo_caixa
from logic.Analises_DFC_DRE.faturamento import coletar_faturamentos
from logic.Analises_DFC_DRE.estoque import coletar_estoques
from logic.Analises_DFC_DRE.gerador_parecer import gerar_parecer_automatico
from logic.Analises_DFC_DRE.exibir_dre import exibir_dre
from logic.Analises_DFC_DRE.analise_gpt import analisar_dfs_com_gpt

# Configuração da página
st.set_page_config(
    page_title="Pré Análise de Documentos", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Funções auxiliares
def formatar_valor_br(valor):
    """Formata um valor numérico para o formato brasileiro (R$)"""
    if isinstance(valor, (int, float)):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    elif isinstance(valor, str):
        try:
            valor_num = float(valor.replace(".", "").replace(",", "."))
            return f"R$ {valor_num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return valor
    return valor

def converter_para_float(valor_str):
    """Converte uma string de valor BR para float"""
    if isinstance(valor_str, (int, float)):
        return float(valor_str)
    try:
        return float(str(valor_str).replace("R$", "").replace(".", "").replace(",", ".").strip())
    except:
        return 0.0

def processar_arquivo(file):
    """Processa um arquivo e retorna os dataframes extraídos"""
    nome = file.name
    tipo = os.path.splitext(nome)[-1].lower()
    
    try:
        if tipo == ".pdf":
            resultado = extrair_lancamentos_pdf(file, nome)
            
            if isinstance(resultado, tuple) and resultado[0] == "debug":
                return {
                    "status": "debug",
                    "mensagem": f"Texto da primeira página do PDF ({nome}):",
                    "conteudo": resultado[1],
                    "tipo": "pdf"
                }
            
            df_resumo = pd.DataFrame(resultado["resumo"])
            df_trans = pd.DataFrame(resultado["transacoes"])
            
            return {
                "status": "sucesso",
                "resumo": df_resumo,
                "transacoes": df_trans,
                "mensagem": f"📥 {nome} → PDF → {len(df_trans)} transações, {len(df_resumo)} resumos",
                "tipo": "pdf"
            }
            
        elif tipo == ".txt":
            df_trans = pd.DataFrame(extrair_lancamentos_txt(file, nome))
            df_trans["Arquivo"] = nome
            
            return {
                "status": "sucesso",
                "transacoes": df_trans,
                "mensagem": f"📥 {nome} → TXT → {len(df_trans)} transações",
                "tipo": "txt"
            }
            
        elif tipo in [".xls", ".xlsx"]:
            df = pd.read_excel(file)
            df["Arquivo"] = nome
            
            return {
                "status": "sucesso",
                "transacoes": df,
                "mensagem": f"📥 {nome} → Excel → {len(df)} linhas",
                "tipo": "excel"
            }
            
        elif tipo == ".ofx":
            transacoes, encoding = extrair_lancamentos_ofx(file, nome)
            
            if isinstance(transacoes, str) or not transacoes:
                return {
                    "status": "erro",
                    "mensagem": f"❌ Erro ao processar {nome}: {encoding}",
                    "tipo": "ofx"
                }
                
            df = pd.DataFrame(transacoes)
            
            return {
                "status": "sucesso",
                "transacoes": df,
                "mensagem": f"📥 {nome} → OFX → {len(df)} transações (codificação: {encoding})",
                "tipo": "ofx"
            }
            
        else:
            return {
                "status": "erro",
                "mensagem": f"⚠️ Tipo de arquivo não suportado: {nome}",
                "tipo": "desconhecido"
            }
            
    except Exception as e:
        return {
            "status": "erro",
            "mensagem": f"❌ Erro ao processar {nome}: {str(e)}",
            "tipo": tipo.replace(".", "")
        }

# Inicialização do estado da aplicação
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "log_uploads" not in st.session_state:
    st.session_state.log_uploads = []
if "processamento_concluido" not in st.session_state:
    st.session_state.processamento_concluido = False
if "df_transacoes_total" not in st.session_state:
    st.session_state.df_transacoes_total = None
if "df_resumo_total" not in st.session_state:
    st.session_state.df_resumo_total = None

# Interface principal
st.title("📑 Pré-Análise de Documentos Bancários")

# Barra lateral com informações
with st.sidebar:
    st.header("ℹ️ Informações")
    st.markdown("""
    ### Tipos de arquivos suportados:
    - 📄 **PDF**: Extratos bancários em PDF
    - 📊 **Excel**: Planilhas XLS/XLSX
    - 📝 **TXT**: Arquivos de texto
    - 🏦 **OFX**: Open Financial Exchange
    
    ### Funcionalidades:
    - ✅ Extração automática de transações
    - 🔄 Remoção de duplicatas
    - 📊 Categorização de transações
    - 💰 Análise de fluxo de caixa
    - 📈 Geração de DRE
    - 🤖 Análise com IA
    """)
    
    if st.session_state.processamento_concluido:
        st.success("✅ Processamento concluído!")
        if st.session_state.df_transacoes_total is not None:
            st.metric("Total de Transações", len(st.session_state.df_transacoes_total))
        
        # Estatísticas básicas se houver dados
        if st.session_state.df_transacoes_total is not None and "Valor (R$)" in st.session_state.df_transacoes_total.columns:
            df = st.session_state.df_transacoes_total.copy()
            df["Valor_Num"] = df["Valor (R$)"].apply(converter_para_float)
            
            creditos = df[df["Valor_Num"] > 0]["Valor_Num"].sum()
            debitos = abs(df[df["Valor_Num"] <= 0]["Valor_Num"].sum())
            
            col1, col2 = st.columns(2)
            col1.metric("Total Créditos", formatar_valor_br(creditos))
            col2.metric("Total Débitos", formatar_valor_br(debitos))
            
            st.metric("Saldo", formatar_valor_br(creditos - debitos), 
                     delta=formatar_valor_br(creditos - debitos))

# Descrição principal
st.markdown("""
### 🎯 Objetivo
Este sistema realiza a pré-análise de documentos bancários, extraindo transações, categorizando-as e gerando relatórios financeiros.

### 📋 Instruções
1. Envie os arquivos bancários (.pdf, .ofx, .xlsx, .txt)
2. O sistema extrairá e consolidará os dados
3. Categorize as transações
4. Gere relatórios de fluxo de caixa e DRE
5. Obtenha análises automáticas
""")

# Uploader de arquivos
with st.expander("📎 Upload de Arquivos", expanded=True):
    uploaded_files = st.file_uploader(
        "Selecione os arquivos para análise",
        type=["pdf", "ofx", "xlsx", "txt"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}"
    )

    col1, col2 = st.columns([1, 4])
    processar = col1.button("🔄 Processar Arquivos", use_container_width=True)
    limpar = col2.button("🧹 Limpar Tudo", use_container_width=True)

# Processamento dos arquivos
if processar and uploaded_files:
    with st.spinner("Processando arquivos... ⏳"):
        st.session_state.log_uploads = []
        lista_resumos = []
        lista_transacoes = []
        
        # Barra de progresso
        progress_bar = st.progress(0)
        total_files = len(uploaded_files)
        
        for i, file in enumerate(uploaded_files):
            # Atualizar progresso
            progress_bar.progress((i + 0.5) / total_files)
            
            resultado = processar_arquivo(file)
            st.session_state.log_uploads.append(resultado["mensagem"])
            
            if resultado["status"] == "debug":
                st.code(resultado["conteudo"], language="text")
            elif resultado["status"] == "sucesso":
                if "resumo" in resultado and not resultado["resumo"].empty:
                    lista_resumos.append(resultado["resumo"])
                if "transacoes" in resultado and not resultado["transacoes"].empty:
                    lista_transacoes.append(resultado["transacoes"])
            elif resultado["status"] == "erro":
                st.error(resultado["mensagem"])
            
            # Atualizar progresso
            progress_bar.progress((i + 1) / total_files)
        
        # Consolidar dados
        if lista_resumos:
            st.session_state.df_resumo_total = pd.concat(lista_resumos, ignore_index=True)
        else:
            st.session_state.df_resumo_total = None
            
        if lista_transacoes:
            df_transacoes_total = pd.concat(lista_transacoes, ignore_index=True)
            df_transacoes_total = remover_duplicatas(df_transacoes_total)
            
            # Formatar valores
            if "Valor (R$)" in df_transacoes_total.columns:
                df_transacoes_total["Valor (R$)"] = df_transacoes_total["Valor (R$)"].apply(formatar_valor_br)
            
            st.session_state.df_transacoes_total = df_transacoes_total
            st.session_state.processamento_concluido = True
        else:
            st.session_state.df_transacoes_total = None
            
        # Finalizar progresso
        progress_bar.progress(100)
        st.success("✅ Processamento concluído!")

# Limpar dados
if limpar:
    nova_key = st.session_state.get("uploader_key", 0) + 1
    st.session_state.clear()
    st.session_state.uploader_key = nova_key
    st.rerun()

# Exibir logs de upload
if st.session_state.log_uploads:
    with st.expander("📄 Logs de Processamento", expanded=True):
        for log in st.session_state.log_uploads:
            st.info(log)

# Exibir resumo das contas
if st.session_state.df_resumo_total is not None:
    with st.expander("📋 Resumo das Contas", expanded=True):
        st.dataframe(st.session_state.df_resumo_total, use_container_width=True)

# Processar transações
if st.session_state.df_transacoes_total is not None:
    df_transacoes_total = st.session_state.df_transacoes_total
    
    # Separar em abas
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["📊 Categorização",
         "💹 Faturamento e Estoque",
         "💰 Fluxo de Caixa",
         "📈 DRE", 
         "💼 Análise Sistema",
         "🤖 Análise IA"])
    
    with tab1:
        st.header("📊 Categorização de Transações")
        
        # Dividir em créditos e débitos para categorização
        df_valores_num = df_transacoes_total.copy()
        if "Valor (R$)" in df_valores_num.columns:
            df_valores_num["Valor_Num"] = df_valores_num["Valor (R$)"].apply(converter_para_float)
            df_creditos = df_valores_num[df_valores_num["Valor_Num"] > 0].copy()
            df_debitos = df_valores_num[df_valores_num["Valor_Num"] <= 0].copy()
            
            # Remover coluna temporária
            if "Valor_Num" in df_creditos.columns:
                df_creditos = df_creditos.drop(columns=["Valor_Num"])
            if "Valor_Num" in df_debitos.columns:
                df_debitos = df_debitos.drop(columns=["Valor_Num"])
            
            # Categorizar créditos
            st.subheader("💰 Categorizar Créditos")
            df_creditos, df_desc_creditos = categorizar_transacoes(df_creditos, prefixo_key="credito", tipo_lancamento="Crédito")
            
            # Exibir resumo da categorização de créditos
            if not df_creditos.empty and "Categoria" in df_creditos.columns:
                with st.expander("✅ Resumo da Categorização de Créditos", expanded=True):
                    # Agrupar por categoria para mostrar totais
                    resumo_creditos = df_creditos.groupby("Categoria").agg(
                        Total=("Valor (R$)", lambda x: sum(converter_para_float(v) for v in x)),
                        Quantidade=("Valor (R$)", "count")
                    ).reset_index()
                    
                    # Formatar o total
                    resumo_creditos["Total"] = resumo_creditos["Total"].apply(formatar_valor_br)
                    
                    # Exibir tabela de resumo
                    st.dataframe(resumo_creditos, use_container_width=True)
                    
                    # Mostrar itens categorizados automaticamente
                    st.markdown("##### 🤖 Itens Categorizados Automaticamente")
                    
                    # Filtrar apenas itens com categoria não vazia
                    df_auto_cat = df_desc_creditos[df_desc_creditos["Categoria"].notna() & (df_desc_creditos["Categoria"] != "")]
                    
                    if not df_auto_cat.empty:
                        for _, row in df_auto_cat.iterrows():
                            desc = row["Descrição"]
                            cat = row["Categoria"]
                            qtd = row["Quantidade"]
                            total = row["Total"]
                            
                            # Formatar o total se for numérico
                            if isinstance(total, (int, float)):
                                total_fmt = formatar_valor_br(total)
                            else:
                                total_fmt = total
                                
                            st.markdown(f"**📌 {desc}** — {qtd}x — Total: {total_fmt} → ✅ **{cat}**")
                    else:
                        st.info("Nenhum item foi categorizado automaticamente.")
            
            # Categorizar débitos
            st.subheader("💸 Categorizar Débitos")
            df_debitos, df_desc_debitos = categorizar_transacoes(df_debitos, prefixo_key="debito", tipo_lancamento="Débito")
            
            # Exibir resumo da categorização de débitos
            if not df_debitos.empty and "Categoria" in df_debitos.columns:
                with st.expander("✅ Resumo da Categorização de Débitos", expanded=True):
                    # Agrupar por categoria para mostrar totais
                    resumo_debitos = df_debitos.groupby("Categoria").agg(
                        Total=("Valor (R$)", lambda x: sum(abs(converter_para_float(v)) for v in x)),
                        Quantidade=("Valor (R$)", "count")
                    ).reset_index()
                    
                    # Formatar o total
                    resumo_debitos["Total"] = resumo_debitos["Total"].apply(formatar_valor_br)
                    
                    # Exibir tabela de resumo
                    st.dataframe(resumo_debitos, use_container_width=True)
                    
                    # Mostrar itens categorizados automaticamente
                    st.markdown("##### 🤖 Itens Categorizados Automaticamente")
                    
                    # Filtrar apenas itens com categoria não vazia
                    df_auto_cat = df_desc_debitos[df_desc_debitos["Categoria"].notna() & (df_desc_debitos["Categoria"] != "")]
                    
                    if not df_auto_cat.empty:
                        for _, row in df_auto_cat.iterrows():
                            desc = row["Descrição"]
                            cat = row["Categoria"]
                            qtd = row["Quantidade"]
                            total = row["Total"]
                            
                            # Formatar o total se for numérico
                            if isinstance(total, (int, float)):
                                total_fmt = formatar_valor_br(total)
                            else:
                                total_fmt = total
                                
                            st.markdown(f"**📌 {desc}** — {qtd}x — Total: {total_fmt} → ✅ **{cat}**")
                    else:
                        st.info("Nenhum item foi categorizado automaticamente.")
            
            # Juntar tudo novamente
            df_transacoes_total = pd.concat([df_creditos, df_debitos], ignore_index=True)
            
            # Garantir que a coluna Considerar exista
            if "Considerar" not in df_transacoes_total.columns:
                df_transacoes_total["Considerar"] = "Sim"
            
            # Atualizar o estado
            st.session_state.df_transacoes_total = df_transacoes_total
            
            # Exibir transações categorizadas
            st.subheader("📋 Todas as Transações Categorizadas")
            
            # Adicionar filtros para a visualização
            col1, col2, col3 = st.columns(3)
            with col1:
                filtro_tipo = st.multiselect(
                    "Filtrar por Tipo:",
                    options=["Crédito", "Débito"],
                    default=["Crédito", "Débito"]
                )
            with col2:
                categorias_disponiveis = sorted(df_transacoes_total["Categoria"].dropna().unique().tolist())
                filtro_categoria = st.multiselect(
                    "Filtrar por Categoria:",
                    options=categorias_disponiveis,
                    default=[]
                )
            with col3:
                filtro_texto = st.text_input("Buscar na descrição:", "")
            
            # Aplicar filtros
            df_filtrado = df_transacoes_total.copy()
            
            # Filtro por tipo
            if filtro_tipo and len(filtro_tipo) < 2:  # Se não estiverem ambos selecionados
                if "Crédito" in filtro_tipo:
                    df_filtrado = df_filtrado[df_filtrado["Valor (R$)"].apply(
                        lambda x: converter_para_float(x) > 0 if pd.notna(x) else False
                    )]
                elif "Débito" in filtro_tipo:
                    df_filtrado = df_filtrado[df_filtrado["Valor (R$)"].apply(
                        lambda x: converter_para_float(x) <= 0 if pd.notna(x) else False
                    )]
            
            # Filtro por categoria
            if filtro_categoria:
                df_filtrado = df_filtrado[df_filtrado["Categoria"].isin(filtro_categoria)]
            
            # Filtro por texto na descrição
            if filtro_texto:
                df_filtrado = df_filtrado[df_filtrado["Descrição"].str.contains(filtro_texto, case=False, na=False)]
            
            # Exibir DataFrame filtrado
            st.dataframe(df_filtrado, use_container_width=True)
            
            # Mostrar estatísticas do filtro
            st.info(f"Exibindo {len(df_filtrado)} de {len(df_transacoes_total)} transações.")
            
            # Botão para download
            output = io.BytesIO()
            df_transacoes_total.to_excel(output, index=False)
            output.seek(0)
            
            st.download_button(
                label="📥 Baixar transações categorizadas (.xlsx)",
                data=output,
                file_name=f"transacoes_categorizadas_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    

    with tab2:
        st.header("💹 Faturamento e Estoque")
        
        # Adicionar faturamento
        df_faturamento = coletar_faturamentos(df_transacoes_total)
        
        # Adicionar estoque
        coletar_estoques(df_transacoes_total)

    with tab3:
        st.header("💰 Fluxo de Caixa")
        
        # Exibir fluxo de caixa
        if st.button("📊 Gerar Fluxo de Caixa", key="btn_fluxo"):
            with st.spinner("Gerando fluxo de caixa... ⏳"):
                resultado_fluxo = exibir_fluxo_caixa(df_transacoes_total)
                
                # Salvar resultado para uso na análise GPT
                st.session_state.resultado_fluxo = resultado_fluxo
    
    with tab4:
        st.header("📈 Demonstrativo de Resultados (DRE)")
        
        if st.button("📊 Gerar DRE", key="btn_dre"):
            with st.spinner("Gerando DRE... ⏳"):
                resultado_fluxo = exibir_fluxo_caixa(df_transacoes_total)
                resultado_dre = exibir_dre(df_fluxo=resultado_fluxo)
                st.session_state.resultado_fluxo = resultado_fluxo
                st.session_state.resultado_dre = resultado_dre
        
        # if st.button("🧾 Gerar Parecer Diagnóstico", key="btn_parecer"):
        #    with st.spinner("Gerando parecer diagnóstico... ⏳"):
        #        gerar_parecer_automatico()
    
    with tab5:
        st.header("💼 Análise Sistema")
        
        if st.button("🧾 Gerar Parecer Diagnóstico", key="btn_parecer"):
            with st.spinner("Gerando parecer diagnóstico... ⏳"):
                df_transacoes_total = st.session_state.df_transacoes_total
                resultado_fluxo = st.session_state.get("resultado_fluxo", exibir_fluxo_caixa(df_transacoes_total))
                gerar_parecer_automatico(resultado_fluxo)

    with tab6:
        st.header("🤖 Análise GPT - Parecer Financeiro Inteligente")
        
        descricao_empresa = st.text_area(
            "📝 Conte um pouco sobre a empresa:",
            placeholder="Ex.: área de atuação, tempo de mercado, porte, número de funcionários, etc.",
            help="Estas informações ajudarão a IA a gerar um parecer mais preciso e contextualizado."
        )
        
        col1, col2 = st.columns([1, 3])
        
        if col1.button("📊 Gerar Parecer com ChatGPT", use_container_width=True):
            if not descricao_empresa.strip():
                st.warning("⚠️ Por favor, preencha a descrição da empresa antes de gerar o parecer.")
            else:
                with st.spinner("Gerando parecer financeiro com inteligência artificial... ⏳"):
                    # Verificar se já temos os resultados de DRE e fluxo de caixa
                    resultado_fluxo = st.session_state.get("resultado_fluxo", exibir_fluxo_caixa(df_transacoes_total))
                    resultado_dre = st.session_state.get("resultado_dre", exibir_dre(df_fluxo=resultado_fluxo))
                    
                    parecer = analisar_dfs_com_gpt(resultado_dre, resultado_fluxo, descricao_empresa)
                
                st.success("✅ Parecer gerado com sucesso!")
                
                # Exibir o parecer em um formato mais agradável
                #st.markdown("### 📝 Parecer Financeiro")
                #st.markdown(parecer)
                
                # Opção para download do parecer
                #st.download_button(
                #    label="📥 Baixar Parecer (.txt)",
                #    data=parecer,
                #    file_name=f"parecer_financeiro_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                #    mime="text/plain"
                #)

# Rodapé
st.markdown("---")
st.caption("© 2025 Sistema de Análise Financeira | Versão 1.0")
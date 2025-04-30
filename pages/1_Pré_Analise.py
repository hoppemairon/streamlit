import streamlit as st
import pandas as pd
import io
import os

# Módulos do projeto
from extractors.pdf_extractor import extrair_lancamentos_pdf
from extractors.txt_extractor import extrair_lancamentos_txt
from extractors.ofx_extractor import extrair_lancamentos_ofx
from logic.deduplicator import remover_duplicatas
from logic.categorizador import categorizar_transacoes
from logic.fluxo_caixa import exibir_fluxo_caixa
from logic.faturamento import coletar_faturamentos
from logic.estoque import coletar_estoques
from logic.gerador_parecer import gerar_parecer_automatico
from logic.exibir_dre import exibir_dre
from logic.analise_gpt import analisar_dfs_com_gpt


# Layout
st.set_page_config(page_title="Pré Análise de Documentos", layout="wide")
st.title("📑 Pré-Análise de Documentos Bancários")

st.markdown("""
Envie arquivos bancários (.pdf, .ofx, .xlsx, .txt).  
O sistema irá identificar o tipo, extrair os dados e consolidar tudo sem duplicidades.
""")

# Estado inicial
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "log_uploads" not in st.session_state:
    st.session_state.log_uploads = []

# Uploader
uploaded_files = st.file_uploader(
    "📎 Envie os arquivos",
    type=["pdf", "ofx", "xlsx", "txt"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)

lista_resumos = []
lista_transacoes = []

# Processamento
if uploaded_files:
    st.session_state.log_uploads.clear()

    for file in uploaded_files:
        nome = file.name
        tipo = os.path.splitext(nome)[-1].lower()

        if tipo == ".pdf":
            resultado = extrair_lancamentos_pdf(file, nome)

            if isinstance(resultado, tuple) and resultado[0] == "debug":
                st.markdown(f"### 🧾 Texto da primeira página do PDF ({nome}):")
                st.code(resultado[1], language="text")
                continue

            df_resumo = pd.DataFrame(resultado["resumo"])
            df_trans = pd.DataFrame(resultado["transacoes"])

            if not df_resumo.empty:
                lista_resumos.append(df_resumo)
            if not df_trans.empty:
                lista_transacoes.append(df_trans)

            st.session_state.log_uploads.append(
                f"📥 {nome} → PDF → {len(df_trans)} transações, {len(df_resumo)} resumo"
            )

        elif tipo == ".txt":
            df_trans = pd.DataFrame(extrair_lancamentos_txt(file, nome))
            df_trans["Arquivo"] = nome
            lista_transacoes.append(df_trans)
            st.session_state.log_uploads.append(f"📥 {nome} → TXT → {len(df_trans)} transações")

        elif tipo in [".xls", ".xlsx"]:
            try:
                df = pd.read_excel(file)
                df["Arquivo"] = nome
                lista_transacoes.append(df)
                st.session_state.log_uploads.append(f"📥 {nome} → Excel → {len(df)} linhas")
            except Exception as e:
                st.warning(f"Erro ao ler Excel: {e}")

        elif tipo == ".ofx":
            transacoes, encoding = extrair_lancamentos_ofx(file, nome)
            if isinstance(transacoes, str) or not transacoes:
                st.error(f"❌ Erro ao processar {nome}: {encoding}")
                continue

            df = pd.DataFrame(transacoes)
            lista_transacoes.append(df)
            st.session_state.log_uploads.append(f"📥 {nome} → OFX → {len(df)} transações (codificação: {encoding})")

        else:
            st.warning(f"Tipo de arquivo não suportado: {nome}")

# Logs
if st.session_state.log_uploads:
    st.markdown("### 📄 Resultado do upload:")
    for log in st.session_state.log_uploads:
        st.info(log)

# Exibição dos dados
if lista_resumos:
    df_resumo_total = pd.concat(lista_resumos, ignore_index=True)
    st.markdown("### 📋 Resumo das Contas:")
    st.dataframe(df_resumo_total, use_container_width=True)

if lista_transacoes:
    df_transacoes_total = pd.concat(lista_transacoes, ignore_index=True)
    df_transacoes_total = remover_duplicatas(df_transacoes_total)

    # Formata valor em BR
    df_transacoes_total["Valor (R$)"] = df_transacoes_total["Valor (R$)"].apply(
        lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    # Divide em créditos e débitos
    df_creditos = df_transacoes_total[df_transacoes_total["Valor (R$)"].str.replace(".", "").str.replace(",", ".").astype(float) > 0].copy()
    df_debitos = df_transacoes_total[df_transacoes_total["Valor (R$)"].str.replace(".", "").str.replace(",", ".").astype(float) <= 0].copy()

    # Categoriza
    st.markdown("## 💰 Categorizar Créditos")
    df_creditos, _ = categorizar_transacoes(df_creditos, prefixo_key="credito", tipo_lancamento="Crédito")

    st.markdown("## 💸 Categorizar Débitos")
    df_debitos, _ = categorizar_transacoes(df_debitos, prefixo_key="debito", tipo_lancamento="Débito")

    # Junta tudo de novo
    df_transacoes_total = pd.concat([df_creditos, df_debitos], ignore_index=True)

    st.markdown("### 📊 Transações Categorizadas:")
    st.dataframe(df_transacoes_total, use_container_width=True)

    output = io.BytesIO()
    df_transacoes_total.to_excel(output, index=False)
    output.seek(0)

    st.download_button(
        label="📥 Baixar transações categorizadas (.xlsx)",
        data=output,
        file_name="transacoes_categorizadas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Garante que a coluna Considerar exista
    if "Considerar" not in df_transacoes_total.columns:
        df_transacoes_total["Considerar"] = "Sim"

    #Adicionar o Faturamento
    if "df_transacoes_total" in locals():
        df_faturamento = coletar_faturamentos(df_transacoes_total)

    #Adicionar o Estoque
    coletar_estoques(df_transacoes_total)

    # Botão para mostrar o fluxo de caixa
    if st.button("📊 Gerar Fluxo de Caixa"):
        st.markdown("---")
        st.header("📆 Demonstrativo do Fluxo de Caixa")
        exibir_fluxo_caixa(df_transacoes_total)
        exibir_dre()

    st.markdown("---")
    st.header("🤖 Análise GPT - Parecer Financeiro Inteligente")

    descricao_empresa = st.text_area("📝 Conte um pouco sobre a empresa (Ex.: área de atuação, tempo de mercado, porte, etc):")

    
    
    if st.button("📊 Gerar Parecer com ChatGPT"):
        if not descricao_empresa.strip():
            st.warning("⚠️ Por favor, preencha a descrição da empresa antes de gerar o parecer.")
        else:
            with st.spinner("Gerando parecer financeiro com inteligência artificial... ⏳"):
                parecer = analisar_dfs_com_gpt(exibir_dre(), exibir_fluxo_caixa(df_transacoes_total), descricao_empresa)

            st.success("✅ Parecer gerado com sucesso!")
            #st.markdown(parecer)

     # Botão para gerar parecer
    if st.button("🧾 Gerar Parecer Diagnóstico"):
        gerar_parecer_automatico()

# Limpar Tela
st.markdown("---")
if st.button("🧹 Limpar Tela"):
    nova_key = st.session_state.get("uploader_key", 0) + 1
    st.session_state.clear()
    st.session_state.uploader_key = nova_key
    st.rerun()
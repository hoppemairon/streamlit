import streamlit as st
import pandas as pd
import io
from extractors.ofx_extractor import extrair_lancamentos_ofx

st.set_page_config(page_title="Conversor OFX", layout="wide")
st.title("💸 Leitor de Arquivos OFX")

# Inicializa estados
if 'df_ofx' not in st.session_state:
    st.session_state.df_ofx = None
if 'mensagens' not in st.session_state:
    st.session_state.mensagens = []
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

# Uploader com chave dinâmica
uploaded_files = st.file_uploader(
    "📁 Envie os arquivos .OFX aqui",
    type=["ofx"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)

# Processamento
if uploaded_files:
    todas_transacoes = []
    st.session_state.mensagens.clear()

    for file in uploaded_files:
        transacoes, encoding = extrair_lancamentos_ofx(file, file.name)

        if isinstance(transacoes, str) or not transacoes:
            st.error(f"❌ Erro ao processar {file.name}: {encoding}")
            continue

        st.success(f"✅ {file.name} processado com sucesso (codificação: {encoding})")
        todas_transacoes.extend(transacoes)

    # Monta o DataFrame
    df = pd.DataFrame(todas_transacoes)

    if not df.empty:
        # Formata valor para BR
        df["Valor (R$)"] = df["Valor (R$)"].map(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.session_state.df_ofx = df

# Exibe mensagens
if st.session_state.mensagens:
    for msg in st.session_state.mensagens:
        st.info(msg)

# Exibe resultados
if st.session_state.df_ofx is not None:
    st.success(f"{len(st.session_state.df_ofx)} transações carregadas.")
    st.dataframe(st.session_state.df_ofx, use_container_width=True)

    output = io.BytesIO()
    st.session_state.df_ofx.to_excel(output, index=False)
    output.seek(0)

    st.download_button(
        label="📥 Baixar Excel Consolidado",
        data=output,
        file_name="transacoes_ofx_consolidado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Limpar tela
if st.session_state.df_ofx is not None:
    if st.button("🧹 Limpar Tela"):
        st.session_state.df_ofx = None
        st.session_state.mensagens = []
        st.session_state.uploader_key += 1
        st.rerun()
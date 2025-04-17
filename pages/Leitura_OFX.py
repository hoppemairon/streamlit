import streamlit as st
import pandas as pd
import io
import chardet
from ofxparse import OfxParser

st.set_page_config(page_title="Leitor de Arquivos OFX", layout="centered")
st.title("💸 Leitor de Arquivos OFX")

# Estado da interface
if 'df_ofx' not in st.session_state:
    st.session_state.df_ofx = None
if 'mensagens' not in st.session_state:
    st.session_state.mensagens = []
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0  # chave dinâmica pro uploader

def convert_to_utf8(file_bytes, file_name):
    result = chardet.detect(file_bytes)
    encoding = result['encoding']

    if encoding:
        if encoding.lower() == 'utf-8':
            st.session_state.mensagens.append(f"✅ Arquivo **{file_name}** já está em UTF-8.")
            return file_bytes
        else:
            st.session_state.mensagens.append(f"🔄 Arquivo **{file_name}** será convertido de `{encoding}` para UTF-8.")
            try:
                data = file_bytes.decode(encoding)
            except UnicodeDecodeError:
                for enc in ['latin1', 'iso-8859-1', 'windows-1252']:
                    try:
                        data = file_bytes.decode(enc)
                        st.session_state.mensagens.append(f"✔️ Decodificado com sucesso com `{enc}`.")
                        break
                    except UnicodeDecodeError:
                        continue
            return data.encode('utf-8')

    st.session_state.mensagens.append(f"⚠️ Não foi possível detectar a codificação do arquivo **{file_name}**.")
    return file_byte

# uploader com chave dinâmica
uploaded_files = st.file_uploader(
    "📁 Envie os arquivos .OFX aqui",
    type=["ofx"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)

# processamento
if uploaded_files:
    todas_transacoes = []
    st.session_state.mensagens.clear()

    for file in uploaded_files:
        file_bytes = file.read()
        utf8_data = convert_to_utf8(file_bytes, file.name)
        ofx = OfxParser.parse(io.StringIO(utf8_data.decode("utf-8")))

        for transaction in ofx.account.statement.transactions:
            todas_transacoes.append({
                "Arquivo": file.name,
                "Data": transaction.date.strftime('%d/%m/%Y'),
                "Descrição": transaction.memo,
                "Valor": transaction.amount,
                "TRNTYPE": transaction.type,
                "Tipo": "Crédito" if transaction.type.upper() == "CREDIT" else "Débito"
            })

    df = pd.DataFrame(todas_transacoes)

    if not df.empty:
        df["Valor"] = df["Valor"].map(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.session_state.df_ofx = df

# exibe avisos
if st.session_state.mensagens:
    for msg in st.session_state.mensagens:
        st.info(msg)

# exibe dados
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

# botão limpar que reinicia tudo
if st.session_state.df_ofx is not None:
    if st.button("🧹 Limpar Tela"):
        st.session_state.df_ofx = None
        st.session_state.mensagens = []
        st.session_state.uploader_key += 1  # muda a chave = reinicia uploader
        st.rerun()
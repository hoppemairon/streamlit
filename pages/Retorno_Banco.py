import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Leitor CNAB240 .RET", layout="centered")
st.title("📄 Leitor de Arquivo CNAB240 (.RET)")

st.markdown("Faça o upload de um arquivo `.RET` (CNAB240) para extrair os dados de **pagamentos (Segmento J)** e gerar um arquivo Excel.")

# Estado da sessão
if "df_ret" not in st.session_state:
    st.session_state.df_ret = None
if "uploader_key_ret" not in st.session_state:
    st.session_state.uploader_key_ret = 0

def ler_cnab240_segmento_j(conteudo_arquivo):
    registros = []

    for linha in conteudo_arquivo.splitlines():
        if len(linha) >= 150 and linha[13] == 'J':
            nome_favorecido = linha[61:90].strip()
            data_pagamento = linha[91:100]
            valor = linha[101:115].strip()

            if "0" in nome_favorecido:
                nome_favorecido = nome_favorecido.replace("0", "")

            try:
                data_formatada = f"{data_pagamento[0:2]}/{data_pagamento[2:4]}/{data_pagamento[4:8]}"
                valor_formatado = int(valor) / 100 if valor.isdigit() else 0
            except:
                data_formatada = ""
                valor_formatado = 0

            registros.append({
                'Favorecido': nome_favorecido,
                'Data Pagamento': data_formatada,
                'Valor (R$)': f"{valor_formatado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            })

    return pd.DataFrame(registros)

# Uploader com key dinâmica
uploaded_file = st.file_uploader(
    "📁 Envie o arquivo .RET aqui",
    type=["ret", "txt"],
    key=f"uploader_ret_{st.session_state.uploader_key_ret}"
)

# Processamento
if uploaded_file:
    conteudo = uploaded_file.read().decode("utf-8", errors="ignore")
    df = ler_cnab240_segmento_j(conteudo)

    if not df.empty:
        st.success(f"{len(df)} pagamentos encontrados.")
        st.session_state.df_ret = df
    else:
        st.warning("❌ Nenhum pagamento (Segmento J) foi encontrado neste arquivo.")

# Exibição
if st.session_state.df_ret is not None:
    st.dataframe(st.session_state.df_ret, use_container_width=True)

    output = io.BytesIO()
    st.session_state.df_ret.to_excel(output, index=False)
    output.seek(0)

    st.download_button(
        label="📥 Baixar Excel",
        data=output,
        file_name="pagamentos_cnab240.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Botão limpar
if st.session_state.df_ret is not None:
    if st.button("🧹 Limpar Tela"):
        st.session_state.df_ret = None
        st.session_state.uploader_key_ret += 1  # força reset do uploader
        st.rerun()      
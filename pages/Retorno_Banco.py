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

codigo_ocorrencias = {
    "00": "Crédito efetuado",
    "01": "Insuficiência de fundos",
    "02": "Crédito cancelado pelo pagador/credor",
    "03": "Débito autorizado pela agência - efetuado",
    "HA": "Lote não aceito",
    "HB": "Inscrição da empresa inválida para o contrato",
    "HC": "Convênio com a empresa inexistente/inválido para o contrato",
    "HD": "Agência/conta corrente da empresa inexistente/inválida para o contrato",
    "HE": "Tipo de serviço inválido para o contrato",
    "HF": "Conta-Corrente da Empresa com saldo insuficiente",
    "H4": "Retorno de Crédito não Pago",
    "AA": "Controle inválido",
    "AB": "Tipo de operação inválido",
    "AC": "Tipo de serviço inválido",
    "AD": "Forma de lançamento inválida",
    "AE": "Tipo/número de inscrição inválido",
    "AF": "Código do convênio inválido",
    "AG": "Agência/conta corrente/Dv inválido",
    "AH": "Número seqüencial do registro do lote inválido",
    "AI": "Código do Segmento de Detalhe inválido",
    "AJ": "Tipo de movimento inválido",
    "AK": "Código da câmara de compensação do favorecido inválido",
    "AL": "Código do Banco Favorecido, Instituição de Pagamento ou Depositário Inválido",
    "AM": "Agência mantenedora da conta corrente do favorecido inválida",
    "AN": "Conta Corrente/DV/Conta de Pagamento do Favorecido Inválido",
    "AO": "Nome do favorecido não informado",
    "AP": "Data do lançamento inválida",
    "AQ": "Tipo/quantidade de moeda inválido",
    "AR": "Valor do lançamento inválido",
    "AS": "Aviso ao favorecido - Identificação inválida",
    "AT": "Tipo/número de inscrição do favorecido inválido",
    "AU": "Logradouro do favorecido não informado",
    "AV": "Número do local do favorecido não informado",
    "AW": "Cidade do favorecido não informado",
    "AX": "Cep/complemento do favorecido inválido",
    "AY": "Sigla do estado do favorecido inválida",
    "AZ": "Código/nome do banco depositário inválido",
    "BA": "Código/nome da agência depositária não informado",
    "BB": "Seu número inválido",
    "BC": "Nosso número inválido",
    "BD": "Confirmação de pagamento agendado",
    "BE": "Código do pagamento inválido",
    "BF": "Período de competência inválido",
    "BG": "Mês de competência inválido",
    "BH": "Ano de competência inválido",
    "BI": "Competência 13 não pode ser antecipada",
    "BJ": "Identificador de pagamento inválido",
    "BK": "Valor da multa inválido",
    "BL": "Valor mínimo de GPS - R$10,00",
    "BM": "Código de Operação para o sistema BLV inválido",
    "BN": "STR006 ou TED fora do horário",
    "BO": "Pagamento em agência do mesmo estado do favorecido",
    "BP": "Erro na validação do código de barras",
    "BQ": "Inconsistência do código de barras da GPS",
    "CC": "Dígito verificador geral inválido",
    "CF": "Valor do Documento Inválido",
    "CI": "Valor de Mora Inválido",
    "CJ": "Valor da Multa Inválido",
    "DD": "Duplicidade de DOC",
    "DT": "Duplicidade de Título",
    "TA": "Lote não aceito - totais de lote com diferença.",
    "XA": "TED Agendada cancelada pelo Piloto.",
    "XC": "TED cancelada pelo Piloto.",
    "XD": "Devolução do SPB.",
    "XE": "Devolução do SPB por erro.",
    "XP": "Devolução do SPB por situação especial.",
    "XR": "Movimento entre contas inválido.",
    "YA": "Título não encontrado.",
    "ZA": "Agência / Conta do Favorecido substituído.",
    "ZI": "Beneficiário divergente",
    "57": "Divergência na indicação da agência, conta corrente, nome ou CNPJ/CPF do favorecido."
}

def ler_cnab240_segmento_j(conteudo_arquivo):
    registros = []

    for linha in conteudo_arquivo.splitlines():
        if len(linha) >= 150 and linha[13] == 'J':
            nome_favorecido = linha[61:90].strip()
            data_pagamento = linha[91:100]
            valor = linha[101:115].strip()
            codigo_pagamento = linha[230:235].strip()
            descricao_confirmacao = codigo_ocorrencias.get(codigo_pagamento, codigo_pagamento)

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
                'Valor (R$)': f"{valor_formatado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                'Codigo':  codigo_pagamento,
                'Descrição': descricao_confirmacao
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

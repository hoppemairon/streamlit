import streamlit as st
import pandas as pd
import io
import unidecode
import os
from dotenv import load_dotenv

load_dotenv()

print(os.getenv("API_MR_URL"))
print(os.getenv("API_MR_KEY"))

from logic.Sistema_MR.API_MR import buscar_lancamentos_api

st.set_page_config(page_title="Leitor CNAB240 .RET", layout="wide")
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
            valor = linha[101:114].strip()
            valor_pago = linha[27:36].strip()
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
                #'Valor (R$)': f"{valor_formatado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                'Valor Pago (R$)': f"{int(valor_pago) / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
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
        # Expansor para análise adicional com API MR
    with st.expander("🔍 Analisar com dados da API MR"):
        EMPRESAS_MR = {
            "GRUPO ROTA - ARARANGUA": "772644ba-3a49-4736-8443-f057581d6b39",
            "GRUPO ROTA - TERRA DE AREIA": "4d49850f-ebf1-433d-a32a-527b54e856aa",
            "GRUPO ROTA - CAMINHO DO SOL": "d5ecbd61-8d4a-4ac6-8cc9-7c4919ead401",
            "GRUPO ROTA - JAGUARUNA": "149653c2-f107-4c60-aad0-b034789c8504",
            "GRUPO ROTA - PARADOURO": "735b6b4e-5513-4bb5-a9c4-50d92462921d",
            "GRUPO ROTA - SÃO PAULO": "1db3be97-a6d6-484a-b75b-fc1bdc6c487a",
            "GRUPO ROTA - ELDORADO": "93f44c44-bfd4-417f-bad2-20933e5c0228",
            "GRUPO ROTA - PINHEIRO MACHADO": "a13229ca-0f8a-442a-91ab-27e0adc1810b",
            "GRUPO ROTA - SEBERI": "eb84222f-2e6b-4f68-8457-760d10e24043",
            "GRUPO ROTA - POA IPIRANGA": "85d3091d-af31-4cb5-86fc-1558aaefa19b",
            "GRUPO ROTA - CRISTAL": "7a078786-1d9e-4433-9d63-8dfc58130b5f",
            "GRUPO ROTA - PORTO ALEGRE": "73a32cc3-d7ac-48d7-91d7-9046045d0bd7",
            "GRUPO ROTA - PARADOURO REST.": "cad79622-124a-4dc0-9408-7da5227576f0",
            "GRUPO ROTA - TRANSPORTADORA": "3885ddf8-f0ac-4468-98ab-97a248e29150"
        }

        empresa_nome = st.selectbox("Selecione a empresa (MR):", list(EMPRESAS_MR.keys()))
        id_empresa = EMPRESAS_MR[empresa_nome]

        api_url = os.getenv("API_MR_URL")
        chave_api = os.getenv("API_MR_KEY")

        if st.button("🔄 Buscar dados da MR"):
            df_api_mr = buscar_lancamentos_api(ids_empresa=id_empresa, anos="2025")

            if df_api_mr.empty or "data" not in df_api_mr.columns or "valor" not in df_api_mr.columns:
                st.warning("⚠️ Nenhum dado útil retornado da API da MR ou estrutura inesperada.")
            else:
                st.success(f"{len(df_api_mr)} registros carregados da MR para a empresa selecionada.")
                #st.dataframe(df_api_mr, use_container_width=True)

                # 🔄 Cruzamento de dados
                df_ret = st.session_state.df_ret.copy()
                df_ret["Data"] = pd.to_datetime(df_ret["Data Pagamento"], dayfirst=True, errors="coerce").dt.date
                df_ret["Valor Pago (R$)"] = df_ret["Valor Pago (R$)"].str.replace(".", "", regex=False).str.replace(",", ".").astype(float)

                df_api_mr["data"] = pd.to_datetime(df_api_mr["data"], errors="coerce").dt.date
                df_api_mr["valor"] = pd.to_numeric(df_api_mr["valor"], errors="coerce")

                # 🧠 Cruzamento por nome (Favorecido vs. Contato MR)
                st.subheader("🧠 Cruzamento por Nome (Favorecido vs. Contato MR)")

                def normalizar_nome(texto):
                    if not isinstance(texto, str):
                        return ""
                    return unidecode.unidecode(texto).lower().strip()

                df_ret["nome_norm"] = df_ret["Favorecido"].apply(normalizar_nome)
                df_api_mr["contato_norm"] = df_api_mr["contato"].apply(normalizar_nome)

                resultados = []
                for _, linha_ret in df_ret.iterrows():
                    possiveis = df_api_mr[df_api_mr["contato_norm"].str.contains(linha_ret["nome_norm"], na=False)]
                    if not possiveis.empty:
                        linha_mr = possiveis.iloc[0]
                        resultados.append({
                            "Data": linha_ret["Data"].strftime("%d/%m/%Y"),
                            "Descrição": linha_ret["Favorecido"],
                            "Valor": linha_ret["Valor Pago (R$)"],
                            "Contato": linha_mr["contato"],
                            "Categoria": linha_mr.get("categoria", "")
                        })
                    else:
                        resultados.append({
                            "Data": linha_ret["Data"].strftime("%d/%m/%Y"),
                            "Descrição": linha_ret["Favorecido"],
                            "Valor": linha_ret["Valor Pago (R$)"],
                            "Contato": "",
                            "Categoria": ""
                        })

                df_fuzzy = pd.DataFrame(resultados)
                st.dataframe(df_fuzzy, use_container_width=True)

                output_fuzzy = io.BytesIO()
                df_fuzzy.to_excel(output_fuzzy, index=False)
                output_fuzzy.seek(0)

                st.download_button(
                    label="📥 Baixar Excel cruzado por nome",
                    data=output_fuzzy,
                    file_name="pagamentos_cruzados_por_nome.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


# Botão limpar
if st.session_state.df_ret is not None:
    if st.button("🧹 Limpar Tela"):
        st.session_state.df_ret = None
        st.session_state.uploader_key_ret += 1  # força reset do uploader
        st.rerun()

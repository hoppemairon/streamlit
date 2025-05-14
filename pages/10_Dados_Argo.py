import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta
import os
import json
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# --- CREDENCIAIS ARGO ---
ARGO_USER = os.getenv("ARGO_USER")
ARGO_PASS = os.getenv("ARGO_PASS")
ARGO_AUTH_URL = os.getenv("ARGO_AUTH_URL")
ARGO_API_BASE = os.getenv("ARGO_API_BASE")

# --- Funções auxiliares ---
def get_token_argo():
    payload = {"login": ARGO_USER, "password": ARGO_PASS}
    r = requests.post(ARGO_AUTH_URL, json=payload)
    if r.status_code != 200:
        st.error("Erro ao autenticar na API Argo.")
        return None
    return r.json().get('access_token')

def get_transacoes_argo(token, data_inicial, data_final):
    str_data_inicial = data_inicial.strftime("%d%m%Y")
    str_data_final = data_final.strftime("%d%m%Y")
    url = (f"{ARGO_API_BASE}transacoescartoes?"
           f"dataInicial={str_data_inicial}&datafinal={str_data_final}")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        st.error(f"Erro na requisição: {r.status_code}")
        return []
    return r.json()

def to_dataframe_argo(dados):
    if not dados:
        return pd.DataFrame()
    return pd.DataFrame(dados)

def save_json(data, folder_path, date_str):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    file_path = os.path.join(folder_path, f"VendasCartoesArgo - {date_str}.json")
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)
    st.success(f"Arquivo salvo em: {file_path}")

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Consulta de Dados - Argo (TeiaCard)", layout="wide")
st.header("Consulta de Dados - Argo (TeiaCard)")

if 'folder_path' not in st.session_state:
    st.session_state['folder_path'] = ""

st.session_state['folder_path'] = st.text_input(
    "Digite o caminho da pasta para salvar os arquivos JSON (deixe vazio para não salvar):",
    value=st.session_state['folder_path'],
    key="folder_path_input"
)

# 1. Autenticação
token = get_token_argo()
if not token:
    st.stop()

# 2. Seleção de período
periodo = st.date_input(
    "Período (Data inicial e final)",
    value=[date.today(), date.today()],
    format="DD/MM/YYYY"
)

if len(periodo) == 2:
    data_inicial, data_final = periodo
else:
    st.warning("Selecione o período desejado.")
    st.stop()

st.write(f"Período selecionado: {data_inicial.strftime('%d/%m/%Y')} até {data_final.strftime('%d/%m/%Y')}")

# 3. Buscar dados
if st.button("Buscar dados"):
    st.info("Aguarde! As consultas podem demorar alguns segundos para cada dia do período selecionado.")
    total_dias = (data_final - data_inicial).days + 1
    progress_bar = st.progress(0)
    dados_total = []
    data_atual = data_inicial

    for i in range(total_dias):
        data_api = data_atual
        st.write(f"Consultando dados do dia {data_api.strftime('%d/%m/%Y')} ...")
        dados_dia = get_transacoes_argo(token, data_api, data_api)
        if dados_dia:
            for item in dados_dia:
                item['data_consulta'] = data_api.strftime("%d/%m/%Y")
            dados_total.extend(dados_dia)
            if st.session_state['folder_path']:
                save_json(dados_dia, st.session_state['folder_path'], data_api.strftime("%Y%m%d"))
        progress_bar.progress((i + 1) / total_dias)
        data_atual += timedelta(days=1)

    df = to_dataframe_argo(dados_total)
    if not df.empty:
        st.success(f"{len(df)} registros encontrados no período selecionado.")
        st.session_state['df_argo'] = df  # Salva o DataFrame na sessão
    else:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        st.session_state['df_argo'] = pd.DataFrame()

# --- Exibição e resumo (após busca) ---
df_argo = st.session_state.get('df_argo', pd.DataFrame())

if isinstance(df_argo, pd.DataFrame) and not df_argo.empty:
    st.subheader("DataFrame completo:")
    st.dataframe(df_argo)

    # --- Filtro por idempresa (multiselect) ---
    if 'idempresa' in df_argo.columns:
        empresas_unicas = sorted(df_argo['idempresa'].unique())
        empresas_opcoes = [str(e) for e in empresas_unicas]
        empresas_selecionadas = st.multiselect(
            "Filtrar por idempresa:",
            options=empresas_opcoes,
            default=empresas_opcoes  # Seleciona todas por padrão
        )
        if empresas_selecionadas:
            df_filtrado = df_argo[df_argo['idempresa'].astype(str).isin(empresas_selecionadas)]
        else:
            st.warning("Selecione ao menos uma empresa para visualizar os dados.")
            df_filtrado = pd.DataFrame()
    else:
        st.warning("Coluna 'idempresa' não encontrada no DataFrame.")
        df_filtrado = df_argo

    # --- Dois resumos lado a lado ---
    col1, col2 = st.columns(2)

    # Resumo por forma de pagamento
    with col1:
        if not df_filtrado.empty and {'formapagamento', 'valorbruto', 'valorliquido'}.issubset(df_filtrado.columns):
            st.subheader("Resumo por Forma de Pagamento")
            df_resumo_fp = (
                df_filtrado.groupby('formapagamento', as_index=False)[['valorbruto', 'valorliquido']]
                .sum()
                .sort_values(by='valorbruto', ascending=False)
            )
            st.dataframe(df_resumo_fp)
        else:
            st.warning("Colunas necessárias para o resumo por forma de pagamento não encontradas.")

    # Resumo por operadora
    with col2:
        if not df_filtrado.empty and {'operadora', 'valorbruto', 'valorliquido'}.issubset(df_filtrado.columns):
            st.subheader("Resumo por Operadora")
            df_resumo_op = (
                df_filtrado.groupby('operadora', as_index=False)[['valorbruto', 'valorliquido']]
                .sum()
                .sort_values(by='valorbruto', ascending=False)
            )
            st.dataframe(df_resumo_op)
        else:
            st.warning("Colunas necessárias para o resumo por operadora não encontradas.")

    # --- Detalhamento segue igual (por forma de pagamento) ---
    if not df_filtrado.empty and {'formapagamento', 'valorbruto', 'valorliquido'}.issubset(df_filtrado.columns):
        forma_opcao = st.selectbox(
            "Selecione a forma de pagamento para filtrar o detalhamento:",
            options=df_filtrado['formapagamento'].unique()
        )
        df_detalhe = df_filtrado[df_filtrado['formapagamento'] == forma_opcao]
        st.subheader(f"Detalhamento para: {forma_opcao}")

        colunas_disponiveis = list(df_detalhe.columns)
        colunas_pre_selecionadas = [
            'formapagamento', 'datavenda', 'valorbruto', 'valorliquido', 'vendapos'
        ]
        colunas_default = [col for col in colunas_pre_selecionadas if col in colunas_disponiveis]

        colunas_escolhidas = st.multiselect(
            "Escolha as colunas para exibir:",
            options=colunas_disponiveis,
            default=colunas_default if colunas_default else colunas_disponiveis
        )
        st.dataframe(df_detalhe[colunas_escolhidas])
    else:
        st.warning("Colunas necessárias para o detalhamento não encontradas no DataFrame ou nenhum dado filtrado.")
else:
    st.info("Realize uma busca para visualizar os dados.")
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import time
import json
import os

# --- CREDENCIAIS (apenas para testes locais) ---
CLIENT_ID = "2"
CLIENT_SECRET = "KZ00QSA1GPBqBlHsArhVlHLSyHTg6srmoqUCKb8c"
USERNAME = "admin@postosrota.com"
PASSWORD = "p!Rt@25"

# --- Funções auxiliares ---
def get_token():
    url = 'https://api.saferedi.nteia.com/v1/oauth/token'
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD
    }
    r = requests.post(url, json=payload)
    if r.status_code != 200:
        st.error("Erro ao autenticar na API Netunna.")
        return None
    return r.json().get('access_token')

def get_empresas(token):
    url = 'https://api.saferedi.nteia.com/v1/retorno/empresas'
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        st.error("Erro ao buscar empresas.")
        return {}
    empresas = r.json()['data']
    return {f"{e['nome_fantasia']} ({e['empresa_codigo']})": e['empresa_codigo'] for e in empresas}

def get_parcelas(token, tipo, data_api, empresa_codigo):
    url = f'https://api.saferedi.nteia.com/v1/retorno/parcelas?tipo={tipo}&data={data_api}&empresa_codigo={empresa_codigo}'
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        st.error(f"Erro na requisição: {r.status_code}")
        return []
    result = r.json()
    total_paginas = result['pagination']['total_pages']
    dados = []
    for page in range(1, total_paginas + 1):
        pag_url = f"{url}&page={page}"
        pag_r = requests.get(pag_url, headers=headers)
        if pag_r.status_code == 200:
            dados.extend(pag_r.json().get('data', []))
    return dados

def validar_arquivos():
    pasta_arquivos = os.path.join(".", "logic", "ArquivosNetunna")
    arquivos_necessarios = [
        "ListaAdquirentes - TeiaCard.json",
        "ListaBandeiras - TeiaCard.json"
    ]
    arquivos_faltando = []
    for arquivo in arquivos_necessarios:
        caminho = os.path.join(pasta_arquivos, arquivo)
        if not os.path.isfile(caminho):
            arquivos_faltando.append(arquivo)
    if arquivos_faltando:
        st.error(
            "Os seguintes arquivos obrigatórios não foram encontrados na pasta "
            f"`{pasta_arquivos}`:\n- " + "\n- ".join(arquivos_faltando)
        )
        return False
    return True

def to_dataframe(dados):
    if not dados:
        return pd.DataFrame()
    return pd.json_normalize(dados)

# --- Carregar arquivos de adquirentes e bandeiras ---
def carregar_adquirentes_bandeiras():
    pasta_arquivos = os.path.join(".", "logic", "ArquivosNetunna")
    # Bandeiras
    with open(os.path.join(pasta_arquivos, "ListaBandeiras - TeiaCard.json"), encoding="utf-8") as f:
        bandeiras_json = json.load(f)
    bandeiras_df = pd.DataFrame(bandeiras_json["data"]).rename(columns={"id": "bandeira_id", "name": "bandeira_nome"})
    # Adquirentes
    with open(os.path.join(pasta_arquivos, "ListaAdquirentes - TeiaCard.json"), encoding="utf-8") as f:
        adquirentes_json = json.load(f)
    adquirentes_df = pd.DataFrame(adquirentes_json["data"]).rename(columns={"id": "adquirente_id", "name": "adquirente_nome"})
    return adquirentes_df, bandeiras_df

# --- INTERFACE STREAMLIT ---

st.header("Consulta de Dados - Netunna (TeiaCard)")

if not validar_arquivos():
    st.stop()

# 1. Autenticação
token = get_token()
if not token:
    st.stop()

# 2. Seleção de parâmetros
empresas_dict = get_empresas(token)
if not empresas_dict:
    st.stop()

tipo = st.selectbox("Tipo de requisição", ["venda", "ocorrencia", "baixa"])

# Data inicial e final no formato brasileiro
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

empresa_nome = st.selectbox("Unidade (empresa)", list(empresas_dict.keys()))
empresa_codigo = empresas_dict[empresa_nome]

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
        data_str_api = data_api.strftime("%Y%m%d")
        st.write(f"Consultando dados do dia {data_api.strftime('%d/%m/%Y')} ...")
        dados_dia = get_parcelas(token, tipo, data_str_api, empresa_codigo)
        if dados_dia:
            for item in dados_dia:
                item['data_consulta'] = data_api.strftime("%d/%m/%Y")
            dados_total.extend(dados_dia)
        progress_bar.progress((i + 1) / total_dias)
        data_atual += timedelta(days=1)
        time.sleep(10)  # Aguarda 10 segundos entre as requisições

    df = to_dataframe(dados_total)
    if not df.empty:
        st.success(f"{len(df)} registros encontrados no período selecionado.")

        # Carregar adquirentes e bandeiras
        adquirentes_df, bandeiras_df = carregar_adquirentes_bandeiras()

        # Renomear colunas do DataFrame principal para bater com os merges
        colunas_renomear = {}
        if "venda.adquirente" in df.columns:
            colunas_renomear["venda.adquirente"] = "adquirente_id"
        if "venda.bandeira" in df.columns:
            colunas_renomear["venda.bandeira"] = "bandeira_id"
        df = df.rename(columns=colunas_renomear)

        # Fazendo merge com adquirentes e bandeiras
        if 'adquirente_id' in df.columns:
            df = df.merge(adquirentes_df, on="adquirente_id", how="left")
        if 'bandeira_id' in df.columns:
            df = df.merge(bandeiras_df, on="bandeira_id", how="left")

        st.write("DataFrame com nomes de adquirente e bandeira:")
        st.dataframe(df)

        # Salva o DataFrame no session_state para persistência entre interações
        st.session_state['df'] = df

    else:
        st.warning("Nenhum dado encontrado para o período selecionado.")

    # 4. Resumo, filtro e gráfico (usando session_state)
    if 'df' in st.session_state and not st.session_state['df'].empty:
        df = st.session_state['df']
        colunas_necessarias = {'bandeira_nome', 'valor_bruto', 'valor_liquido', 'valor_liquido_original'}
        if colunas_necessarias.issubset(df.columns):
            df_resumo = (
                df.groupby('bandeira_nome', as_index=False)[['valor_bruto', 'valor_liquido', 'valor_liquido_original']]
                .sum()
                .sort_values(by='valor_bruto', ascending=False)
            )

            st.subheader("Resumo por Bandeira")
            st.dataframe(df_resumo)

        if not df_resumo.empty:
            bandeira_opcao = st.selectbox(
                "Selecione a bandeira para filtrar o detalhamento:",
                options=df_resumo['bandeira_nome'].unique()
            )
            df_filtrado = df[df['bandeira_nome'] == bandeira_opcao]
            st.subheader(f"Detalhamento para a bandeira: {bandeira_opcao}")

            # --- Seleção de colunas com pré-seleção ---
            colunas_disponiveis = list(df_filtrado.columns)
            colunas_pre_selecionadas = [
                'bandeira_nome',
                'venda.venda_data',
                'venda.valor_bruto',
                'valor_liquido',
                'valor_liquido_original'
            ]
            # Seleciona apenas as que existem no DataFrame
            colunas_default = [col for col in colunas_pre_selecionadas if col in colunas_disponiveis]

            colunas_escolhidas = st.multiselect(
                "Escolha as colunas para exibir:",
                options=colunas_disponiveis,
                default=colunas_default if colunas_default else colunas_disponiveis
            )
            st.dataframe(df_filtrado[colunas_escolhidas])

    else:
        st.warning("Colunas necessárias para o resumo não encontradas no DataFrame.")
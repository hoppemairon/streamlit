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
    st.write("Status code:", r.status_code)
    st.write("Resposta:", r.text)
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

import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta

# --- CREDENCIAIS ARGO ---
ARGO_USER = "infra.milanezi"
ARGO_PASS = "$HhhY3yDdfqFNRrq"
ARGO_AUTH_URL = "https://toda-one-auth.argoservicos.com/api/v1/auth"
ARGO_API_BASE = "http://rederota.ddns.me:60532/argoapi/"

# --- Funções auxiliares ---
def get_token_argo():
    payload = {"login": ARGO_USER, "password": ARGO_PASS}
    r = requests.post(ARGO_AUTH_URL, json=payload)
    if r.status_code != 200:
        st.error("Erro ao autenticar na API Argo.")
        return None
    return r.json().get('access_token')

def get_transacoes_argo(token, data_inicial, data_final):
    # Datas no formato ddmmaaaa
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

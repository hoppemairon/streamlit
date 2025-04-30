import pandas as pd
import streamlit as st
import os
import json

# Função para carregar empresas ARGO
def carregar_empresas_argo():
    caminho = os.path.join('logic', 'ArquivosArgo', 'EmpesasArgo.json')
    with open(caminho, 'r', encoding='utf-8') as f:
        empresas = json.load(f)
    return pd.DataFrame(empresas)

# Função para carregar empresas Netunna
def carregar_empresas_netunna():
    caminho = os.path.join('logic', 'ArquivosNetunna', 'ListaEmpresas - TeiaCard.json')
    with open(caminho, 'r', encoding='utf-8') as f:
        empresas = json.load(f)
    return pd.DataFrame(empresas['data'])

# Função para mapear empresas pelo CNPJ
def mapear_empresas_por_cnpj(empresas_argo, empresas_netunna):
    """Mapeia empresas ARGO e Netunna pelo CNPJ."""
    if 'cnpj' not in empresas_argo.columns or 'nu_inscricao' not in empresas_netunna.columns:
        st.error("⚠️ Arquivos precisam conter os campos 'cnpj' e 'nu_inscricao'.")
        return pd.DataFrame()

    # Padronizar CNPJ (remover pontos, traços, etc)
    empresas_argo['cnpj'] = empresas_argo['cnpj'].str.replace(r'\D', '', regex=True)
    empresas_netunna['nu_inscricao'] = empresas_netunna['nu_inscricao'].str.replace(r'\D', '', regex=True)

    mapeamento = pd.merge(
        empresas_argo,
        empresas_netunna,
        left_on='cnpj',
        right_on='nu_inscricao',
        suffixes=('_argo', '_netunna')
    )

    # Renomear para facilitar a vida depois
    mapeamento = mapeamento.rename(columns={
        'idempresa': 'empresa_argo_id',
        'nomefantasia': 'empresa_argo_nome',
        'empresa_codigo': 'empresa_netunna_id',
        'nome_fantasia': 'empresa_netunna_nome'
    })

    # Criar uma coluna para facilitar o display no selectbox
    mapeamento['empresa_display'] = mapeamento['empresa_argo_id'].astype(str) + ' :: ' + mapeamento['empresa_argo_nome']

    return mapeamento[['empresa_argo_id', 'empresa_argo_nome', 'empresa_netunna_id', 'empresa_netunna_nome', 'empresa_display']]
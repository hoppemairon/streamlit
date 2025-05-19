import pandas as pd
import os
import json

def carregar_empresas_argo():
    caminho = os.path.join('logic', 'ArquivosArgo', 'EmpesasArgo.json')
    with open(caminho, 'r', encoding='utf-8') as f:
        empresas = json.load(f)
    return pd.DataFrame(empresas)

def carregar_empresas_netunna():
    caminho = os.path.join('logic', 'ArquivosNetunna', 'ListaEmpresas - TeiaCard.json')
    with open(caminho, 'r', encoding='utf-8') as f:
        empresas = json.load(f)
    return pd.DataFrame(empresas['data'])

def mapear_empresas_por_cnpj(empresas_argo, empresas_netunna):
    if 'cnpj' not in empresas_argo.columns or 'nu_inscricao' not in empresas_netunna.columns:
        raise ValueError("Arquivos precisam conter os campos 'cnpj' e 'nu_inscricao'.")

    empresas_argo['cnpj'] = empresas_argo['cnpj'].str.replace(r'\D', '', regex=True)
    empresas_netunna['nu_inscricao'] = empresas_netunna['nu_inscricao'].str.replace(r'\D', '', regex=True)

    mapeamento = pd.merge(
        empresas_argo,
        empresas_netunna,
        left_on='cnpj',
        right_on='nu_inscricao',
        suffixes=('_argo', '_netunna')
    )

    mapeamento = mapeamento.rename(columns={
        'idempresa': 'empresa_argo_id',
        'nomefantasia': 'empresa_argo_nome',
        'empresa_codigo': 'empresa_netunna_id',
        'nome_fantasia': 'empresa_netunna_nome'
    })

    mapeamento['empresa_display'] = mapeamento['empresa_argo_id'].astype(str) + ' :: ' + mapeamento['empresa_argo_nome']

    return mapeamento[['empresa_argo_id', 'empresa_argo_nome', 'empresa_netunna_id', 'empresa_netunna_nome', 'empresa_display']]
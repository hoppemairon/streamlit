import pandas as pd
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

# ----------- Funcoes auxiliares -------------

def padronizar_cnpj(cnpj):
    return re.sub(r'[^0-9]', '', str(cnpj))

# ----------- Funcoes de carregamento -------------

def carregar_argo(file):
    vendas = json.load(file)
    df = pd.DataFrame(vendas)

    df['datavenda'] = pd.to_datetime(df['datavenda'], errors='coerce')
    df['horavenda'] = pd.to_timedelta(df['horavenda'], errors='coerce')
    df['datacompleta'] = df['datavenda'] + df['horavenda']

    df['valorbruto'] = pd.to_numeric(df['valorbruto'], errors='coerce')
    df['nsu'] = df['nsu'].astype(str).str.zfill(9)

    return df[['idempresa', 'datavenda', 'horavenda', 'datacompleta', 'valorbruto', 'nsu', 'operadora', 'formapagamento', 'bandeira', 'vendapos']]

def carregar_netunna(file):
    vendas = json.load(file)

    if isinstance(vendas, list):
        vendas = vendas[0]

    if 'data' in vendas:
        df = pd.json_normalize(vendas['data'])
    else:
        df = pd.json_normalize(vendas)

    colunas = df.columns.tolist()

    campo_data = next((col for col in colunas if 'data' in col.lower()), None)
    campo_valor = next((col for col in colunas if 'valor' in col.lower()), None)
    campo_nsu = next((col for col in colunas if 'nsu' in col.lower()), None)

    if campo_data:
        df[campo_data] = pd.to_datetime(df[campo_data], errors='coerce')
    if campo_valor:
        df[campo_valor] = pd.to_numeric(df[campo_valor], errors='coerce')
    if campo_nsu:
        df[campo_nsu] = df[campo_nsu].astype(str).str.zfill(9)

    return df

def carregar_arquivo_individual(caminho_arquivo, tipo):
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            if tipo == 'argo':
                return carregar_argo(f)
            elif tipo == 'netunna':
                return carregar_netunna(f)
    except Exception:
        return pd.DataFrame()

def carregar_todos_jsons_pasta(pasta_path, tipo='argo'):
    arquivos = [os.path.join(pasta_path, arq) for arq in os.listdir(pasta_path) if arq.endswith('.json')]

    if not arquivos:
        return pd.DataFrame()

    dfs = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        resultados = list(executor.map(lambda arq: carregar_arquivo_individual(arq, tipo), arquivos))

    for df in resultados:
        if not df.empty:
            dfs.append(df)

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return pd.DataFrame()

# ----------- Funcao de comparacao principal (melhorada) -------------

def comparar_vendas(df_argo, df_netunna):
    df_argo = df_argo.rename(columns={
        'datacompleta': 'datahora',
        'valorbruto': 'valor',
        'nsu': 'nsu',
        'operadora': 'operadora_argo',
        'formapagamento': 'formapagamento_argo'
    })

    df_netunna = df_netunna.rename(columns={
        'venda.venda_data': 'datahora',
        'venda.valor_bruto': 'valor',
        'venda.nsu': 'nsu'
    })

    df_argo['nsu'] = df_argo['nsu'].astype(str)
    df_netunna['nsu'] = df_netunna['nsu'].astype(str)

    df_argo['datahora'] = pd.to_datetime(df_argo['datahora'], errors='coerce')
    df_netunna['datahora'] = pd.to_datetime(df_netunna['datahora'], errors='coerce')

    # Batimento por NSU + Valor
    df_argo['chave_nsu_valor'] = df_argo['nsu'] + "_" + df_argo['valor'].astype(str)
    df_netunna['chave_nsu_valor'] = df_netunna['nsu'] + "_" + df_netunna['valor'].astype(str)

    casados_nsu_valor = pd.merge(
        df_argo,
        df_netunna,
        on='chave_nsu_valor',
        how='inner',
        suffixes=('_argo', '_netunna')
    )
    casados_nsu_valor['status'] = '✅ Batido'

    # Separar não casados para fallback
    nsu_valor_casados_argo = casados_nsu_valor['nsu_argo'].tolist()
    nsu_valor_casados_netunna = casados_nsu_valor['nsu_netunna'].tolist()

    df_argo_restante = df_argo[~df_argo['nsu'].isin(nsu_valor_casados_argo)]
    df_netunna_restante = df_netunna[~df_netunna['nsu'].isin(nsu_valor_casados_netunna)]

    # Batimento por Data (sem hora) + Valor
    df_argo_restante['data_dia'] = df_argo_restante['datahora'].dt.date
    df_netunna_restante['data_dia'] = df_netunna_restante['datahora'].dt.date

    df_argo_restante['chave_data_valor'] = df_argo_restante['data_dia'].astype(str) + "_" + df_argo_restante['valor'].astype(str)
    df_netunna_restante['chave_data_valor'] = df_netunna_restante['data_dia'].astype(str) + "_" + df_netunna_restante['valor'].astype(str)

    casados_data_valor = pd.merge(
        df_argo_restante,
        df_netunna_restante,
        on='chave_data_valor',
        how='inner',
        suffixes=('_argo', '_netunna')
    )
    casados_data_valor['status'] = '⚠️ Pareado Data+Valor'

    # Só no ARGO
    nsus_ja_casados_argo = pd.concat([
        casados_nsu_valor['nsu_argo'], casados_data_valor['nsu_argo']
    ]).unique()
    df_argo_sobra = df_argo[~df_argo['nsu'].isin(nsus_ja_casados_argo)].copy()
    df_argo_sobra['nsu_netunna'] = None
    df_argo_sobra['valor_netunna'] = None
    df_argo_sobra['valor_argo'] = df_argo_sobra['valor']
    df_argo_sobra['status'] = '⚠️ Só no ARGO'

    # Só na Netunna
    nsus_ja_casados_netunna = pd.concat([
        casados_nsu_valor['nsu_netunna'], casados_data_valor['nsu_netunna']
    ]).unique()
    df_netunna_sobra = df_netunna[~df_netunna['nsu'].isin(nsus_ja_casados_netunna)].copy()
    df_netunna_sobra['nsu_argo'] = None
    df_netunna_sobra['valor_argo'] = None
    df_netunna_sobra['valor_netunna'] = df_netunna_sobra['valor']
    df_netunna_sobra['status'] = '⚠️ Só na Netunna'

    # Garantir campos de valor para casados
    casados_nsu_valor['valor_argo'] = casados_nsu_valor['valor_argo']
    casados_nsu_valor['valor_netunna'] = casados_nsu_valor['valor_netunna']

    casados_data_valor['valor_argo'] = casados_data_valor['valor_argo']
    casados_data_valor['valor_netunna'] = casados_data_valor['valor_netunna']

    # Concatenar tudo
    resultado = pd.concat([
        casados_nsu_valor[['datahora_argo', 'nsu_argo', 'valor_argo', 'nsu_netunna', 'valor_netunna', 'status']],
        casados_data_valor[['datahora_argo', 'nsu_argo', 'valor_argo', 'nsu_netunna', 'valor_netunna', 'status']],
        df_argo_sobra[['datahora', 'nsu', 'valor_argo', 'nsu_netunna', 'valor_netunna', 'status']].rename(columns={
            'datahora': 'datahora_argo', 'nsu': 'nsu_argo'
        }),
        df_netunna_sobra[['datahora', 'nsu_argo', 'valor_argo', 'nsu', 'valor_netunna', 'status']].rename(columns={
            'datahora': 'datahora_netunna', 'nsu': 'nsu_netunna'
        })
    ], ignore_index=True)

    resultado['datahora'] = resultado.get('datahora_argo').combine_first(resultado.get('datahora_netunna'))
    resultado = resultado[['datahora', 'nsu_argo', 'valor_argo', 'nsu_netunna', 'valor_netunna', 'status']]

    return resultado


# ----------- Funcoes de relacionamento manual -------------

def gerar_sugestoes_relacionamentos_v2(df_argo, df_netunna, comparativo, id_empresa, datas_filtradas):
    df_argo = df_argo.copy()
    df_netunna = df_netunna.copy()

    df_argo['data_somente'] = df_argo['datavenda'].dt.date
    df_netunna['data_somente'] = pd.to_datetime(df_netunna['venda.venda_data']).dt.date

    df_argo = df_argo[df_argo['data_somente'].isin(datas_filtradas)]
    df_netunna = df_netunna[df_netunna['data_somente'].isin(datas_filtradas)]

    nsu_somente_argo = comparativo[comparativo['status'] == '⚠️ Só no ARGO']['nsu_argo'].dropna().unique()
    nsu_somente_netunna = comparativo[comparativo['status'] == '⚠️ Só na Netunna']['nsu_netunna'].dropna().unique()

    df_argo = df_argo[df_argo['nsu'].isin(nsu_somente_argo)]
    df_netunna = df_netunna[df_netunna['venda.nsu'].isin(nsu_somente_netunna)]

    sugestoes = []
    df_netunna_indexado = df_netunna.set_index(['venda.nsu', 'data_somente'])

    for idx, venda_argo in df_argo.iterrows():
        nsu_argo = venda_argo['nsu']
        data_argo = venda_argo['data_somente']
        valor_argo = venda_argo['valorbruto']
        idempresa_argo = venda_argo['idempresa']

        try:
            venda_netunna = df_netunna_indexado.loc[(nsu_argo, data_argo)]
            if isinstance(venda_netunna, pd.Series):
                valor_netunna = venda_netunna['venda.valor_bruto']
                idempresa_netunna = venda_netunna['venda.empresa_codigo']
                if abs(valor_argo - valor_netunna) <= 0.01 and idempresa_argo == idempresa_netunna:
                    sugestoes.append({
                        'idempresa': id_empresa,
                        'data_argo': str(data_argo),
                        'nsu_argo': nsu_argo,
                        'valor_argo': valor_argo,
                        'forma_pagamento_argo': venda_argo['formapagamento'],
                        'data_netunna': str(data_argo),
                        'nsu_netunna': venda_netunna['venda.nsu'],
                        'valor_netunna': valor_netunna,
                        'bandeira_netunna': venda_netunna['venda.bandeira'],
                        'metodo_sugestao': 'NSU',
                        'validado': False,
                        'observacao': ''
                    })
                    continue
        except Exception:
            pass

        candidatos = df_netunna[(df_netunna['data_somente'] == data_argo) & (abs(df_netunna['venda.valor_bruto'] - valor_argo) <= 0.01)]
        if not candidatos.empty:
            venda_netunna = candidatos.iloc[0]
            idempresa_netunna = venda_netunna['venda.empresa_codigo']
            if idempresa_argo == idempresa_netunna:
                sugestoes.append({
                    'idempresa': id_empresa,
                    'data_argo': str(data_argo),
                    'nsu_argo': nsu_argo,
                    'valor_argo': valor_argo,
                    'forma_pagamento_argo': venda_argo['formapagamento'],
                    'data_netunna': str(data_argo),
                    'nsu_netunna': venda_netunna['venda.nsu'],
                    'valor_netunna': venda_netunna['venda.valor_bruto'],
                    'bandeira_netunna': venda_netunna['venda.bandeira'],
                    'metodo_sugestao': 'Data+Valor',
                    'validado': False,
                    'observacao': ''
                })

    return pd.DataFrame(sugestoes)

# ----------- Funcao para salvar validacoes -------------

def salvar_validacoes_json(df_validacoes, id_empresa, datas_filtradas):
    pasta = 'ValidacaoArgoNetunna'
    if not os.path.exists(pasta):
        os.makedirs(pasta)

    nome_arquivo = f"validacao_argo_netunna_{id_empresa}_{min(datas_filtradas)}.json"
    caminho_completo = os.path.join(pasta, nome_arquivo)

    df_validacoes.to_json(caminho_completo, orient='records', indent=4)

def resumo_por_status_valor(comparativo: pd.DataFrame) -> pd.DataFrame:
    comparativo = comparativo.copy()

    # Preencher valor_base com valor_argo ou, se nulo, com valor_netunna
    comparativo['valor_base'] = comparativo['valor_argo']
    comparativo.loc[comparativo['valor_base'].isna(), 'valor_base'] = comparativo['valor_netunna']

    resumo = comparativo.groupby('status').agg(
        Quantidade=('status', 'count'),
        Valor_Bruto=('valor_base', 'sum')
    ).reset_index()

    return resumo

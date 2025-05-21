import os
import json
import pandas as pd
import numpy as np
import glob

def carregar_todos_jsons_pasta(pasta, tipo='argo'):
    """
    Carrega todos os arquivos JSON de uma pasta em um DataFrame.
    Args:
        pasta (str): Caminho da pasta contendo os arquivos JSON
        tipo (str): Tipo de arquivo ('argo' ou 'netunna')
    Returns:
        DataFrame: DataFrame com todos os dados dos arquivos JSON
    """
    if not os.path.exists(pasta):
        raise FileNotFoundError(f"Pasta não encontrada: {pasta}")

    arquivos = glob.glob(os.path.join(pasta, "*.json"))

    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo JSON encontrado na pasta: {pasta}")

    dfs = []

    for arquivo in arquivos:
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)

            if tipo == 'argo':
                df = pd.DataFrame(dados)
                if 'datavenda' in df.columns:
                    df['datavenda'] = pd.to_datetime(df['datavenda'], errors='coerce')
                dfs.append(df)
            elif tipo == 'netunna':
                # O JSON do Netunna pode ser uma lista de blocos ou um dicionário com 'data'
                if isinstance(dados, list):
                    for bloco in dados:
                        if 'data' in bloco:
                            df = pd.json_normalize(bloco['data'])
                            dfs.append(df)
                elif 'data' in dados:
                    df = pd.DataFrame(dados['data'])
                    dfs.append(df)
        except Exception as e:
            print(f"Erro ao processar arquivo {arquivo}: {str(e)}")
            continue

    if not dfs:
        raise ValueError(f"Nenhum dado válido encontrado nos arquivos da pasta: {pasta}")

    df_final = pd.concat(dfs, ignore_index=True)
    return df_final

def comparar_vendas(df_argo, df_netunna):
    """
    Compara vendas entre ARGO e Netunna, identificando correspondências por NSU e, se não houver, por data e valor.
    Args:
        df_argo (DataFrame): DataFrame com vendas do ARGO
        df_netunna (DataFrame): DataFrame com vendas do Netunna
    Returns:
        DataFrame: DataFrame com o resultado da comparação
    """
    import numpy as np
    import pandas as pd

    # Verificar se os DataFrames estão vazios
    if df_argo.empty and df_netunna.empty:
        return pd.DataFrame(columns=[
            'datahora', 'nsu_argo', 'valor_argo', 'formapagamento_argo',
            'nsu_netunna', 'valor_netunna', 'bandeira_netunna', 'operadora_netunna', 'status'
        ])

    # Criar cópias para não modificar os originais
    df_argo = df_argo.copy() if not df_argo.empty else pd.DataFrame()
    df_netunna = df_netunna.copy() if not df_netunna.empty else pd.DataFrame()

    # Preparar DataFrame ARGO
    if not df_argo.empty:
        df_argo_prep = df_argo[['nsu', 'datavenda', 'valorbruto', 'formapagamento']].copy()
        df_argo_prep.columns = ['nsu_argo', 'datahora', 'valor_argo', 'formapagamento_argo']
        df_argo_prep['nsu_argo'] = df_argo_prep['nsu_argo'].astype(str)
        df_argo_prep['status'] = '⚠️ Só no ARGO'
    else:
        df_argo_prep = pd.DataFrame(columns=['nsu_argo', 'datahora', 'valor_argo', 'formapagamento_argo', 'status'])

    # Preparar DataFrame Netunna
    if not df_netunna.empty:
        # Garante que as colunas existem, criando-as vazias se necessário
        for col in ['venda.nsu', 'venda.venda_data', 'venda.valor_bruto', 'venda.bandeira']:
            if col not in df_netunna.columns:
                df_netunna[col] = np.nan
        # 'venda.operadora' não existe no Netunna, mas criamos para compatibilidade
        if 'venda.operadora' not in df_netunna.columns:
            df_netunna['venda.operadora'] = np.nan

        df_netunna_prep = df_netunna[['venda.nsu', 'venda.venda_data', 'venda.valor_bruto', 'venda.bandeira', 'venda.operadora', 'venda.adquirente.id']].copy()
        df_netunna_prep.columns = ['nsu_netunna', 'datahora', 'valor_netunna', 'bandeira_netunna', 'operadora_netunna', 'adquirente_netunna']
        df_netunna_prep['nsu_netunna'] = df_netunna_prep['nsu_netunna'].astype(str)
        df_netunna_prep['status'] = '⚠️ Só na Netunna'
    else:
        df_netunna_prep[['datahora', 'nsu_netunna', 'valor_netunna', 'bandeira_netunna', 'operadora_netunna', 'adquirente_netunna', 'status']]

    # Padronizar NSUs para o mesmo tamanho (com zeros à esquerda)
    max_nsu_len = max(
        df_argo_prep['nsu_argo'].str.len().max() if not df_argo_prep.empty else 0,
        df_netunna_prep['nsu_netunna'].str.len().max() if not df_netunna_prep.empty else 0
    )
    df_argo_prep['nsu_argo'] = df_argo_prep['nsu_argo'].str.zfill(max_nsu_len)
    df_netunna_prep['nsu_netunna'] = df_netunna_prep['nsu_netunna'].str.zfill(max_nsu_len)

    # Encontrar correspondências por NSU (batimento exato)
    df_batido = pd.merge(
        df_argo_prep, 
        df_netunna_prep,
        left_on='nsu_argo',
        right_on='nsu_netunna',
        how='inner',
        suffixes=('_argo', '_netunna')
    )

    # Usar a data do ARGO como referência
    if 'datahora_argo' in df_batido.columns and 'datahora_netunna' in df_batido.columns:
        df_batido['datahora'] = df_batido['datahora_argo']
        df_batido = df_batido.drop(['datahora_argo', 'datahora_netunna'], axis=1)

    # Marcar como batido
    if not df_batido.empty:
        df_batido['status'] = '✅ Batido'

    # Remover NSUs já batidos dos DataFrames originais
    if not df_batido.empty:
        nsus_batidos = df_batido['nsu_argo'].unique()
        df_argo_prep = df_argo_prep[~df_argo_prep['nsu_argo'].isin(nsus_batidos)]
        df_netunna_prep = df_netunna_prep[~df_netunna_prep['nsu_netunna'].isin(nsus_batidos)]

    # -------------------------------------------
    # Batimento alternativo: por data e valor
    # -------------------------------------------
    # Convertendo datahora para datetime para comparação precisa
    df_argo_prep['datahora'] = pd.to_datetime(df_argo_prep['datahora'], errors='coerce').dt.date
    df_netunna_prep['datahora'] = pd.to_datetime(df_netunna_prep['datahora'], errors='coerce').dt.date

    possiveis_matches = []
    idxs_argo_usados = set()
    idxs_netunna_usados = set()

    for idx_argo, row_argo in df_argo_prep.iterrows():
        valor_argo = row_argo['valor_argo']
        data_argo = row_argo['datahora']
        # Procura por valor e data (tolerância de centavos)
        candidatos = df_netunna_prep[
            (np.abs(df_netunna_prep['valor_netunna'] - valor_argo) <= 0.01) &
            (df_netunna_prep['datahora'] == data_argo)
        ]
        if not candidatos.empty:
            candidato = candidatos.iloc[0]
            match = {
                'datahora': data_argo,
                'nsu_argo': row_argo['nsu_argo'],
                'valor_argo': valor_argo,
                'formapagamento_argo': row_argo.get('formapagamento_argo', np.nan),
                'nsu_netunna': candidato['nsu_netunna'],
                'valor_netunna': candidato['valor_netunna'],
                'bandeira_netunna': candidato.get('bandeira_netunna', np.nan),
                'adquirente_netunna': candidato.get('adquirente_netunna', np.nan),
                'operadora_netunna': candidato.get('operadora_netunna', np.nan),
                'status': '⚠️ Possível Match Data+Valor'
            }
            possiveis_matches.append(match)
            idxs_argo_usados.add(idx_argo)
            idxs_netunna_usados.add(candidato.name)

    # Remove os que já foram batidos por data+valor
    df_argo_prep = df_argo_prep.drop(list(idxs_argo_usados))
    df_netunna_prep = df_netunna_prep.drop(list(idxs_netunna_usados))

    # -------------------------------------------
    # Garante que todos os DataFrames tenham as colunas finais
    colunas_finais = ['datahora', 'nsu_argo', 'valor_argo', 'formapagamento_argo', 
                      'nsu_netunna', 'valor_netunna', 'bandeira_netunna', 'operadora_netunna', 'status', 'adquirente_netunna']
    for df in [df_batido, df_argo_prep, df_netunna_prep]:
        for col in colunas_finais:
            if col not in df.columns:
                df[col] = pd.Series(dtype='object')

    # -------------------------------------------
    # Unir todos os resultados
    # -------------------------------------------
    resultado = pd.concat([
        df_batido[['datahora', 'nsu_argo', 'valor_argo', 'formapagamento_argo', 
           'nsu_netunna', 'valor_netunna', 'bandeira_netunna', 'operadora_netunna', 'adquirente_netunna', 'status']],
        pd.DataFrame(possiveis_matches),
        df_argo_prep[['datahora', 'nsu_argo', 'valor_argo', 'formapagamento_argo', 'status']],
        df_netunna_prep[['datahora', 'nsu_netunna', 'valor_netunna', 'bandeira_netunna', 'operadora_netunna', 'adquirente_netunna', 'status']]
    ], ignore_index=True)

    # Garantir colunas (caso ainda falte)
    for col in ['nsu_argo', 'valor_argo', 'formapagamento_argo', 'nsu_netunna', 'valor_netunna', 'bandeira_netunna', 'operadora_netunna']:
        if col not in resultado.columns:
            resultado[col] = np.nan

    # Ordenar por data
    resultado['datahora'] = pd.to_datetime(resultado['datahora'], errors='coerce')
    resultado = resultado.sort_values('datahora').reset_index(drop=True)

    return resultado

def gerar_sugestoes_relacionamentos_v2(df_argo, df_netunna, comparativo, id_empresa, datas_filtradas):
    """
    Gera sugestões de relacionamento entre vendas ARGO e Netunna para casos não batidos.
    """
    df_argo = df_argo.copy()
    df_netunna = df_netunna.copy()

    df_argo['data_somente'] = pd.to_datetime(df_argo['datavenda'], errors='coerce').dt.date
    df_netunna['data_somente'] = pd.to_datetime(df_netunna['venda.venda_data'], errors='coerce').dt.date

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

def resumo_por_status_valor(comparativo: pd.DataFrame) -> pd.DataFrame:
    """
    Gera um resumo por status e valor bruto.
    """
    comparativo = comparativo.copy()
    comparativo['valor_base'] = comparativo['valor_argo']
    comparativo.loc[comparativo['valor_base'].isna(), 'valor_base'] = comparativo['valor_netunna']

    resumo = comparativo.groupby('status').agg(
        Quantidade=('status', 'count'),
        Valor_Bruto=('valor_base', 'sum')
    ).reset_index()

    return resumo   

def gerar_sugestoes_relacionamentos_v2(df_argo, df_netunna, comparativo, id_empresa, datas_filtradas):
    """
    Gera sugestões de relacionamento entre vendas ARGO e Netunna para casos não batidos.
    """
    df_argo = df_argo.copy()
    df_netunna = df_netunna.copy()

    df_argo['data_somente'] = pd.to_datetime(df_argo['datavenda'], errors='coerce').dt.date
    df_netunna['data_somente'] = pd.to_datetime(df_netunna['venda.venda_data'], errors='coerce').dt.date

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

def resumo_por_status_valor(comparativo: pd.DataFrame) -> pd.DataFrame:
    """
    Gera um resumo por status e valor bruto.
    """
    comparativo = comparativo.copy()
    comparativo['valor_base'] = comparativo['valor_argo']
    comparativo.loc[comparativo['valor_base'].isna(), 'valor_base'] = comparativo['valor_netunna']

    resumo = comparativo.groupby('status').agg(
        Quantidade=('status', 'count'),
        Valor_Bruto=('valor_base', 'sum')
    ).reset_index()

    return resumo   

def carregar_arquivos_upload(arquivos, tipo):
    import json
    import pandas as pd
    dataframes = []
    if arquivos:
        for file in arquivos:
            dados = json.load(file)
            # Para ambos os tipos, normalizar com sep='.'
            if isinstance(dados, list):
                df = pd.json_normalize(dados, sep='.')
            else:
                df = pd.json_normalize([dados], sep='.')
            dataframes.append(df)
    return pd.concat(dataframes, ignore_index=True) if dataframes else pd.DataFrame()
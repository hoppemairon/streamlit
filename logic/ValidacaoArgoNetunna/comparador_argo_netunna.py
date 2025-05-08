import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
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
    try:
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
                    # Processar arquivo ARGO
                    df = pd.DataFrame(dados)
                    # Converter campos de data
                    if 'datavenda' in df.columns:
                        df['datavenda'] = pd.to_datetime(df['datavenda'], errors='coerce')
                    dfs.append(df)
                    
                elif tipo == 'netunna':
                    # Processar arquivo Netunna
                    if 'data' in dados:
                        df = pd.DataFrame(dados['data'])
                        dfs.append(df)
                    else:
                        df = pd.DataFrame(dados)
                        dfs.append(df)
            except Exception as e:
                print(f"Erro ao processar arquivo {arquivo}: {str(e)}")
                continue
        
        if not dfs:
            raise ValueError(f"Nenhum dado válido encontrado nos arquivos da pasta: {pasta}")
            
        df_final = pd.concat(dfs, ignore_index=True)
        return df_final
        
    except Exception as e:
        raise Exception(f"Erro ao carregar arquivos JSON: {str(e)}")

def comparar_vendas(df_argo, df_netunna):
    """
    Compara vendas entre ARGO e Netunna, identificando correspondências e divergências.
    
    Args:
        df_argo (DataFrame): DataFrame com vendas do ARGO
        df_netunna (DataFrame): DataFrame com vendas do Netunna
        
    Returns:
        DataFrame: DataFrame com o resultado da comparação
    """
    try:
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
            df_netunna_prep = df_netunna[['venda.nsu', 'venda.venda_data', 'venda.valor_bruto', 'venda.bandeira', 'venda.operadora']].copy()
            df_netunna_prep.columns = ['nsu_netunna', 'datahora', 'valor_netunna', 'bandeira_netunna', 'operadora_netunna']
            df_netunna_prep['nsu_netunna'] = df_netunna_prep['nsu_netunna'].astype(str)
            df_netunna_prep['status'] = '⚠️ Só na Netunna'
        else:
            df_netunna_prep = pd.DataFrame(columns=['nsu_netunna', 'datahora', 'valor_netunna', 'bandeira_netunna', 'operadora_netunna', 'status'])
        
        # Encontrar correspondências por NSU
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
        df_batido['status'] = '✅ Batido'
        
        # Remover NSUs já batidos dos DataFrames originais
        if not df_batido.empty:
            nsus_batidos = df_batido['nsu_argo'].unique()
            df_argo_prep = df_argo_prep[~df_argo_prep['nsu_argo'].isin(nsus_batidos)]

def carregar_todos_jsons_pasta(pasta, tipo='argo'):
    """
    Carrega todos os arquivos JSON de uma pasta em um DataFrame.
    
    Args:
        pasta (str): Caminho da pasta contendo os arquivos JSON
        tipo (str): Tipo de arquivo ('argo' ou 'netunna')
        
    Returns:
        DataFrame: DataFrame com todos os dados dos arquivos JSON
    """
    try:
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
                    # Processar arquivo ARGO
                    df = pd.DataFrame(dados)
                    # Converter campos de data
                    if 'datavenda' in df.columns:
                        df['datavenda'] = pd.to_datetime(df['datavenda'], errors='coerce')
                    dfs.append(df)
                    
                elif tipo == 'netunna':
                    # Processar arquivo Netunna
                    if 'data' in dados:
                        df = pd.DataFrame(dados['data'])
                        dfs.append(df)
                    else:
                        df = pd.DataFrame(dados)
                        dfs.append(df)
            except Exception as e:
                print(f"Erro ao processar arquivo {arquivo}: {str(e)}")
                continue
        
        if not dfs:
            raise ValueError(f"Nenhum dado válido encontrado nos arquivos da pasta: {pasta}")
            
        df_final = pd.concat(dfs, ignore_index=True)
        return df_final
        
    except Exception as e:
        raise Exception(f"Erro ao carregar arquivos JSON: {str(e)}")

def comparar_vendas(df_argo, df_netunna):
    """
    Compara vendas entre ARGO e Netunna, identificando correspondências e divergências.
    
    Args:
        df_argo (DataFrame): DataFrame com vendas do ARGO
        df_netunna (DataFrame): DataFrame com vendas do Netunna
        
    Returns:
        DataFrame: DataFrame com o resultado da comparação
    """
    try:
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
            df_netunna_prep = df_netunna[['venda.nsu', 'venda.venda_data', 'venda.valor_bruto', 'venda.bandeira', 'venda.operadora']].copy()
            df_netunna_prep.columns = ['nsu_netunna', 'datahora', 'valor_netunna', 'bandeira_netunna', 'operadora_netunna']
            df_netunna_prep['nsu_netunna'] = df_netunna_prep['nsu_netunna'].astype(str)
            df_netunna_prep['status'] = '⚠️ Só na Netunna'
        else:
            df_netunna_prep = pd.DataFrame(columns=['nsu_netunna', 'datahora', 'valor_netunna', 'bandeira_netunna', 'operadora_netunna', 'status'])
        
        # Encontrar correspondências por NSU
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
        df_batido['status'] = '✅ Batido'
        
        # Remover NSUs já batidos dos DataFrames originais
        if not df_batido.empty:
            nsus_batidos = df_batido['nsu_argo'].unique()
            df_argo_prep = df_argo_prep[~df_argo_prep['nsu_argo'].isin(nsus_batidos)]
            df_netunna_prep = df_netunna_prep[~df_netunna_prep['nsu_netunna'].isin(nsus_
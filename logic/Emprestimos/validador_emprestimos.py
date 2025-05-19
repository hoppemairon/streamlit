import re
import pandas as pd
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detectar_pagamentos_emprestimo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recebe um DataFrame de transações e retorna aquelas que parecem ser pagamentos de empréstimos.
    Tenta extrair número de contrato com base no campo de descrição da transação.
    
    Args:
        df (pd.DataFrame): DataFrame com transações bancárias
        
    Returns:
        pd.DataFrame: DataFrame filtrado contendo apenas transações de empréstimos
        
    Raises:
        ValueError: Se nenhuma coluna de descrição for encontrada no DataFrame
    """
    logger.info("Iniciando detecção de pagamentos de empréstimos")
    
    # Verificar se o DataFrame está vazio
    if df.empty:
        logger.warning("DataFrame vazio recebido")
        return pd.DataFrame()
    
    # Lista de padrões que indicam pagamentos de empréstimos
    padroes_emprestimos = [
        "EMPRESTIMO",
        "CDC",
        "CONS. PESSOAL",
        "PAGTO CONTRATO",
        "CONTRATO",
        "CREDITO PESSOAL",
        "PAGAMENTO CONSIG.",
        "PAGAMENTO EMPRESTIMO",
        "FINANCIAMENTO",
        "PARCELA",
        "PRESTACAO",
        "CRED PESSOAL",
        "CRED.PESSOAL",
    ]
    
    # Padrões específicos por banco
    padroes_por_banco = {
        "BRADESCO": ["PAGTO FINANCIAMENTO", "PARCELA EMPREST", "PAGTO EMPREST"],
        "ITAU": ["PARCELA EMPRESTIMO", "PAGTO EMPRESTIMO"],
        "SANTANDER": ["LIQUIDACAO EMPRESTIMO", "PAGTO CRED PESSOAL"],
        "BANCO DO BRASIL": ["PARCELA BB CRED", "BB CREDITO", "PARCELA FINANC"],
        "CAIXA": ["PAGTO CRED CAIXA", "PRESTACAO HABITAC", "FINANC HABITAC"]
    }
    
    # Função para identificar se uma descrição contém padrões de empréstimo
    def identificar_categoria(texto: str) -> bool:
        if not isinstance(texto, str):
            return False
            
        texto = texto.upper()
        
        # Verificar padrões gerais
        if any(p in texto for p in padroes_emprestimos):
            return True
            
        # Verificar padrões específicos por banco
        for banco, padroes_banco in padroes_por_banco.items():
            if banco in texto or any(p in texto for p in padroes_banco):
                return True
                
        return False
    
    # Função para extrair número de contrato da descrição
    def extrair_contrato(texto: str) -> str:
        if not isinstance(texto, str):
            return ""
            
        # Padrões de extração de contrato
        padroes = [
            r"\b\d{6,}\b",  # Sequência de 6+ dígitos
            r"CONTRATO[:\s]+(\d+)",  # "CONTRATO: 123456"
            r"CONTR[:\s]+(\d+)",  # "CONTR: 123456"
            r"EMPRESTIMO[:\s]+(\d+)"  # "EMPRESTIMO: 123456"
        ]
        
        for padrao in padroes:
            matches = re.findall(padrao, texto.upper())
            if matches:
                return matches[0]
                
        return "SEM_CONTRATO"
    
    # Identificar a coluna de descrição disponível
    colunas_possiveis = ["Descrição", "Histórico", "Memo", "Name", "MEMO", "DESC", "DESCRICAO"]
    coluna_uso = next((c for c in colunas_possiveis if c in df.columns), None)
    
    if not coluna_uso:
        logger.error(f"Nenhuma coluna de descrição encontrada. Esperado uma das: {colunas_possiveis}")
        raise ValueError(f"Nenhuma coluna de descrição encontrada. Esperado uma das: {colunas_possiveis}")
    
    logger.info(f"Usando coluna '{coluna_uso}' para análise de descrições")
    
    # Converter a coluna para string
    df[coluna_uso] = df[coluna_uso].astype(str)
    
    # Filtrar transações que parecem ser pagamentos de empréstimos
    df_filtrado = df[df[coluna_uso].apply(identificar_categoria)].copy()
    
    # Se não encontrou nada, tentar uma abordagem mais flexível
    if df_filtrado.empty:
        logger.warning("Nenhum pagamento encontrado com padrões estritos. Tentando abordagem flexível.")
        
        # Padrões mais flexíveis
        padroes_flexiveis = ["PARCELA", "FINANC", "CRED", "PREST"]
        
        def identificar_flexivel(texto: str) -> bool:
            if not isinstance(texto, str):
                return False
            texto = texto.upper()
            return any(p in texto for p in padroes_flexiveis)
        
        df_filtrado = df[df[coluna_uso].apply(identificar_flexivel)].copy()
    
    # Extrair números de contrato
    if not df_filtrado.empty:
        df_filtrado["Contrato"] = df_filtrado[coluna_uso].apply(extrair_contrato)
        
        # Filtrar apenas débitos (pagamentos)
        if "Tipo" in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["Tipo"] == "Débito"]
        
        # Ordenar por data
        if "Data" in df_filtrado.columns:
            df_filtrado = df_filtrado.sort_values("Data")
        
        logger.info(f"Detectados {len(df_filtrado)} possíveis pagamentos de empréstimos")
    else:
        logger.warning("Nenhum pagamento de empréstimo detectado")
    
    return df_filtrado
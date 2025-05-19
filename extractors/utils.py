import re
from datetime import datetime

def parse_valor(valor_str: str) -> float:
    """
    Converte valor no formato brasileiro para float.
    Ex: '1.234,56-' → -1234.56
    """
    valor_str = valor_str.replace(".", "").replace(",", ".")
    if valor_str.endswith("-"):
        return -float(valor_str[:-1])
    return float(valor_str)

def inferir_mes_ano_do_nome(arquivo_nome: str) -> tuple:
    """
    Tenta extrair mês e ano do nome do arquivo com padrão 01-2025.
    """
    match = re.search(r"(\d{2})-(\d{4})", arquivo_nome)
    if match:
        mes, ano = match.groups()
        return int(mes), int(ano)
    return 1, 2025  # fallback padrão

def construir_data_completa(dia_str: str, nome_arquivo: str) -> str:
    """
    Monta uma data completa (DD/MM/YYYY) a partir do dia + nome do arquivo.
    """
    dia = int(dia_str)
    mes, ano = inferir_mes_ano_do_nome(nome_arquivo)
    try:
        return datetime(ano, mes, dia).strftime("%d/%m/%Y")
    except ValueError:
        return ""

def normalizar_descricao(desc: str) -> str:
    """
    Remove espaços duplicados, converte para minúsculas e remove espaços laterais.
    """
    return re.sub(r"\s+", " ", str(desc).strip().lower())
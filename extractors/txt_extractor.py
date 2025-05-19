import re
from .utils import construir_data_completa, parse_valor

def extrair_lancamentos_txt(file, nome_arquivo):
    texto = file.read().decode("utf-8", errors="ignore")
    linhas = texto.splitlines()
    return processar_linhas(linhas, nome_arquivo)

def processar_linhas(linhas, nome_arquivo):
    dados = []
    movimento_ativo = False
    for linha in linhas:
        if "movimentos" in linha.lower() and "conta" in linha.lower():
            movimento_ativo = True
        elif movimento_ativo:
            match = re.match(r"^\s{0,2}(\d{2})\s{2,}(.+?)\s{2,}(\d+)\s+([\d.,-]+)$", linha.strip())
            if match:
                dia, descricao, documento, valor = match.groups()
                data = construir_data_completa(dia, nome_arquivo)
                valor_float = parse_valor(valor)
                dados.append({
                    "Data": data,
                    "Descrição": descricao.strip(),
                    "Documento": documento,
                    "Valor (R$)": valor_float
                })
    return dados
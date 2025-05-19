import pdfplumber
import re
from .utils import parse_valor, construir_data_completa

def extrair_lancamentos_pdf(file, nome_arquivo):
    texto_completo = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            texto = page.extract_text()
            if texto:
                texto_completo += texto + "\n"

    resumo = extrair_resumo(texto_completo, nome_arquivo)
    transacoes = extrair_transacoes(texto_completo, nome_arquivo)

    return {
        "resumo": resumo,
        "transacoes": transacoes
    }

def extrair_resumo(texto, nome_arquivo):
    dados = {
        "Arquivo": nome_arquivo,
        "Agencia": "",
        "Conta": "",
        "Cliente": "",
        "Identificação": "",
        "Saldo Disponível": None,
        "Saldo Livre": None,
        "Limite Conta": None,
        "Limite Disponível": None
    }

    encontrou_valor = False

    for linha in texto.splitlines():
        linha_upper = linha.upper()

        if "AGENCIA" in linha_upper:
            dados["Agencia"] = linha.split(":")[-1].strip()
        if "CONTA" in linha_upper and "SALDO" not in linha_upper:
            dados["Conta"] = linha.split(":")[-1].strip()
        if "NOME" in linha_upper:
            dados["Cliente"] = linha.split(":")[-1].strip()
        if "IDENTIFICACAO" in linha_upper:
            dados["Identificação"] = linha.split(":")[-1].strip()

        if "SALDO DISPONIVEL" in linha_upper and "R$" in linha:
            valor = re.search(r"R\$[\s\.]*([\d.,-]+)", linha)
            if valor:
                dados["Saldo Disponível"] = parse_valor(valor.group(1))
                encontrou_valor = True

        if "SALDO LIVRE" in linha_upper and "R$" in linha:
            valor = re.search(r"R\$[\s\.]*([\d.,-]+)", linha)
            if valor:
                dados["Saldo Livre"] = parse_valor(valor.group(1))
                encontrou_valor = True

        if "LIMITE DA CONTA DISPONIVEL" in linha_upper:
            valor = re.search(r"R\$[\s\.]*([\d.,-]+)", linha)
            if valor:
                dados["Limite Disponível"] = parse_valor(valor.group(1))
                encontrou_valor = True

        elif "LIMITE DA CONTA" in linha_upper:
            valor = re.search(r"R\$[\s\.]*([\d.,-]+)", linha)
            if valor:
                dados["Limite Conta"] = parse_valor(valor.group(1))
                encontrou_valor = True

    return [dados] if encontrou_valor else []

def extrair_transacoes(texto, nome_arquivo):
    linhas = texto.splitlines()
    transacoes = []
    dia_atual = None

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue

        # Detecta valor no final da linha
        match_valor = re.search(r"([\d.]+,\d{2}-?)$", linha)
        if not match_valor:
            continue

        valor_str = match_valor.group(1)
        valor_pos = linha.rfind(valor_str)
        parte_esquerda = linha[:valor_pos].rstrip()

        # tenta pegar o documento (últimos 5+ dígitos antes do valor)
        match_doc = re.search(r"(\d{5,})\s+" + re.escape(valor_str), linha)
        documento = match_doc.group(1) if match_doc else ""

        # verifica se começa com dia (dois dígitos)
        match_dia = re.match(r"^(\d{2})\s+(.*)", parte_esquerda)
        if match_dia:
            dia_atual = match_dia.group(1)
            descricao = match_dia.group(2).strip()
        else:
            descricao = parte_esquerda.strip()

        if not dia_atual:
            continue  # ainda não temos data

        data_formatada = construir_data_completa(dia_atual, nome_arquivo)
        try:
            valor = parse_valor(valor_str)
            transacoes.append({
                "Data": data_formatada,
                "Descrição": descricao,
                "Documento": documento,
                "Valor (R$)": valor
            })
        except:
            continue

    return transacoes
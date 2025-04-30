import io
import chardet
from ofxparse import OfxParser


def detectar_codificacao(file_bytes):
    """
    Detecta a codificação de um arquivo usando chardet e tenta múltiplas opções
    com fallback seguro para ISO-8859-1.
    """
    detectado = chardet.detect(file_bytes)
    possiveis_encodings = [
        detectado.get("encoding"),
        "iso-8859-1",   # Prioriza encoding típico de bancos brasileiros
        "utf-8",
        "latin1",
        "windows-1252",
    ]

    for tentativa in possiveis_encodings:
        if not tentativa:
            continue
        try:
            texto = file_bytes.decode(tentativa, errors='replace')  # substitui caracteres inválidos
            return texto, tentativa
        except Exception:
            continue
    return None, "erro: falha na leitura com múltiplos encodings"


def parsear_ofx(texto):
    """
    Usa ofxparse para interpretar o conteúdo do OFX em texto.
    """
    try:
        return OfxParser.parse(io.StringIO(texto)), None
    except Exception as e:
        return None, f"erro no parser: {e}"


def montar_transacoes(ofx, file_name):
    """
    Constrói uma lista de transações a partir do objeto OFX parseado.
    """
    transacoes = []
    for t in ofx.account.statement.transactions:
        transacoes.append({
            "Arquivo": file_name,
            "Data": t.date.strftime('%d/%m/%Y'),
            "Descrição": t.memo,
            "Valor (R$)": t.amount,
            "TRNTYPE": t.type,
            "Tipo": "Crédito" if t.type.upper() == "CREDIT" else "Débito"
        })
    return transacoes


def extrair_lancamentos_ofx(file, file_name):
    """
    Função principal: lê o arquivo OFX, detecta encoding, parseia e retorna as transações.
    """
    file_bytes = file.read()
    texto, encoding_usado = detectar_codificacao(file_bytes)

    if texto is None:
        return [], encoding_usado

    ofx, erro = parsear_ofx(texto)
    if erro:
        return [], erro

    transacoes = montar_transacoes(ofx, file_name)
    return transacoes, encoding_usado
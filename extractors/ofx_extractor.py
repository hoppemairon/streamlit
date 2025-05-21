import io
import chardet
import re
from ofxparse import OfxParser
import logging
import unicodedata

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detectar_codificacao(file_bytes):
    """
    Detecta a codificação de um arquivo usando chardet e tenta múltiplas opções.
    """
    logger.info("Tentando detectar codificação do arquivo")
    detectado = chardet.detect(file_bytes)
    possiveis_encodings = [
        detectado.get("encoding"),
        "iso-8859-1",
        "utf-8",
        "latin1",
        "windows-1252",
        "cp1252",
    ]
    
    for tentativa in possiveis_encodings:
        if not tentativa:
            continue
        try:
            texto = file_bytes.decode(tentativa, errors='replace')
            logger.info(f"Arquivo decodificado com sucesso usando {tentativa}")
            return texto, tentativa
        except Exception as e:
            logger.warning(f"Falha ao decodificar com {tentativa}: {e}")
            continue
            
    logger.error("Falha em todas as tentativas de decodificação")
    return None, "erro: falha na leitura com múltiplos encodings"


def corrigir_valores_trnamt(texto):
    """
    Substitui vírgulas por ponto nos valores <TRNAMT>.
    """
    return re.sub(r"<TRNAMT>(-?\d+),(\d+)", r"<TRNAMT>\1.\2", texto)


def corrigir_cabecalho_ofx(texto):
    """
    Corrige o cabeçalho OFX para usar UTF-8 no parser e evitar erro de ascii.
    """
    texto = re.sub(r"ENCODING:.*", "ENCODING:UTF-8", texto)
    texto = re.sub(r"CHARSET:.*", "CHARSET:UTF-8", texto)
    return texto


def limpar_caracteres_invalidos(texto):
    """
    Remove ou substitui caracteres que podem causar problemas de codificação.
    """
    # Substitui caracteres não-ASCII por espaços ou equivalentes ASCII
    texto_limpo = ""
    for char in texto:
        if ord(char) < 128:
            texto_limpo += char
        else:
            # Substituições específicas para caracteres comuns em português
            if char == 'ç':
                texto_limpo += 'c'
            elif char == 'ã' or char == 'â' or char == 'á' or char == 'à':
                texto_limpo += 'a'
            elif char == 'é' or char == 'ê' or char == 'è':
                texto_limpo += 'e'
            elif char == 'í' or char == 'ì':
                texto_limpo += 'i'
            elif char == 'ó' or char == 'ô' or char == 'õ' or char == 'ò':
                texto_limpo += 'o'
            elif char == 'ú' or char == 'ù':
                texto_limpo += 'u'
            else:
                texto_limpo += ' '
    
    return texto_limpo


def parsear_ofx(texto):
    """
    Usa ofxparse para interpretar o conteúdo do OFX em texto limpo.
    """
    try:
        # Primeira tentativa com o texto original
        return OfxParser.parse(io.StringIO(texto)), None
    except UnicodeDecodeError as e:
        logger.warning(f"Erro de codificação na primeira tentativa: {e}")
        try:
            # Segunda tentativa com texto limpo
            texto_limpo = limpar_caracteres_invalidos(texto)
            return OfxParser.parse(io.StringIO(texto_limpo)), None
        except Exception as e2:
            logger.error(f"Erro na segunda tentativa após limpeza: {e2}")
            return None, f"erro após limpeza: {e2}"
    except ValueError as e:
        logger.error(f"Erro de formato: {e}")
        return None, f"erro de formato: {e}"
    except Exception as e:
        logger.error(f"Erro no parser: {e}")
        
        # Tentativa alternativa com uma abordagem mais agressiva
        try:
            # Converter para ASCII, ignorando caracteres problemáticos
            texto_ascii = texto.encode('ascii', 'ignore').decode('ascii')
            return OfxParser.parse(io.StringIO(texto_ascii)), None
        except Exception as e_ascii:
            logger.error(f"Falha na tentativa ASCII: {e_ascii}")
            return None, f"erro no parser: {e}"


def montar_transacoes(ofx, file_name):
    """
    Constrói uma lista de transações a partir do objeto OFX parseado.
    """
    transacoes = []
    
    # Verificar se o objeto OFX tem a estrutura esperada
    if not hasattr(ofx, 'account') or not hasattr(ofx.account, 'statement'):
        logger.warning("Estrutura OFX inválida ou incompleta")
        return transacoes
    
    # Extrair informações da conta
    conta_info = {
        "banco": getattr(ofx.account, 'routing_number', 'N/A'),
        "agencia": getattr(ofx.account, 'branch_id', 'N/A'),
        "conta": getattr(ofx.account, 'account_id', 'N/A'),
        "tipo_conta": getattr(ofx.account, 'account_type', 'N/A'),
        "moeda": getattr(ofx.account.statement, 'currency', 'BRL')
    }
    
    logger.info(f"Processando {len(ofx.account.statement.transactions)} transações")
    
    for t in ofx.account.statement.transactions:
        # Validar valores antes de adicionar
        valor = getattr(t, 'amount', 0.0)
        data = t.date.strftime('%d/%m/%Y') if hasattr(t, 'date') else 'N/A'
        
        transacoes.append({
            "Arquivo": file_name,
            "Data": data,
            "Descrição": getattr(t, 'memo', ''),
            "Valor (R$)": valor,
            "Num Doc.": getattr(t, "checknum", None),
            "TRNTYPE": getattr(t, "type", ""),
            "Tipo": "Crédito" if getattr(t, "type", "").upper() == "CREDIT" else "Débito",
            "Banco": conta_info["banco"],
            "Conta": conta_info["conta"]
        })
    
    return transacoes


def extrair_lancamentos_ofx(file, file_name):
    """
    Função principal: faz todo o processamento para retornar as transações.
    """
    logger.info(f"Iniciando processamento do arquivo: {file_name}")
    
    try:
        file_bytes = file.read()
        texto, encoding_usado = detectar_codificacao(file_bytes)

        if texto is None:
            logger.error("Não foi possível detectar a codificação do arquivo")
            return [], encoding_usado

        # Aplicar correções no texto
        texto_corrigido = corrigir_valores_trnamt(texto)
        texto_corrigido = corrigir_cabecalho_ofx(texto_corrigido)

        # Tentativa com abordagem mais específica para Bradesco
        if "Bradesco" in file_name:
            logger.info("Arquivo do Bradesco detectado, aplicando tratamento específico")
            # Forçar codificação específica para arquivos do Bradesco
            try:
                # Reabrir o arquivo e tentar com codificação específica
                file.seek(0)
                texto_bradesco = file.read().decode('iso-8859-1', errors='replace')
                texto_bradesco = corrigir_valores_trnamt(texto_bradesco)
                texto_bradesco = corrigir_cabecalho_ofx(texto_bradesco)
                
                # Remover caracteres problemáticos específicos
                texto_bradesco = re.sub(r'[^\x00-\x7F]+', ' ', texto_bradesco)
                
                ofx, erro = parsear_ofx(texto_bradesco)
                if not erro:
                    transacoes = montar_transacoes(ofx, file_name)
                    logger.info(f"Processamento específico para Bradesco concluído: {len(transacoes)} transações")
                    return transacoes, "iso-8859-1 (tratamento especial)"
            except Exception as e_bradesco:
                logger.warning(f"Falha no tratamento específico para Bradesco: {e_bradesco}")
                # Continuar com o fluxo normal se falhar

        # Fluxo normal
        ofx, erro = parsear_ofx(texto_corrigido)
        if erro:
            logger.error(f"Erro ao fazer parse do arquivo: {erro}")
            
            # Tentativa alternativa com codificação forçada
            try:
                # Converter para ASCII puro
                texto_ascii = ''.join(char for char in texto_corrigido if ord(char) < 128)
                ofx_alt, erro_alt = parsear_ofx(texto_ascii)
                
                if not erro_alt:
                    transacoes = montar_transacoes(ofx_alt, file_name)
                    logger.info(f"Processamento com ASCII puro concluído: {len(transacoes)} transações")
                    return transacoes, f"{encoding_usado} (convertido para ASCII)"
            except Exception as e_alt:
                logger.error(f"Falha na tentativa alternativa: {e_alt}")
            
            return [], erro

        transacoes = montar_transacoes(ofx, file_name)
        logger.info(f"Processamento concluído: {len(transacoes)} transações extraídas")
        return transacoes, encoding_usado
        
    except Exception as e:
        logger.exception(f"Erro não tratado: {e}")
        return [], f"erro não tratado: {e}"
    
def normalizar_texto(texto):
    """
    Remove acentuação e normaliza espaços e caixa.
    """
    if not texto:
        return ""
    texto = texto.lower().strip()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join([c for c in texto if not unicodedata.combining(c)])
    return re.sub(r'\s+', ' ', texto)

def remover_lancamentos_duplicados(transacoes):
    """
    Remove lançamentos duplicados da lista de transações baseada em data, valor, tipo e descrição normalizada.
    """
    vistos = set()
    transacoes_unicas = []

    for t in transacoes:
        chave = (
            t.get("Data"),
            round(float(t.get("Valor (R$)", 0)), 2),
            t.get("Tipo"),
            normalizar_texto(t.get("Descrição", ""))
        )
        if chave not in vistos:
            vistos.add(chave)
            transacoes_unicas.append(t)

    return transacoes_unicas

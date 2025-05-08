import pandas as pd
from datetime import datetime
import json
import os
import logging
from typing import Dict, List, Optional

from logic.contratos_emprestimos import ContratoEmprestimo, calcular_taxa_equivalente, obter_taxa_mercado

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GerenciadorContratos:
    """Classe para gerenciar múltiplos contratos de empréstimos"""

    def __init__(self, caminho_arquivo: str = "./data/contratos.json"):
        """
        Inicializa o gerenciador de contratos

        Args:
            caminho_arquivo: Caminho para o arquivo de contratos
        """
        self.caminho_arquivo = caminho_arquivo
        self.contratos = {}
        self.carregar_contratos()

    def carregar_contratos(self):
        """Carrega contratos do arquivo JSON"""
        if not os.path.exists(self.caminho_arquivo):
            logger.info(f"Arquivo de contratos não encontrado: {self.caminho_arquivo}")
            return

        try:
            with open(self.caminho_arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)

                for num_contrato, info in dados.items():
                    # Converter strings de data para datetime
                    data_contrato = datetime.strptime(info['data_contrato'], '%Y-%m-%d')
                    data_primeira_parcela = datetime.strptime(info['data_primeira_parcela'], '%Y-%m-%d')

                    # Criar objeto de contrato
                    self.contratos[num_contrato] = ContratoEmprestimo(
                        numero_contrato=num_contrato,
                        data_contrato=data_contrato,
                        data_primeira_parcela=data_primeira_parcela,
                        valor_contratado=float(info['valor_contratado']),
                        taxa_juros=float(info['taxa_juros']),
                        prazo_meses=int(info['prazo_meses']),
                        tipo_contrato=info['tipo_contrato']
                    )

                    # Registrar pagamentos se existirem
                    if 'pagamentos' in info:
                        for pagamento in info['pagamentos']:
                            data_pagamento = datetime.strptime(pagamento['data'], '%Y-%m-%d')
                            self.contratos[num_contrato].registrar_pagamento(
                                data_pagamento=data_pagamento,
                                valor_pago=float(pagamento['valor']),
                                descricao=pagamento.get('descricao', '')
                            )

                logger.info(f"Carregados {len(self.contratos)} contratos")

        except Exception as e:
            logger.error(f"Erro ao carregar contratos: {e}")

    def salvar_contratos(self):
        """Salva contratos no arquivo JSON"""
        os.makedirs(os.path.dirname(self.caminho_arquivo), exist_ok=True)

        dados = {}

        for num_contrato, contrato in self.contratos.items():
            dados_contrato = {
                'data_contrato': contrato.data_contrato.strftime('%Y-%m-%d'),
                'data_primeira_parcela': contrato.data_primeira_parcela.strftime('%Y-%m-%d'),
                'valor_contratado': contrato.valor_contratado,
                'taxa_juros': contrato.taxa_juros * 100,  # Converter para percentual
                'prazo_meses': contrato.prazo_meses,
                'tipo_contrato': contrato.tipo_contrato,
                'pagamentos': []
            }

            for pagamento in contrato.parcelas_pagas:
                dados_contrato['pagamentos'].append({
                    'data': pagamento['Data_Pagamento'].strftime('%Y-%m-%d'),
                    'valor': pagamento['Valor_Pago'],
                    'descricao': pagamento.get('Descricao', '')
                })

            dados[num_contrato] = dados_contrato

        try:
            with open(self.caminho_arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)

            logger.info(f"Salvos {len(self.contratos)} contratos em {self.caminho_arquivo}")

        except Exception as e:
            logger.error(f"Erro ao salvar contratos: {e}")

    def adicionar_contrato(self, contrato: ContratoEmprestimo):
        """Adiciona um novo contrato ao gerenciador"""
        self.contratos[contrato.numero_contrato] = contrato
        logger.info(f"Contrato adicionado: {contrato.numero_contrato}")
        self.salvar_contratos()

    def remover_contrato(self, numero_contrato: str):
        """Remove um contrato do gerenciador"""
        if numero_contrato in self.contratos:
            del self.contratos[numero_contrato]
            logger.info(f"Contrato removido: {numero_contrato}")
            self.salvar_contratos()
        else:
            logger.warning(f"Contrato não encontrado: {numero_contrato}")

    def obter_contrato(self, numero_contrato: str) -> Optional[ContratoEmprestimo]:
        """Retorna o contrato pelo número, se existir"""
        return self.contratos.get(numero_contrato)

    def listar_contratos(self) -> List[str]:
        """Lista todos os números de contratos cadastrados"""
        return list(self.contratos.keys())

    def associar_pagamentos_a_contratos(self, df_pagamentos: pd.DataFrame):
        """
        Associa pagamentos detectados no DataFrame aos contratos cadastrados,
        usando o campo 'Contrato' do DataFrame.
        """
        for numero_contrato in df_pagamentos['Contrato'].unique():
            if numero_contrato == "SEM_CONTRATO":
                continue
            contrato = self.obter_contrato(numero_contrato)
            if contrato:
                pagamentos = df_pagamentos[df_pagamentos['Contrato'] == numero_contrato]
                contrato.associar_pagamentos(pagamentos)
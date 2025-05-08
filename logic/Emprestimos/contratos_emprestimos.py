import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Dict, List, Tuple, Optional

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContratoEmprestimo:
    """Classe para gerenciar contratos de empréstimos e seus cálculos"""
    
    def __init__(self, 
                 numero_contrato: str,
                 data_contrato: datetime,
                 data_primeira_parcela: datetime,
                 valor_contratado: float,
                 taxa_juros: float,
                 prazo_meses: int,
                 tipo_contrato: str = "PRICE"):
        self.numero_contrato = numero_contrato
        self.data_contrato = data_contrato
        self.data_primeira_parcela = data_primeira_parcela
        self.valor_contratado = float(valor_contratado)
        self.taxa_juros = float(taxa_juros) / 100  # Converter para decimal
        self.prazo_meses = int(prazo_meses)
        self.tipo_contrato = tipo_contrato.upper()
        self.parcelas_calculadas = None
        self.parcelas_pagas = []
        self._calcular_parcelas()
    
    def _calcular_parcelas(self):
        """Calcula as parcelas teóricas do contrato com base no tipo"""
        parcelas = []
        
        if self.tipo_contrato == "PRICE":
            # Sistema Francês (parcelas iguais)
            valor_parcela = self.valor_contratado * (
                (self.taxa_juros * (1 + self.taxa_juros) ** self.prazo_meses) / 
                ((1 + self.taxa_juros) ** self.prazo_meses - 1)
            )
            
            saldo_devedor = self.valor_contratado
            
            for i in range(1, self.prazo_meses + 1):
                juros = saldo_devedor * self.taxa_juros
                amortizacao = valor_parcela - juros
                saldo_devedor -= amortizacao
                
                if i == self.prazo_meses:
                    amortizacao += saldo_devedor
                    saldo_devedor = 0
                
                data_vencimento = self._calcular_data_parcela(i)
                
                parcelas.append({
                    'Parcela': i,
                    'Data_Vencimento': data_vencimento,
                    'Valor_Parcela': float(valor_parcela),
                    'Juros': float(juros),
                    'Amortizacao': float(amortizacao),
                    'Saldo_Devedor': float(saldo_devedor)
                })
                
        elif self.tipo_contrato == "SAC":
            amortizacao = self.valor_contratado / self.prazo_meses
            saldo_devedor = self.valor_contratado
            
            for i in range(1, self.prazo_meses + 1):
                juros = saldo_devedor * self.taxa_juros
                valor_parcela = amortizacao + juros
                saldo_devedor -= amortizacao
                
                data_vencimento = self._calcular_data_parcela(i)
                
                parcelas.append({
                    'Parcela': i,
                    'Data_Vencimento': data_vencimento,
                    'Valor_Parcela': float(valor_parcela),
                    'Juros': float(juros),
                    'Amortizacao': float(amortizacao),
                    'Saldo_Devedor': float(saldo_devedor)
                })
        else:
            logger.warning(f"Tipo de contrato não suportado: {self.tipo_contrato}")
            
        self.parcelas_calculadas = pd.DataFrame(parcelas)
    
    def _calcular_data_parcela(self, numero_parcela: int) -> datetime:
        from dateutil.relativedelta import relativedelta
        if numero_parcela == 1:
            return self.data_primeira_parcela
        return self.data_primeira_parcela + relativedelta(months=numero_parcela-1)
    
    def registrar_pagamento(self, data_pagamento: datetime, valor_pago: float, descricao: str = ""):
        self.parcelas_pagas.append({
            'Data_Pagamento': data_pagamento,
            'Valor_Pago': float(abs(valor_pago)),
            'Descricao': descricao
        })
    
    def associar_pagamentos(self, df_pagamentos: pd.DataFrame):
        self.parcelas_pagas = []
        df_pagamentos['Valor_Abs'] = df_pagamentos['Valor (R$)'].astype(float).abs()
        for _, row in df_pagamentos.iterrows():
            self.registrar_pagamento(
                data_pagamento=row['Data'],
                valor_pago=row['Valor_Abs'],
                descricao=row.get('Descrição', '') or row.get('Memo', '') or row.get('MEMO', '')
            )
    
    def analisar_divergencias(self) -> pd.DataFrame:
        if self.parcelas_calculadas is None:
            logger.warning("Parcelas não calculadas")
            return pd.DataFrame()
        if not self.parcelas_pagas:
            logger.warning("Nenhum pagamento registrado")
            return pd.DataFrame()
        
        df_pagos = pd.DataFrame(self.parcelas_pagas)
        df_pagos = df_pagos.sort_values('Data_Pagamento')
        resultado = self.parcelas_calculadas.copy()
        resultado['Status'] = 'Pendente'
        resultado['Data_Pagamento'] = None
        resultado['Valor_Pago'] = None
        resultado['Divergencia'] = None
        resultado['Percentual_Divergencia'] = None
        
        for i, pagamento in enumerate(df_pagos.itertuples()):
            if i < len(resultado):
                parcela = resultado.iloc[i]
                resultado.at[i, 'Data_Pagamento'] = pagamento.Data_Pagamento
                resultado.at[i, 'Valor_Pago'] = float(pagamento.Valor_Pago)
                resultado.at[i, 'Status'] = 'Pago'
                divergencia = float(pagamento.Valor_Pago) - float(parcela['Valor_Parcela'])
                resultado.at[i, 'Divergencia'] = divergencia
                if parcela['Valor_Parcela'] > 0:
                    perc_div = (divergencia / float(parcela['Valor_Parcela'])) * 100
                    resultado.at[i, 'Percentual_Divergencia'] = perc_div
        return resultado
    
    def resumo_contrato(self) -> Dict:
        total_pago = float(sum(float(p['Valor_Pago']) for p in self.parcelas_pagas))
        qtd_parcelas_pagas = len(self.parcelas_pagas)
        valor_teorico = 0.0
        if self.parcelas_calculadas is not None and qtd_parcelas_pagas > 0:
            valor_teorico = float(self.parcelas_calculadas.iloc[:qtd_parcelas_pagas]['Valor_Parcela'].sum())
        divergencia_total = total_pago - valor_teorico
        perc_medio_div = 0.0
        if valor_teorico > 0:
            perc_medio_div = (divergencia_total / valor_teorico) * 100
        return {
            'Numero_Contrato': self.numero_contrato,
            'Tipo_Contrato': self.tipo_contrato,
            'Valor_Contratado': float(self.valor_contratado),
            'Taxa_Juros': float(self.taxa_juros) * 100,
            'Prazo_Total': int(self.prazo_meses),
            'Parcelas_Pagas': qtd_parcelas_pagas,
            'Parcelas_Pendentes': int(self.prazo_meses) - qtd_parcelas_pagas,
            'Total_Pago': total_pago,
            'Total_Teorico': valor_teorico,
            'Divergencia_Total': divergencia_total,
            'Percentual_Divergencia': perc_medio_div
        }


def calcular_taxa_equivalente(taxa_anual: float, periodo_meses: int = 12) -> float:
    taxa_anual_decimal = float(taxa_anual) / 100
    taxa_mensal_decimal = (1 + taxa_anual_decimal) ** (1 / periodo_meses) - 1
    return taxa_mensal_decimal * 100


def obter_taxa_mercado(tipo_emprestimo: str) -> float:
    taxas_referencia = {
        "PESSOAL": 60.0,
        "CONSIGNADO": 24.0,
        "IMOBILIARIO": 10.0,
        "VEICULAR": 18.0,
        "RURAL": 8.0,
        "EMPRESARIAL": 15.0
    }
    tipo_normalizado = tipo_emprestimo.upper().strip()
    if tipo_normalizado in taxas_referencia:
        return taxas_referencia[tipo_normalizado]
    for tipo, taxa in taxas_referencia.items():
        if tipo in tipo_normalizado or tipo_normalizado in tipo:
            return taxa
    return taxas_referencia["PESSOAL"]
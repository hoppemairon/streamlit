import os
import pandas as pd
from logic.ValidacaoArgoNetunna import comparador_argo_netunna as comparador
from logic.ValidacaoArgoNetunna import mapeador_empresas as mapeador

def executar_pipeline_completa(pasta_argo, pasta_netunna):
    empresas_argo = mapeador.carregar_empresas_argo()
    empresas_netunna = mapeador.carregar_empresas_netunna()
    mapeamento = mapeador.mapear_empresas_por_cnpj(empresas_argo, empresas_netunna)

    df_argo = comparador.carregar_todos_jsons_pasta(pasta_argo, tipo='argo')
    df_netunna = comparador.carregar_todos_jsons_pasta(pasta_netunna, tipo='netunna')

    resultados = []

    for _, empresa in mapeamento.iterrows():
        id_argo = empresa['empresa_argo_id']
        id_netunna = empresa['empresa_netunna_id']
        nome = empresa['empresa_argo_nome']

        vendas_argo_empresa = df_argo[df_argo['idempresa'] == id_argo]
        vendas_netunna_empresa = df_netunna[df_netunna['venda.empresa_codigo'] == id_netunna]

        if vendas_argo_empresa.empty and vendas_netunna_empresa.empty:
            continue

        comparativo = comparador.comparar_vendas(vendas_argo_empresa, vendas_netunna_empresa)

        # Corrigir campo data para agrupamento
        comparativo['data'] = pd.to_datetime(comparativo['datahora'], errors='coerce').dt.date

        # Gerar valor_base consolidado
        comparativo['valor_base'] = comparativo['valor_argo']
        comparativo.loc[comparativo['valor_base'].isna(), 'valor_base'] = comparativo['valor_netunna']

        # Agregação por data com base no status
        resumo_por_dia = comparativo.groupby('data').agg(
            batidas=('status', lambda x: (x == '✅ Batido').sum()),
            pendentes=('status', lambda x: (x != '✅ Batido').sum()),
            valor_batido=('valor_base', lambda x: x[comparativo.loc[x.index, 'status'] == '✅ Batido'].sum()),
            valor_pendente=('valor_base', lambda x: x[comparativo.loc[x.index, 'status'] != '✅ Batido'].sum())
        ).reset_index()

        for _, row in resumo_por_dia.iterrows():
            registrar_fechamento(
                dia=row['data'],
                id_empresa=id_argo,
                batidas=row['batidas'],
                pendentes=row['pendentes'],
                valor_batido=row['valor_batido'],
                valor_pendente=row['valor_pendente'],
                fechado=False
            )

        resultados.append({
            'empresa_id': id_argo,
            'empresa_nome': nome,
            'comparativo': comparativo
        })

    return resultados


def registrar_fechamento(dia, id_empresa, batidas, pendentes, valor_batido, valor_pendente, fechado):
    pasta = 'Fechamentos'
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f'fechamentos_empresa_{id_empresa}.csv')

    linha = {
        'data': str(dia),
        'dia_fechado': fechado,
        'transacoes_batidas': batidas,
        'transacoes_pendentes': pendentes,
        'valor_batido': valor_batido,
        'valor_pendente': valor_pendente
    }

    if os.path.exists(caminho):
        df = pd.read_csv(caminho)
        df = df[df['data'] != str(dia)]
        df = pd.concat([df, pd.DataFrame([linha])], ignore_index=True)
    else:
        df = pd.DataFrame([linha])

    df.to_csv(caminho, index=False)


def marcar_dia_como_fechado(id_empresa, dia):
    caminho = f"Fechamentos/fechamentos_empresa_{id_empresa}.csv"
    if not os.path.exists(caminho):
        return

    df = pd.read_csv

def carregar_fechamentos(id_empresa):
    caminho = f"Fechamentos/fechamentos_empresa_{id_empresa}.csv"
    if os.path.exists(caminho):
        return pd.read_csv(caminho)
    return pd.DataFrame(columns=[
        'data',
        'dia_fechado',
        'transacoes_batidas',
        'transacoes_pendentes',
        'valor_batido',
        'valor_pendente'
    ])
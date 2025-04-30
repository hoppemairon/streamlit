import pandas as pd
import streamlit as st
import os
import json

# ----------- Carregar Adquirentes e Bandeiras -----------
def carregar_adquirentes():
    caminho = os.path.join('logic', 'ArquivosNetunna', 'ListaAdquirentes - TeiaCard.json')
    with open(caminho, 'r', encoding='utf-8') as f:
        adquirentes = json.load(f)
    return pd.DataFrame(adquirentes['data'])

def carregar_bandeiras():
    caminho = os.path.join('logic', 'ArquivosNetunna', 'ListaBandeiras - TeiaCard.json')
    with open(caminho, 'r', encoding='utf-8') as f:
        bandeiras = json.load(f)
    return pd.DataFrame(bandeiras['data'])

# ----------- Gerar lista combinada (não mudou) -----------
def gerar_lista_combinada_adquirente_bandeira(adquirentes, bandeiras):
    lista = []
    for adquirente in adquirentes['name'].dropna().unique():
        for bandeira in bandeiras['name'].dropna().unique():
            lista.append(f"{adquirente} - {bandeira}")
    return lista

# ----------- Função principal (agora usando formapagamento) -----------
def mapear_formapagamento_v3_com_sugestoes(formapagamentos_argo, sugestoes_automaticas=None):
    """Mapeia Formas de Pagamento ARGO para Adquirente e Bandeira."""
    adquirentes_netunna = carregar_adquirentes()
    bandeiras_netunna = carregar_bandeiras()

    mapeamento = []

    adquirentes = ['[Não Mapeado]'] + sorted(adquirentes_netunna['name'].dropna().unique())
    bandeiras = ['[Não Mapeado]'] + sorted(bandeiras_netunna['name'].dropna().unique())

    for formapagamento in sorted(formapagamentos_argo):
        col1, col2 = st.columns(2)

        sugestao_adquirente, sugestao_bandeira = sugestoes_automaticas.get(formapagamento, ("[Não Mapeado]", "[Não Mapeado]")) if sugestoes_automaticas else ("[Não Mapeado]", "[Não Mapeado]")

        with col1:
            adquirente_escolhido = st.selectbox(
                f"Adquirente para Forma de Pagamento: {formapagamento}",
                options=adquirentes,
                index=adquirentes.index(sugestao_adquirente) if sugestao_adquirente in adquirentes else 0,
                key=f"adquirente_{formapagamento}"
            )

        with col2:
            bandeira_escolhida = st.selectbox(
                f"Bandeira para Forma de Pagamento: {formapagamento}",
                options=bandeiras,
                index=bandeiras.index(sugestao_bandeira) if sugestao_bandeira in bandeiras else 0,
                key=f"bandeira_{formapagamento}"
            )

        if adquirente_escolhido == '[Não Mapeado]' or bandeira_escolhida == '[Não Mapeado]':
            combinado_final = formapagamento
            mapeado = False
        else:
            combinado_final = f"{adquirente_escolhido} - {bandeira_escolhida}"
            mapeado = True

        mapeamento.append({
            'formapagamento_argo_nome': formapagamento,
            'adquirente_netunna_nome': adquirente_escolhido,
            'bandeira_netunna_nome': bandeira_escolhida,
            'combinado_netunna': combinado_final,
            'mapeado': mapeado
        })

    df_mapeamento = pd.DataFrame(mapeamento)

    return df_mapeamento

# ----------- Salvar / Carregar -----------
def salvar_mapeamento_operadoras(df_mapeamento, caminho_csv=None, caminho_json=None):
    if caminho_csv:
        df_mapeamento.to_csv(caminho_csv, index=False)
    if caminho_json:
        df_mapeamento.to_json(caminho_json, orient='records', indent=4)

def carregar_mapeamento_operadoras(caminho):
    if caminho.endswith('.csv'):
        return pd.read_csv(caminho)
    elif caminho.endswith('.json'):
        return pd.read_json(caminho)
    else:
        raise ValueError("Formato de arquivo não suportado para mapeamento (use .csv ou .json)")
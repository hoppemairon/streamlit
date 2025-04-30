import streamlit as st
import pandas as pd
import json
import os
from logic import mapeador_operadoras as mapeador_op

st.set_page_config(page_title="Mapeamento de Formas de Pagamento", layout="wide")
st.title('🔹 Mapeamento de Formas de Pagamento ARGO para Netunna')

# Upload dos arquivos
st.subheader('🔹 Upload dos Arquivos Base')
file_vendas_argo = st.file_uploader('Upload arquivo de vendas ARGO (para listar Formas de Pagamento)', type=['json'])

# SUGESTÕES automáticas (baseado no que você mandou)
sugestoes_automaticas = { }

# Processar uploads
if file_vendas_argo:
    vendas_argo = pd.DataFrame(json.load(file_vendas_argo))

    if 'formapagamento' in vendas_argo.columns:
        # Formas de pagamento reais no arquivo
        formas_pagamento_ativas = vendas_argo['formapagamento'].dropna().unique()
        formas_pagamento_ativas = [fp for fp in formas_pagamento_ativas if fp.strip() != '']

        st.success(f'✅ {len(formas_pagamento_ativas)} formas de pagamento únicas encontradas no ARGO!')

        # Mostrar exemplos
        st.subheader('🔍 Formas de Pagamento encontradas com exemplo:')

        exemplos = []

        for formapagamento in sorted(formas_pagamento_ativas):
            exemplo = vendas_argo[vendas_argo['formapagamento'] == formapagamento].head(1)
            if not exemplo.empty:
                exemplos.append({
                    'Forma de Pagamento': formapagamento,
                    'Data Venda': exemplo.iloc[0]['datavenda'],
                    'Valor Bruto': exemplo.iloc[0]['valorbruto'],
                    'NSU': exemplo.iloc[0]['nsu'] if 'nsu' in exemplo.columns else ''
                })

        df_exemplos = pd.DataFrame(exemplos)

        st.dataframe(df_exemplos, use_container_width=True)

        # --- Mapeamento manual usando V3 atualizado ---
        df_mapeamento = mapeador_op.mapear_formapagamento_v3_com_sugestoes(
            formas_pagamento_ativas, 
            sugestoes_automaticas
        )

        if not df_mapeamento.empty:
            st.subheader('🔎 Mapeamento Realizado')
            st.dataframe(df_mapeamento, use_container_width=True)

            if st.button('📥 Salvar Mapeamento'):
                mapeador_op.salvar_mapeamento_operadoras(
                    df_mapeamento,
                    caminho_csv='mapeamento_formapagamento.csv',
                    caminho_json='mapeamento_formapagamento.json'
                )
                st.success('✅ Mapeamento salvo com sucesso!')
    else:
        st.error('⚠️ Arquivo ARGO não possui coluna "formapagamento". Verifique o formato!')
else:
    st.info('⚠️ Faça upload do arquivo de vendas ARGO para iniciar o mapeamento.')
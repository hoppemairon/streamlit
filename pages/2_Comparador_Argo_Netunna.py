import streamlit as st
import pandas as pd
import os

from logic import comparador_argo_netunna as comparador
from logic import mapeador_empresas as mapeador
from logic import fechamento_conciliador as fechamento

# ----------- Configurações da Página -----------
st.set_page_config(page_title="Comparador ARGO x Netunna", layout="wide")
st.title('📊 Comparador de Vendas - ARGO x Netunna')

# ----------- Inicializar Session State -----------
variaveis_session = [
    'df_argo', 'df_netunna', 'empresas_argo', 'empresas_netunna',
    'mapeamento', 'comparativo', 'sugestoes', 'validacoes_temporarias', 'resultados_pipeline'
]
for var in variaveis_session:
    if var not in st.session_state:
        st.session_state[var] = None

# ----------- Upload dos Arquivos de Vendas -----------
st.subheader('🔹 Upload das Vendas')
pasta_vendas_argo = st.text_input('Caminho da Pasta de Vendas ARGO', r'C:\Users\mairo\OneDrive\Área de Trabalho\Teste Netunna\Vendas_Argo')
pasta_vendas_netunna = st.text_input('Caminho da Pasta de Vendas Netunna', r'C:\Users\mairo\OneDrive\Área de Trabalho\Teste Netunna\Vendas_Netunna')

if st.button('🚀 Carregar Arquivos de Vendas'):
    with st.spinner('🔄 Lendo empresas configuradas...'):
        st.session_state['empresas_argo'] = mapeador.carregar_empresas_argo()
        st.session_state['empresas_netunna'] = mapeador.carregar_empresas_netunna()

    with st.spinner('🔄 Lendo vendas...'):
        st.session_state['df_argo'] = comparador.carregar_todos_jsons_pasta(pasta_vendas_argo, tipo='argo')
        st.session_state['df_netunna'] = comparador.carregar_todos_jsons_pasta(pasta_vendas_netunna, tipo='netunna')

    with st.spinner('🔄 Mapeando Empresas...'):
        st.session_state['mapeamento'] = mapeador.mapear_empresas_por_cnpj(
            st.session_state['empresas_argo'],
            st.session_state['empresas_netunna']
        )
    st.success('✅ Arquivos carregados com sucesso!')

# ----------- Comparação Manual Normal -----------
if st.session_state['df_argo'] is not None and st.session_state['df_netunna'] is not None:

    st.subheader('🔹 Mapeamento de Empresas')
    empresa_display = st.selectbox('Selecione a Empresa para Comparar', st.session_state['mapeamento']['empresa_display'])

    if empresa_display:
        empresa_row = st.session_state['mapeamento'][st.session_state['mapeamento']['empresa_display'] == empresa_display]
        id_empresa_argo = empresa_row['empresa_argo_id'].values[0]
        id_empresa_netunna = empresa_row['empresa_netunna_id'].values[0]

        vendas_argo = st.session_state['df_argo'][st.session_state['df_argo']['idempresa'] == id_empresa_argo].copy()
        vendas_netunna = st.session_state['df_netunna'][st.session_state['df_netunna']['venda.empresa_codigo'] == id_empresa_netunna].copy()

        vendas_argo['data_somente'] = vendas_argo['datavenda'].dt.date
        vendas_netunna['data_somente'] = pd.to_datetime(vendas_netunna['venda.venda_data']).dt.date

        todas_datas = sorted(set(vendas_argo['data_somente'].dropna()).union(set(vendas_netunna['data_somente'].dropna())))
        datas_selecionadas = st.multiselect('Selecione as Datas para Comparar', todas_datas)

        if datas_selecionadas:
            vendas_argo_data = vendas_argo[vendas_argo['data_somente'].isin(datas_selecionadas)]
            vendas_netunna_data = vendas_netunna[vendas_netunna['data_somente'].isin(datas_selecionadas)]

            operadoras_disponiveis = vendas_argo_data['formapagamento'].dropna().unique()
            operadoras_selecionadas = st.multiselect('Selecione as Formas de Pagamento (opcional)', operadoras_disponiveis)

            if operadoras_selecionadas:
                vendas_argo_data = vendas_argo_data[vendas_argo_data['formapagamento'].isin(operadoras_selecionadas)]

            if not vendas_argo_data.empty and not vendas_netunna_data.empty:
                comparativo = comparador.comparar_vendas(vendas_argo_data, vendas_netunna_data)
                comparativo['datahora'] = pd.to_datetime(comparativo['datahora']).dt.date
                st.session_state['comparativo'] = comparativo.copy()

                status_disponiveis = ['✅ Batido', '⚠️ Só no ARGO', '⚠️ Só na Netunna']
                status_selecionados = st.multiselect('Selecione os Status para Visualizar', status_disponiveis, default=status_disponiveis)

                if status_selecionados:
                    comparativo = comparativo[comparativo['status'].isin(status_selecionados)]

                col1, col2 = st.columns(2)
                with col1:
                    valor_total_argo = vendas_argo_data['valorbruto'].sum()
                    st.metric(label="🔵 Valor Total ARGO", value=f"R$ {valor_total_argo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                    st.dataframe(vendas_argo_data[['nsu', 'datavenda', 'valorbruto', 'formapagamento']].reset_index(drop=True), use_container_width=True)

                with col2:
                    valor_total_netunna = vendas_netunna_data['venda.valor_bruto'].sum()
                    st.metric(label="🔴 Valor Total Netunna", value=f"R$ {valor_total_netunna:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                    st.dataframe(vendas_netunna_data[['venda.nsu', 'venda.venda_data', 'venda.valor_bruto', 'venda.bandeira']].reset_index(drop=True), use_container_width=True)

                st.subheader('🔍 Comparativo das Datas Selecionadas')
                st.dataframe(comparativo[['nsu_argo', 'valor_argo', 'nsu_netunna', 'valor_netunna', 'status']], use_container_width=True)

               #st.subheader('🔗 Gerenciar Relacionamentos Manuais')
               #if st.button('✨ Gerar Sugestões de Relacionamento'):
               #    st.session_state['sugestoes'] = comparador.gerar_sugestoes_relacionamentos_v2(
               #        vendas_argo_data, vendas_netunna_data, st.session_state['comparativo'], id_empresa_argo, datas_selecionadas
               #    )

               #    if st.session_state['sugestoes'].empty:
               #        st.warning('⚠️ Nenhuma sugestão encontrada.')
               #    else:
               #        st.success(f'✅ {len(st.session_state["sugestoes"])} sugestões geradas.')

               #if st.session_state['sugestoes'] is not None and not st.session_state['sugestoes'].empty:
               #    if st.session_state['validacoes_temporarias'] is None:
               #        st.session_state['validacoes_temporarias'] = []

               #    for idx, sugestao in st.session_state['sugestoes'].iterrows():
               #        with st.expander(f"Relacionamento {idx+1} - Método: {sugestao['metodo_sugestao']}"):
               #            aceita = st.checkbox('✅ Aceitar essa sugestão', key=f"aceitar_{idx}")
               #            observacao = st.text_input('📝 Observação (opcional)', key=f"observacao_{idx}")
               #            if aceita:
               #                sugestao_dict = sugestao.to_dict()
               #                sugestao_dict['validado'] = True
               #                sugestao_dict['observacao'] = observacao
               #                st.session_state['validacoes_temporarias'].append(sugestao_dict)

               #    if st.session_state['validacoes_temporarias']:
               #        if st.button('📥 Salvar Relacionamentos Validados'):
               #            df_validacoes = pd.DataFrame(st.session_state['validacoes_temporarias'])
               #            comparador.salvar_validacoes_json(df_validacoes, id_empresa_argo, datas_selecionadas)
               #            st.success(f"✅ {len(df_validacoes)} validações salvas!")
               #            st.session_state['validacoes_temporarias'] = []

            st.subheader('🖥️ Resumo por Sistema (ARGO x Netunna)')
            resumo = comparador.resumo_por_status_valor(st.session_state['comparativo'])
            st.dataframe(resumo, use_container_width=True)

else:
    st.info('⚠️ Carregue os arquivos de vendas para iniciar.')

# ----------- 🔵 Validação Manual de Transações Pendentes -----------
st.subheader('🖐️ Validação Manual de Transações Pendentes')

# Filtra pendências
pendentes = st.session_state['comparativo'][st.session_state['comparativo']['status'] != '✅ Batido'].copy()

if not pendentes.empty:
    st.info(f'⚠️ {len(pendentes)} transações pendentes encontradas. É necessário validá-las manualmente para fechar o dia.')

    # Inicializa session_state se necessário
    if 'validacoes_pendentes' not in st.session_state:
        st.session_state['validacoes_pendentes'] = {}

    for idx, row in pendentes.iterrows():
        with st.expander("🔍 Detalhes da Transação Pendente"):
            if pd.notna(row['nsu_argo']):
                st.markdown(f"""
                **🟠 Transação ARGO**
                - Data: `{row['datahora']}`
                - Valor: `R$ {row['valor_argo']:,.2f}`
                - NSU: `{row['nsu_argo']}`
                - Forma de Pagamento: `{row.get('formapagamento_argo', 'N/A')}`
                """)
            if pd.notna(row['nsu_netunna']):
                st.markdown(f"""
                **🔵 Transação Netunna**
                - Data: `{row['datahora']}`
                - Valor: `R$ {row['valor_netunna']:,.2f}`
                - NSU: `{row['nsu_netunna']}`
                - Bandeira: `{row.get('bandeira_netunna', 'N/A')}`
                - Adquirente: `{row.get('operadora_netunna', 'N/A')}`
                """)

            decisao = st.radio(
                "Decisão para esta transação:",
                ('Selecionar correspondência', 'Justificar como correta', 'Marcar como erro'),
                key=f'decisao_{idx}'
            )

            observacao = st.text_input('Observação:', key=f'observacao_{idx}')

            escolhido = None
            if decisao == 'Selecionar correspondência':
                vendas_netunna_data = st.session_state['df_netunna']
                vendas_netunna_data['data_dia'] = pd.to_datetime(vendas_netunna_data['venda.venda_data'], errors='coerce').dt.date

                # NSUs já usados
                nsus_batidos_netunna = st.session_state['comparativo']['nsu_netunna'].dropna().unique().tolist()
                nsus_validados_manual = [
                    v['nsu_selecionado'] for v in st.session_state.get('validacoes_pendentes', {}).values()
                    if v['decisao'] == 'Selecionar correspondência' and v['nsu_selecionado']
                ]
                nsus_indisponiveis = set(nsus_batidos_netunna + nsus_validados_manual)

                candidatos = vendas_netunna_data[
                    (vendas_netunna_data['data_dia'] == pd.to_datetime(row['datahora']).date()) &
                    (abs(vendas_netunna_data['venda.valor_bruto'] - (row['valor_argo'] or row['valor_netunna'])) <= 0.05) &
                    (~vendas_netunna_data['venda.nsu'].isin(nsus_indisponiveis))
                ]

                if not candidatos.empty:
                    candidatos['label_opcao'] = candidatos.apply(
                        lambda r: f"{r['venda.nsu']} | {r['venda.venda_data'][:10]} | R$ {r['venda.valor_bruto']:.2f} | {r.get('venda.bandeira', '')} | {r.get('venda.operadora', '')}",
                        axis=1
                    )
                    mapa_nsu = dict(zip(candidatos['label_opcao'], candidatos['venda.nsu'].astype(str)))
                    labels_exibidos = ['Nenhum'] + list(mapa_nsu.keys())

                    escolhido_label = st.selectbox(
                        'Selecione um NSU correspondente Netunna',
                        labels_exibidos,
                        key=f'nsu_escolhido_{idx}'
                    )
                    escolhido = mapa_nsu.get(escolhido_label, None)
                else:
                    st.warning('❌ Nenhuma correspondência possível encontrada para esta transação.')

            # Salva a decisão temporariamente
            st.session_state['validacoes_pendentes'][idx] = {
                'data': str(pd.to_datetime(row['datahora']).date()),
                'nsu_argo': row.get('nsu_argo'),
                'valor_argo': row.get('valor_argo'),
                'formapagamento_argo': row.get('formapagamento_argo'),
                'nsu_netunna': row.get('nsu_netunna'),
                'valor_netunna': row.get('valor_netunna'),
                'bandeira_netunna': row.get('bandeira_netunna'),
                'operadora_netunna': row.get('operadora_netunna'),
                'decisao': decisao,
                'nsu_selecionado': escolhido,
                'observacao': observacao
            }

else:
    st.success('✅ Todas as transações foram conciliadas automaticamente.')



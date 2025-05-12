import streamlit as st
import pandas as pd
import time
from datetime import date, timedelta
import datetime
import os

# Importe suas funções reais
from logic.ValidacaoArgoNetunna.mapeador_empresas import carregar_empresas_argo, carregar_empresas_netunna, mapear_empresas_por_cnpj
from logic.ValidacaoArgoNetunna.Dados_Netunna import get_token as get_token_netunna, get_parcelas, to_dataframe as to_dataframe_netunna
from logic.ValidacaoArgoNetunna.Dados_Argo import get_token_argo, get_transacoes_argo, to_dataframe_argo
from logic.ValidacaoArgoNetunna.comparador_argo_netunna import comparar_vendas, gerar_sugestoes_relacionamentos_v2, resumo_por_status_valor
from logic.ValidacaoArgoNetunna import fechamento_conciliador as fechamento

st.set_page_config(page_title="Comparador ARGO x Netunna", layout="wide")
st.title('📊 Comparador de Vendas - ARGO x Netunna')

abas = st.tabs(["1️⃣ Buscar Dados via API", "2️⃣ Comparativo e Filtros"])

# ----------- ABA 1: BUSCA VIA API -----------
with abas[0]:
    st.subheader("1️⃣ Buscar dados das APIs")
    col1, col2 = st.columns(2)
    with col1:
        periodo = st.date_input(
            "Período (Data inicial e final)",
            value=[date.today(), date.today()],
            format="DD/MM/YYYY"
        )
    with col2:
        empresas_argo = carregar_empresas_argo()
        empresas_netunna = carregar_empresas_netunna()
        mapeamento = mapear_empresas_por_cnpj(empresas_argo, empresas_netunna)
        if mapeamento.empty:
            st.error("Não há empresas mapeadas entre Netunna e Argo.")
            st.stop()
        empresa_display = st.selectbox(
            "Selecione a unidade (apenas empresas mapeadas):",
            mapeamento['empresa_display']
        )
        empresa_row = mapeamento[mapeamento['empresa_display'] == empresa_display]
        id_empresa_argo = empresa_row['empresa_argo_id'].values[0]
        id_empresa_netunna = empresa_row['empresa_netunna_id'].values[0]

    if len(periodo) != 2:
        st.warning("Selecione o período desejado.")
        st.stop()
    data_ini, data_fim = periodo

    if st.button("Buscar dados das duas APIs"):
        with st.spinner("Consultando dados na Netunna..."):
            token_netunna = get_token_netunna()
            if not token_netunna:
                st.error("Erro ao autenticar na Netunna.")
                st.stop()
            total_dias = (data_fim - data_ini).days + 1
            dados_netunna = []
            data_atual = data_ini
            for i in range(total_dias):
                # Corrige o desvio de um dia na Netunna
                data_api = (data_atual + timedelta(days=1)).strftime("%Y%m%d")
                dados_dia = get_parcelas(token_netunna, "venda", data_api, id_empresa_netunna)
                if dados_dia:
                    for item in dados_dia:
                        item['data_consulta'] = data_atual.strftime("%d/%m/%Y")
                    dados_netunna.extend(dados_dia)
                data_atual += timedelta(days=1)
                time.sleep(0.5)
            df_netunna = to_dataframe_netunna(dados_netunna)
            st.success(f"{len(df_netunna)} registros Netunna encontrados.")

        with st.spinner("Consultando dados na Argo..."):
            token_argo = get_token_argo()
            if not token_argo:
                st.error("Erro ao autenticar na Argo.")
                st.stop()
            dados_argo = []
            data_atual = data_ini
            for i in range(total_dias):
                dados_dia = get_transacoes_argo(token_argo, data_atual, data_atual)
                if dados_dia:
                    for item in dados_dia:
                        item['data_consulta'] = data_atual.strftime("%d/%m/%Y")
                    dados_argo.extend(dados_dia)
                data_atual += timedelta(days=1)
            df_argo = to_dataframe_argo(dados_argo)
            df_argo = df_argo[df_argo['idempresa'] == id_empresa_argo]
            st.success(f"{len(df_argo)} registros Argo encontrados.")

        # Salva no session_state para a próxima aba
        st.session_state['df_argo'] = df_argo
        st.session_state['df_netunna'] = df_netunna
        st.session_state['mapeamento'] = mapeamento

        # Exibe lado a lado
        st.subheader("Dados Netunna x Argo")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Netunna**")
            st.dataframe(df_netunna)
        with col2:
            st.markdown("**Argo**")
            st.dataframe(df_argo)

# ----------- ABA 2: COMPARATIVO E FILTROS -----------
with abas[1]:
    st.subheader("2️⃣ Comparativo Detalhado")
    if st.session_state.get('df_argo') is not None and st.session_state.get('df_netunna') is not None:
        df_argo = st.session_state['df_argo']
        df_netunna = st.session_state['df_netunna']
        mapeamento = st.session_state['mapeamento']

        st.subheader('🔹 Mapeamento de Empresas')
        empresa_display = st.selectbox('Selecione a Empresa para Comparar', 
                                       mapeamento['empresa_display'],
                                       key='empresa_select')

        if empresa_display:
            empresa_row = mapeamento[mapeamento['empresa_display'] == empresa_display]
            id_empresa_argo = empresa_row['empresa_argo_id'].values[0]
            id_empresa_netunna = empresa_row['empresa_netunna_id'].values[0]

            vendas_argo = df_argo[df_argo['idempresa'] == id_empresa_argo].copy()
            vendas_netunna = df_netunna[df_netunna['venda.empresa_codigo'] == id_empresa_netunna].copy()

            if vendas_argo.empty and vendas_netunna.empty:
                st.warning(f'⚠️ Nenhuma venda encontrada para a empresa selecionada.')
            else:
                vendas_argo['data_somente'] = pd.to_datetime(vendas_argo['datavenda'], errors='coerce').dt.date
                vendas_netunna['data_somente'] = pd.to_datetime(vendas_netunna['venda.venda_data'], errors='coerce').dt.date

                todas_datas = sorted(set(vendas_argo['data_somente'].dropna()).union(set(vendas_netunna['data_somente'].dropna())))
                
                if not todas_datas:
                    st.warning('⚠️ Nenhuma data válida encontrada nas vendas.')
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        data_inicial = st.date_input('Data Inicial', min(todas_datas), key='data_inicial')
                    with col2:
                        data_final = st.date_input('Data Final', max(todas_datas), key='data_final')
                    
                    datas_selecionadas = [d for d in todas_datas if data_inicial <= d <= data_final]
                    
                    if datas_selecionadas:
                        vendas_argo_data = vendas_argo[vendas_argo['data_somente'].isin(datas_selecionadas)]
                        vendas_netunna_data = vendas_netunna[vendas_netunna['data_somente'].isin(datas_selecionadas)]

                        operadoras_disponiveis = sorted(vendas_argo_data['formapagamento'].dropna().unique())
                        operadoras_selecionadas = st.multiselect('Selecione as Formas de Pagamento (opcional)', 
                                                                 operadoras_disponiveis,
                                                                 key='operadoras')

                        if operadoras_selecionadas:
                            vendas_argo_data = vendas_argo_data[vendas_argo_data['formapagamento'].isin(operadoras_selecionadas)]

                        if not vendas_argo_data.empty or not vendas_netunna_data.empty:
                            with st.spinner('🔄 Comparando vendas...'):
                                comparativo = comparar_vendas(vendas_argo_data, vendas_netunna_data)
                                comparativo['datahora'] = pd.to_datetime(comparativo['datahora'], errors='coerce').dt.date
                                st.session_state['comparativo'] = comparativo.copy()

                            status_disponiveis = ['✅ Batido', '⚠️ Só no ARGO', '⚠️ Só na Netunna', '⚠️ Possível Match Data+Valor']
                            status_selecionados = st.multiselect('Selecione os Status para Visualizar', 
                                                                  status_disponiveis, 
                                                                  default=status_disponiveis,
                                                                  key='status_filter')

                            if status_selecionados:
                                comparativo_filtrado = comparativo[comparativo['status'].isin(status_selecionados)]
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    valor_total_argo = vendas_argo_data['valorbruto'].sum()
                                    st.metric(label="🔵 Valor Total ARGO", 
                                              value=f"R$ {valor_total_argo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                                    with st.expander("Detalhes ARGO"):
                                        st.dataframe(vendas_argo_data[['nsu', 'datavenda', 'valorbruto', 'formapagamento']].reset_index(drop=True), 
                                                     use_container_width=True)

                                with col2:
                                    valor_total_netunna = vendas_netunna_data['venda.valor_bruto'].sum()
                                    st.metric(label="🔴 Valor Total Netunna", 
                                              value=f"R$ {valor_total_netunna:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                                    with st.expander("Detalhes Netunna"):
                                        st.dataframe(
                                            vendas_netunna_data[['venda.nsu', 'venda.venda_data', 'venda.valor_bruto', 'venda.bandeira']].rename(
                                                columns={'venda.bandeira': 'id_bandeira'}
                                            ).reset_index(drop=True),
                                            use_container_width=True
                                        )

                                st.subheader('🔍 Comparativo das Datas Selecionadas')
                                st.dataframe(comparativo_filtrado[['nsu_argo', 'valor_argo', 'nsu_netunna', 'valor_netunna', 'status']], 
                                             use_container_width=True)

                                st.subheader('🖥️ Resumo por Sistema (ARGO x Netunna)')
                                resumo = resumo_por_status_valor(comparativo)
                                st.dataframe(resumo, use_container_width=True)
                                
                                if st.button('✨ Gerar Sugestões de Relacionamento', key='btn_sugestoes'):
                                    with st.spinner('🔄 Gerando sugestões...'):
                                        sugestoes = gerar_sugestoes_relacionamentos_v2(
                                            vendas_argo_data, vendas_netunna_data, st.session_state['comparativo'], 
                                            id_empresa_argo, datas_selecionadas
                                        )
                                        st.session_state['sugestoes'] = sugestoes

                                    if st.session_state['sugestoes'] is None or st.session_state['sugestoes'].empty:
                                        st.warning('⚠️ Nenhuma sugestão encontrada.')
                                    else:
                                        st.success(f'✅ {len(st.session_state["sugestoes"])} sugestões geradas.')
                                        st.subheader('🔗 Sugestões de Relacionamento')
                                        st.dataframe(st.session_state['sugestoes'][[
                                            'nsu_argo', 'valor_argo', 'nsu_netunna', 'valor_netunna', 'metodo_sugestao'
                                        ]], use_container_width=True)
                            else:
                                st.info('ℹ️ Selecione pelo menos um status para visualizar os resultados.')
                        else:
                            st.warning('⚠️ Nenhuma venda encontrada para os filtros selecionados.')
                    else:
                        st.warning('⚠️ Selecione um intervalo de datas válido.')

        # ----------- Validação Manual -----------
        st.subheader('🖐️ Validação Manual de Transações Pendentes')

        if 'comparativo' in st.session_state and st.session_state['comparativo'] is not None:
            pendentes = st.session_state['comparativo'][st.session_state['comparativo']['status'] != '✅ Batido'].copy()
            
            if not pendentes.empty:
                st.info(f'⚠️ {len(pendentes)} transações pendentes encontradas. É necessário validá-las manualmente para fechar o dia.')

                if 'validacoes_pendentes' not in st.session_state:
                    st.session_state['validacoes_pendentes'] = {}

                for idx, row in pendentes.iterrows():
                    with st.expander(f"🔍 Transação Pendente #{idx+1} - Status: {row['status']}"):
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
                            """)

                        decisao = st.radio(
                            "Decisão para esta transação:",
                            ('Selecionar correspondência', 'Justificar como correta', 'Marcar como erro'),
                            key=f'decisao_{idx}'
                        )

                        observacao = st.text_input('Observação:', key=f'observacao_{idx}')

                        escolhido = None
                        if decisao == 'Selecionar correspondência':
                            try:
                                vendas_netunna_data = st.session_state['df_netunna'][
                                    st.session_state['df_netunna']['venda.empresa_codigo'] == id_empresa_netunna
                                ].copy()
                                
                                vendas_netunna_data['data_dia'] = pd.to_datetime(vendas_netunna_data['venda.venda_data'], errors='coerce').dt.date

                                nsus_batidos_netunna = st.session_state['comparativo']['nsu_netunna'].dropna().unique().tolist()
                                nsus_validados_manual = [
                                    v['nsu_selecionado'] for v in st.session_state.get('validacoes_pendentes', {}).values()
                                    if v.get('decisao') == 'Selecionar correspondência' and v.get('nsu_selecionado')
                                ]
                                nsus_indisponiveis = set(nsus_batidos_netunna + nsus_validados_manual)

                                valor_comparacao = row['valor_argo'] if pd.notna(row['valor_argo']) else row['valor_netunna']
                                data_comparacao = pd.to_datetime(row['datahora']).date() if pd.notna(row['datahora']) else None

                                candidatos = vendas_netunna_data[
                                    (vendas_netunna_data['data_dia'] == data_comparacao) &
                                    (abs(vendas_netunna_data['venda.valor_bruto'] - valor_comparacao) <= 0.05) &
                                    (~vendas_netunna_data['venda.nsu'].astype(str).isin([str(x) for x in nsus_indisponiveis]))
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
                                    
                                    if escolhido_label != 'Nenhum':
                                        escolhido = mapa_nsu.get(escolhido_label)
                                else:
                                    st.warning("⚠️ Nenhum candidato encontrado para correspondência.")
                            except Exception as e:
                                st.error(f"Erro ao buscar candidatos: {str(e)}")

                        if st.button('💾 Salvar Decisão', key=f'salvar_{idx}'):
                            st.session_state['validacoes_pendentes'][idx] = {
                                'idx': idx,
                                'nsu_argo': row.get('nsu_argo'),
                                'valor_argo': row.get('valor_argo'),
                                'nsu_netunna': row.get('nsu_netunna'),
                                'valor_netunna': row.get('valor_netunna'),
                                'decisao': decisao,
                                'observacao': observacao,
                                'nsu_selecionado': escolhido,
                                'data_validacao': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            st.success('✅ Decisão salva!')

                if st.session_state['validacoes_pendentes']:
                    if st.button('📥 Finalizar Todas as Validações', key='finalizar_validacoes'):
                        try:
                            empresa_row = st.session_state['mapeamento'][st.session_state['mapeamento']['empresa_display'] == empresa_display]
                            id_empresa = empresa_row['empresa_argo_id'].values[0]
                            
                            df_validacoes = pd.DataFrame(list(st.session_state['validacoes_pendentes'].values()))
                            
                            nome_arquivo = f"validacao_manual_{id_empresa}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                            pasta_validacoes = 'ValidacaoArgoNetunna'
                            os.makedirs(pasta_validacoes, exist_ok=True)
                            caminho_completo = os.path.join(pasta_validacoes, nome_arquivo)
                            
                            df_validacoes.to_csv(caminho_completo, index=False)
                            
                            datas_validadas = pd.to_datetime(pendentes['datahora']).dt.date.unique()
                            for data in datas_validadas:
                                fechamento.marcar_dia_como_fechado(id_empresa, data)
                            
                            st.success(f"✅ {len(df_validacoes)} validações salvas em {caminho_completo}!")
                            st.session_state['validacoes_pendentes'] = {}
                        except Exception as e:
                            st.error(f"❌ Erro ao salvar validações: {str(e)}")
            else:
                st.success('✅ Não há transações pendentes para validação.')
        else:
            st.info('⚠️ Realize uma comparação primeiro para visualizar as transações pendentes.')
import streamlit as st
import pandas as pd
import os
import datetime

from logic.ValidacaoArgoNetunna import comparador_argo_netunna as comparador
from logic.ValidacaoArgoNetunna import mapeador_empresas as mapeador
from logic.ValidacaoArgoNetunna import fechamento_conciliador as fechamento

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
col1, col2 = st.columns(2)
with col1:
    arquivos_argo = st.file_uploader("Upload arquivos ARGO (.json)", type="json", accept_multiple_files=True, key="upload_argo")
with col2:
    arquivos_netunna = st.file_uploader("Upload arquivos Netunna (.json)", type="json", accept_multiple_files=True, key="upload_netunna")

# Exibe quantidade de arquivos carregados para cada upload
st.info(f"📥 ARGO: {len(arquivos_argo) if arquivos_argo else 0} arquivo(s) carregado(s).")
st.info(f"📥 Netunna: {len(arquivos_netunna) if arquivos_netunna else 0} arquivo(s) carregado(s).")

if st.button('🚀 Carregar Arquivos de Vendas', key='btn_carregar'):
    try:
        with st.spinner('🔄 Lendo empresas configuradas...'):
            st.session_state['empresas_argo'] = mapeador.carregar_empresas_argo()
            st.session_state['empresas_netunna'] = mapeador.carregar_empresas_netunna()

        with st.spinner('🔄 Lendo vendas...'):
            st.session_state['df_argo'] = comparador.carregar_arquivos_upload(arquivos_argo, tipo='argo')
            st.session_state['df_netunna'] = comparador.carregar_arquivos_upload(arquivos_netunna, tipo='netunna')
            st.write("📋 Colunas df_argo:", st.session_state['df_argo'].columns.tolist())
            st.write("📋 Colunas df_netunna:", st.session_state['df_netunna'].columns.tolist())

        with st.spinner('🔄 Mapeando Empresas...'):
            st.session_state['mapeamento'] = mapeador.mapear_empresas_por_cnpj(
                st.session_state['empresas_argo'],
                st.session_state['empresas_netunna']
            )
        st.success('✅ Arquivos carregados com sucesso!')
    except Exception as e:
        st.error(f'❌ Erro ao carregar arquivos: {str(e)}')

# ----------- Comparação Manual Normal -----------
if st.session_state['df_argo'] is not None and st.session_state['df_netunna'] is not None:
    st.subheader('🔹 Mapeamento de Empresas')
    
    # Verificar se há empresas mapeadas
    if st.session_state['mapeamento'] is None or st.session_state['mapeamento'].empty:
        st.warning('⚠️ Nenhuma empresa mapeada. Verifique os arquivos de empresas.')
    else:
        empresa_display = st.selectbox('Selecione a Empresa para Comparar', 
                                      st.session_state['mapeamento']['empresa_display'],
                                      key='empresa_select')

        if empresa_display:
            empresa_row = st.session_state['mapeamento'][st.session_state['mapeamento']['empresa_display'] == empresa_display]
            id_empresa_argo = empresa_row['empresa_argo_id'].values[0]
            id_empresa_netunna = empresa_row['empresa_netunna_id'].values[0]

            if 'idempresa' not in st.session_state['df_argo'].columns:
                st.error("❌ A coluna 'idempresa' não existe em df_argo. Verifique a importação dos dados.")
                vendas_argo = pd.DataFrame()
            else:
                vendas_argo = st.session_state['df_argo'][st.session_state['df_argo']['idempresa'] == int(id_empresa_argo)].copy()
            if 'venda.empresa_codigo' not in st.session_state['df_netunna'].columns:
                st.error("❌ A coluna 'venda.empresa_codigo' não existe em df_netunna. Verifique a importação dos dados.")
                vendas_netunna = pd.DataFrame()
            else:
                vendas_netunna = st.session_state['df_netunna'][st.session_state['df_netunna']['venda.empresa_codigo'] == str(id_empresa_netunna)].copy()

            # Verificar se há vendas para a empresa selecionada
            if vendas_argo.empty and vendas_netunna.empty:
                st.warning(f'⚠️ Nenhuma venda encontrada para a empresa selecionada.')
            else:
                # Preparar datas para filtro
                vendas_argo['data_somente'] = pd.to_datetime(vendas_argo['datavenda'], errors='coerce').dt.date
                if not vendas_netunna.empty and 'venda.venda_data' in vendas_netunna.columns:
                    vendas_netunna['data_somente'] = pd.to_datetime(vendas_netunna['venda.venda_data'], errors='coerce').dt.date
                else:
                    vendas_netunna['data_somente'] = pd.NaT

                todas_datas = sorted(set(vendas_argo['data_somente'].dropna()).union(set(vendas_netunna['data_somente'].dropna())))
                
                if not todas_datas:
                    st.warning('⚠️ Nenhuma data válida encontrada nas vendas.')
                else:
                    # Filtro de datas
                    col1, col2 = st.columns(2)
                    with col1:
                        data_inicial = st.date_input('Data Inicial', min(todas_datas), key='data_inicial')
                    with col2:
                        data_final = st.date_input('Data Final', max(todas_datas), key='data_final')
                    
                    # Filtrar por intervalo de datas
                    datas_selecionadas = [d for d in todas_datas if data_inicial <= d <= data_final]
                    
                    if datas_selecionadas:
                        vendas_argo_data = vendas_argo[vendas_argo['data_somente'].isin(datas_selecionadas)]
                        vendas_netunna_data = vendas_netunna[vendas_netunna['data_somente'].isin(datas_selecionadas)]

                        # Filtro de operadoras/formas de pagamento
                        operadoras_disponiveis = sorted(vendas_argo_data['formapagamento'].dropna().unique())
                        operadoras_selecionadas = st.multiselect('Selecione as Formas de Pagamento (opcional)', 
                                                               operadoras_disponiveis,
                                                               key='operadoras')

                        if operadoras_selecionadas:
                            vendas_argo_data = vendas_argo_data[vendas_argo_data['formapagamento'].isin(operadoras_selecionadas)]

                        # Realizar comparação
                        if not vendas_argo_data.empty or not vendas_netunna_data.empty:
                            with st.spinner('🔄 Comparando vendas...'):
                                comparativo = comparador.comparar_vendas(vendas_argo_data, vendas_netunna_data)
                                comparativo['datahora'] = pd.to_datetime(comparativo['datahora'], errors='coerce').dt.date
                                st.session_state['comparativo'] = comparativo.copy()

                            # Filtro de status
                            status_disponiveis = ['✅ Batido', '⚠️ Só no ARGO', '⚠️ Só na Netunna']
                            status_selecionados = st.multiselect('Selecione os Status para Visualizar', 
                                                              status_disponiveis, 
                                                              default=status_disponiveis,
                                                              key='status_filter')

                            if status_selecionados:
                                comparativo_filtrado = comparativo[comparativo['status'].isin(status_selecionados)]
                                
                                # Exibir resumo
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

                                # Exibir comparativo
                                st.subheader('🔍 Comparativo das Datas Selecionadas')
                                st.dataframe(comparativo_filtrado[['nsu_argo', 'valor_argo', 'nsu_netunna', 'valor_netunna', 'status']], 
                                           use_container_width=True)

                                # Exibir resumo por status
                                st.subheader('🖥️ Resumo por Sistema (ARGO x Netunna)')
                                resumo = comparador.resumo_por_status_valor(comparativo)
                                st.dataframe(resumo, use_container_width=True)
                                
                                # Botão para gerar sugestões
                                if st.button('✨ Gerar Sugestões de Relacionamento', key='btn_sugestoes'):
                                    with st.spinner('🔄 Gerando sugestões...'):
                                        st.session_state['sugestoes'] = comparador.gerar_sugestoes_relacionamentos_v2(
                                            vendas_argo_data, vendas_netunna_data, st.session_state['comparativo'], 
                                            id_empresa_argo, datas_selecionadas
                                        )

                                    if st.session_state['sugestoes'] is None or st.session_state['sugestoes'].empty:
                                        st.warning('⚠️ Nenhuma sugestão encontrada.')
                                    else:
                                        st.success(f'✅ {len(st.session_state["sugestoes"])} sugestões geradas.')
                                        
                                        # Exibir sugestões
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

# ----------- 🖐️ Validação Manual de Transações Pendentes -----------
st.subheader('🖐️ Validação Manual de Transações Pendentes')

# Verifica se comparativo existe e não é None
if 'comparativo' in st.session_state and st.session_state['comparativo'] is not None:
    # Filtra pendências
    pendentes = st.session_state['comparativo'][st.session_state['comparativo']['status'] != '✅ Batido'].copy()
    
    if not pendentes.empty:
        st.info(f'⚠️ {len(pendentes)} transações pendentes encontradas. É necessário validá-las manualmente para fechar o dia.')

        # Inicializa session_state se necessário
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
                    # Obter candidatos para correspondência
                    try:
                        empresa_row = st.session_state['mapeamento'][st.session_state['mapeamento']['empresa_display'] == empresa_display]
                        id_empresa_argo = empresa_row['empresa_argo_id'].values[0]
                        id_empresa_netunna = empresa_row['empresa_netunna_id'].values[0]
                        
                        vendas_netunna_data = st.session_state['df_netunna'][
                            st.session_state['df_netunna']['venda.empresa_codigo'] == str(id_empresa_netunna)
                        ].copy()
                        vendas_netunna_data['data_dia'] = pd.to_datetime(vendas_netunna_data['venda.venda_data'], errors='coerce').dt.date

                        # NSUs já usados
                        nsus_batidos_netunna = st.session_state['comparativo']['nsu_netunna'].dropna().unique().tolist()
                        nsus_validados_manual = [
                            v['nsu_selecionado'] for v in st.session_state.get('validacoes_pendentes', {}).values()
                            if v.get('decisao') == 'Selecionar correspondência' and v.get('nsu_selecionado')
                        ]
                        nsus_indisponiveis = set(nsus_batidos_netunna + nsus_validados_manual)

                        # Valor para comparação
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

        # Botão para finalizar todas as validações
        if st.session_state['validacoes_pendentes']:
            if st.button('📥 Finalizar Todas as Validações', key='finalizar_validacoes'):
                try:
                    # Obter empresa atual
                    empresa_row = st.session_state['mapeamento'][st.session_state['mapeamento']['empresa_display'] == empresa_display]
                    id_empresa = empresa_row['empresa_argo_id'].values[0]
                    
                    # Criar DataFrame com validações
                    df_validacoes = pd.DataFrame(list(st.session_state['validacoes_pendentes'].values()))
                    
                    # Salvar validações
                    nome_arquivo = f"validacao_manual_{id_empresa}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    pasta_validacoes = 'ValidacaoArgoNetunna'
                    os.makedirs(pasta_validacoes, exist_ok=True)
                    caminho_completo = os.path.join(pasta_validacoes, nome_arquivo)
                    
                    df_validacoes.to_csv(caminho_completo, index=False)
                    
                    # Marcar dias como fechados
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

# ----------- Pipeline de Fechamento -----------
st.subheader('🔄 Pipeline de Fechamento Automático')

if st.button('🚀 Executar Pipeline de Fechamento', key='btn_pipeline'):
    with st.spinner('🔄 Executando pipeline de fechamento...'):
        try:
            resultados = fechamento.executar_pipeline_completa(st.session_state['df_argo'], st.session_state['df_netunna'])
            st.session_state['resultados_pipeline'] = resultados
            st.success(f'✅ Pipeline executada com sucesso para {len(resultados)} empresas!')
            
            # Exibir resumo da pipeline
            for resultado in resultados:
                with st.expander(f"Empresa: {resultado['empresa_nome']} (ID: {resultado['empresa_id']})"):
                    # Resumo por data
                    resumo_empresa = resultado['comparativo'].groupby('data').agg(
                        total=('status', 'count'),
                        batidas=('status', lambda x: (x == '✅ Batido').sum()),
                        pendentes=('status', lambda x: (x != '✅ Batido').sum())
                    ).reset_index()
                    
                    st.dataframe(resumo_empresa, use_container_width=True)
                    
                    # Carregar status de fechamento
                    fechamentos = fechamento.carregar_fechamentos(resultado['empresa_id'])
                    if not fechamentos.empty:
                        st.subheader('Status de Fechamento')
                        st.dataframe(fechamentos, use_container_width=True)
        except Exception as e:
            st.error(f'❌ Erro ao executar pipeline: {str(e)}')
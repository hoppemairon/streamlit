import streamlit as st
import pandas as pd
import io
import re
import os
from datetime import datetime

from extractors.ofx_extractor import extrair_lancamentos_ofx
from logic.Emprestimos.gerenciador_contratos import GerenciadorContratos
from logic.Emprestimos.contratos_emprestimos import ContratoEmprestimo

CAMINHO_MARCACOES = "./logic/CSVs/marcacoes_emprestimos.csv"

st.set_page_config(page_title="Análise de Empréstimos", layout="wide")
st.title("🔍 Validador de Pagamentos de Empréstimos")

def corrigir_ofx_valores(file_obj):
    conteudo = file_obj.read().decode("latin-1", errors="ignore")
    conteudo_corrigido = re.sub(r"<TRNAMT>(-?\d+),(\d+)", r"<TRNAMT>\1.\2", conteudo)
    return io.BytesIO(conteudo_corrigido.encode("latin-1", errors="ignore"))

def salvar_marcacoes(df_marcado):
    os.makedirs(os.path.dirname(CAMINHO_MARCACOES), exist_ok=True)
    colunas_salvar = ["Arquivo", "Data", "Descrição", "Valor (R$)", "Num Doc", "Num Doc."]
    colunas_presentes = [col for col in colunas_salvar if col in df_marcado.columns]
    if not colunas_presentes:
        st.warning("Nenhuma coluna identificadora encontrada para salvar marcações.")
        return
    df_marcado[colunas_presentes].drop_duplicates().to_csv(
        CAMINHO_MARCACOES,
        mode='a',
        header=not os.path.exists(CAMINHO_MARCACOES),
        index=False
    )
    st.success("Marcações salvas! Da próxima vez, elas serão recuperadas automaticamente.")

if 'ofx_raw_df' not in st.session_state:
    st.session_state.ofx_raw_df = None
if 'emprestimos_df' not in st.session_state:
    st.session_state.emprestimos_df = None
if 'gerenciador_contratos' not in st.session_state:
    st.session_state.gerenciador_contratos = GerenciadorContratos()

uploaded_files = st.file_uploader(
    "📁 Envie arquivos OFX para análise",
    type=["ofx"],
    accept_multiple_files=True
)

if uploaded_files:
    todas_transacoes = []

    for file in uploaded_files:
        try:
            file_corrigido = corrigir_ofx_valores(file)
            transacoes, encoding = extrair_lancamentos_ofx(file_corrigido, file.name)

            if not transacoes or isinstance(transacoes, str):
                st.error(f"Erro ao processar {file.name}")
                continue

            for t in transacoes:
                t['Arquivo'] = file.name

            todas_transacoes.extend(transacoes)

        except Exception as e:
            st.error(f"Erro ao processar {file.name}: {e}")

    df = pd.DataFrame(todas_transacoes)

    # Padroniza nome da coluna de documento
    if "Num Doc." in df.columns and "Num Doc" not in df.columns:
        df = df.rename(columns={"Num Doc.": "Num Doc"})

    # --- RECUPERA MARCAÇÕES SALVAS ---
    if not df.empty and os.path.exists(CAMINHO_MARCACOES) and os.path.getsize(CAMINHO_MARCACOES) > 0:
        df_marcacoes = pd.read_csv(CAMINHO_MARCACOES)
        if "Num Doc." in df_marcacoes.columns and "Num Doc" not in df_marcacoes.columns:
            df_marcacoes = df_marcacoes.rename(columns={"Num Doc.": "Num Doc"})
        colunas_merge = ["Arquivo", "Data", "Descrição", "Valor (R$)", "Num Doc"]
        colunas_presentes = [col for col in colunas_merge if col in df.columns and col in df_marcacoes.columns]
        if colunas_presentes:
            df = df.merge(
                df_marcacoes.assign(Marcar_Como_Emprestimo=True),
                on=colunas_presentes,
                how="left",
                suffixes=('', '_y')
            )
            df["Marcar_Como_Emprestimo"] = df["Marcar_Como_Emprestimo"].fillna(False)
        else:
            df["Marcar_Como_Emprestimo"] = False
    else:
        df["Marcar_Como_Emprestimo"] = False

    if 'Contrato' not in df.columns:
        df['Contrato'] = ""

    if df.empty:
        st.warning("Nenhuma transação encontrada.")
    else:
        st.session_state.ofx_raw_df = df

        # --- FILTRO POR DESCRIÇÃO E SELEÇÃO EM LOTE ---
        st.subheader("🖊️ Marcação Manual de Pagamentos de Empréstimo")

        filtro_descricao = st.text_input("🔎 Filtrar transações pela descrição:")

        df_filtrado = df.copy()
        if filtro_descricao:
            df_filtrado = df_filtrado[df_filtrado['Descrição'].str.contains(filtro_descricao, case=False, na=False)]

        df_filtrado['Valor (R$) - BR'] = df_filtrado['Valor (R$)'].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notnull(x) else ""
        )

        colunas_exibir = [
            'Arquivo',
            'Data',
            'Descrição',
            'Valor (R$) - BR',
            'Num Doc',
            'Tipo',
            'Banco',
            'Conta',
            'Marcar_Como_Emprestimo'
        ]
        colunas_exibir = [col for col in colunas_exibir if col in df_filtrado.columns]
        df_exibir = df_filtrado[colunas_exibir].copy()

        # --- Selecionar/Desmarcar todos exibidos ---
        if 'select_all_flag' not in st.session_state:
            st.session_state.select_all_flag = False
        if 'deselect_all_flag' not in st.session_state:
            st.session_state.deselect_all_flag = False

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Selecionar todos exibidos"):
                df_exibir['Marcar_Como_Emprestimo'] = True
                st.session_state.select_all_flag = True
                st.session_state.deselect_all_flag = False
                st.session_state['df_exibir'] = df_exibir
                st.rerun()
        with col2:
            if st.button("❌ Desmarcar todos exibidos"):
                df_exibir['Marcar_Como_Emprestimo'] = False
                st.session_state.deselect_all_flag = True
                st.session_state.select_all_flag = False
                st.session_state['df_exibir'] = df_exibir
                st.rerun()

        # Recupera o DataFrame ajustado após o rerun
        if 'df_exibir' in st.session_state:
            df_exibir = st.session_state['df_exibir']
            del st.session_state['df_exibir']

        edited_df = st.data_editor(
            df_exibir,
            column_config={
                "Marcar_Como_Emprestimo": st.column_config.CheckboxColumn(
                    "É pagamento de empréstimo?", default=False
                ),
                "Valor (R$) - BR": st.column_config.TextColumn(
                    "Valor (R$)", disabled=True
                )
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_transacoes"
        )

        st.session_state.select_all_flag = False
        st.session_state.deselect_all_flag = False

        # Atualiza a coluna de marcação no DataFrame original
        df_filtrado['Marcar_Como_Emprestimo'] = edited_df['Marcar_Como_Emprestimo']
        df.loc[df_filtrado.index, 'Marcar_Como_Emprestimo'] = df_filtrado['Marcar_Como_Emprestimo']

        # DataFrame apenas com os marcados
        df_marcado = df[df["Marcar_Como_Emprestimo"] == True].copy()
        if not df_marcado.empty and 'Contrato' not in df_marcado.columns:
            df_marcado['Contrato'] = ""
        st.session_state.emprestimos_df = df_marcado

        # --- BOTÃO PARA SALVAR MARCAÇÕES ---
        if not df_marcado.empty and st.button("💾 Salvar marcações atuais"):
            salvar_marcacoes(df_marcado)

        # --- ASSOCIAÇÃO EM LOTE (SOMENTE NÃO ASSOCIADOS) ---
        if not st.session_state.emprestimos_df.empty:
            df_possiveis = st.session_state.emprestimos_df[
                st.session_state.emprestimos_df['Contrato'].isnull() | (st.session_state.emprestimos_df['Contrato'] == "")
            ]

            if not df_possiveis.empty:
                st.subheader("🔗 Associar múltiplos lançamentos a um contrato")
                indices_disponiveis = df_possiveis.index.tolist()

                if 'multiselect_indices' not in st.session_state:
                    st.session_state.multiselect_indices = []

                selecionados = st.multiselect(
                    "Selecione os lançamentos para associar a um contrato:",
                    options=indices_disponiveis,
                    default=st.session_state.multiselect_indices,
                    format_func=lambda x: f"{df_possiveis.loc[x, 'Data']} | {df_possiveis.loc[x, 'Descrição']} | R$ {df_possiveis.loc[x, 'Valor (R$)']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    key="multiselect_indices"
                )

                contratos_existentes = st.session_state.gerenciador_contratos.listar_contratos()
                contrato_escolhido = st.selectbox(
                    "Selecione o contrato para associar os lançamentos selecionados:",
                    options=["<Novo>"] + contratos_existentes,
                    key="contrato_escolhido"
                )

                if contrato_escolhido == "<Novo>":
                    novo_num = st.text_input("Informe o número do novo contrato:", key="novo_num_lote")
                    if novo_num and st.button("Associar ao novo contrato", key="btn_novo_lote"):
                        st.session_state.emprestimos_df.loc[selecionados, 'Contrato'] = novo_num
                        st.success(f"{len(selecionados)} lançamentos associados ao contrato {novo_num}")
                        df.update(st.session_state.emprestimos_df)
                        st.session_state.multiselect_indices = []
                        st.rerun()
                else:
                    if st.button("Associar ao contrato selecionado", key="btn_existente_lote"):
                        st.session_state.emprestimos_df.loc[selecionados, 'Contrato'] = contrato_escolhido
                        st.success(f"{len(selecionados)} lançamentos associados ao contrato {contrato_escolhido}")
                        df.update(st.session_state.emprestimos_df)
                        st.session_state.multiselect_indices = []
                        st.rerun()
            else:
                st.info("Todos os lançamentos já foram associados a contratos.")

        # --- RESUMO POR CONTRATO ---
        if 'Contrato' in st.session_state.emprestimos_df.columns:
            resumo = (
                st.session_state.emprestimos_df.groupby('Contrato')
                .agg(
                    Total_Credito=pd.NamedAgg(column='Valor (R$)', aggfunc=lambda x: x[st.session_state.emprestimos_df.loc[x.index, 'Tipo'] == 'Crédito'].sum()),
                    Total_Debito=pd.NamedAgg(column='Valor (R$)', aggfunc=lambda x: x[st.session_state.emprestimos_df.loc[x.index, 'Tipo'] == 'Débito'].sum()),
                    Qtd_Lancamentos=('Valor (R$)', 'count')
                )
                .reset_index()
            )
            st.subheader("📊 Resumo por Contrato")
            st.dataframe(resumo, use_container_width=True)

        # --- Fluxo original de cadastro e associação de contratos ---
        if not st.session_state.emprestimos_df.empty:
            st.subheader("🔗 Vinculação de Contrato Para Pagamentos")
            contratos_existentes = st.session_state.gerenciador_contratos.listar_contratos()
            for idx, row in st.session_state.emprestimos_df.iterrows():
                if pd.isnull(row.get('Contrato', "")) or row.get('Contrato', "") == "":
                    descricao = str(row.get('Descrição', ''))
                    data = pd.to_datetime(row.get('Data')).strftime('%d/%m/%Y') if not pd.isnull(row.get('Data')) else ''
                    valor = row.get('Valor (R$)', '')
                    valor_str = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notnull(valor) else ''
                    transacao_str = f"Descrição: {descricao} | Data: {data} | Valor: {valor_str}"

                    st.write(transacao_str)
                    contrato_selecionado = st.selectbox(
                        f"Selecione ou crie um contrato para:\n{transacao_str}",
                        options=["<Novo>"] + contratos_existentes,
                        key=f"contrato_select_{idx}_{hash(transacao_str)}"
                    )
                    if contrato_selecionado == "<Novo>":
                        novo_num = st.text_input(
                            f"Informe o número do novo contrato para:\n{transacao_str}",
                            key=f"novo_num_{idx}_{hash(transacao_str)}"
                        )
                        if novo_num:
                            st.session_state.emprestimos_df.loc[idx, 'Contrato'] = novo_num
                    else:
                        st.session_state.emprestimos_df.loc[idx, 'Contrato'] = contrato_selecionado

if st.session_state.emprestimos_df is not None and not st.session_state.emprestimos_df.empty:
    st.success(f"{len(st.session_state.emprestimos_df)} pagamentos de empréstimo selecionados pelo usuário.")

    if 'Contrato' not in st.session_state.emprestimos_df.columns:
        st.session_state.emprestimos_df['Contrato'] = ""

    st.divider()
    st.subheader("📝 Cadastro de Contratos de Empréstimo")
    contratos_detectados = st.session_state.emprestimos_df['Contrato'].unique()

    for contrato_num in contratos_detectados:
        if not contrato_num or contrato_num == "SEM_CONTRATO":
            continue
        with st.expander(f"Contrato {contrato_num}"):
            contrato_existente = st.session_state.gerenciador_contratos.obter_contrato(contrato_num)
            if contrato_existente:
                st.success("Contrato já cadastrado.")
                st.write(contrato_existente.resumo_contrato())
            else:
                data_contrato = st.date_input(f"Data do Contrato ({contrato_num})", key=f"data_contrato_{contrato_num}")
                data_primeira = st.date_input(f"Data da 1ª Parcela ({contrato_num})", key=f"data_primeira_{contrato_num}")
                valor = st.number_input(f"Valor Contratado ({contrato_num})", min_value=0.0, key=f"valor_{contrato_num}")
                taxa = st.number_input(f"Juros Contratado ao mês (%) ({contrato_num})", min_value=0.0, key=f"taxa_{contrato_num}")
                prazo = st.number_input(f"Prazo (meses) ({contrato_num})", min_value=1, step=1, key=f"prazo_{contrato_num}")
                tipo = st.selectbox(f"Tipo de Contrato ({contrato_num})", ["PRICE", "SAC"], key=f"tipo_{contrato_num}")
                if st.button(f"Salvar Contrato {contrato_num}"):
                    contrato = ContratoEmprestimo(
                        numero_contrato=contrato_num,
                        data_contrato=pd.to_datetime(data_contrato),
                        data_primeira_parcela=pd.to_datetime(data_primeira),
                        valor_contratado=valor,
                        taxa_juros=taxa,
                        prazo_meses=int(prazo),
                        tipo_contrato=tipo
                    )
                    st.session_state.gerenciador_contratos.adicionar_contrato(contrato)
                    st.success("Contrato cadastrado com sucesso!")

    if st.button("🔗 Associar Pagamentos aos Contratos"):
        st.session_state.gerenciador_contratos.associar_pagamentos_a_contratos(st.session_state.emprestimos_df)
        st.success("Pagamentos associados!")

    st.divider()
    st.subheader("📋 Tabelas de Transações por Contrato")

    for contrato_num in st.session_state.emprestimos_df['Contrato'].unique():
        if not contrato_num or contrato_num == "SEM_CONTRATO":
            continue
        st.markdown(f"#### Contrato {contrato_num}")

        df_contrato = st.session_state.emprestimos_df[
            st.session_state.emprestimos_df['Contrato'] == contrato_num
        ].copy()

        if 'Data' in df_contrato.columns:
            df_contrato['Data'] = pd.to_datetime(df_contrato['Data'], errors='coerce')
            df_contrato = df_contrato.sort_values('Data')

        colunas_tabela = [
            'Arquivo', 'Data', 'Valor (R$) - BR', 'Num Doc', 'Tipo', 'Banco', 'Conta', 'Descrição'
        ]
        colunas_tabela = [col for col in colunas_tabela if col in df_contrato.columns]

        st.dataframe(df_contrato[colunas_tabela], use_container_width=True)

with st.expander("📊 Ver todas as transações importadas"):
    if st.session_state.ofx_raw_df is not None:
        st.dataframe(st.session_state.ofx_raw_df, use_container_width=True)
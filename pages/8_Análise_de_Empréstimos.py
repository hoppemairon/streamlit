import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

from extractors.ofx_extractor import extrair_lancamentos_ofx
from logic.gerenciador_contratos import GerenciadorContratos
from logic.contratos_emprestimos import ContratoEmprestimo

st.set_page_config(page_title="Análise de Empréstimos", layout="wide")
st.title("🔍 Validador de Pagamentos de Empréstimos")

def corrigir_ofx_valores(file_obj):
    conteudo = file_obj.read().decode("latin-1", errors="ignore")
    conteudo_corrigido = re.sub(r"<TRNAMT>(-?\d+),(\d+)", r"<TRNAMT>\1.\2", conteudo)
    return io.BytesIO(conteudo_corrigido.encode("latin-1", errors="ignore"))

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

    #st.subheader("🛠️ Diagnóstico de Arquivo")
    #st.write("Colunas do DataFrame carregado:", df.columns.tolist())
    #st.dataframe(df.head())

    if df.empty:
        st.warning("Nenhuma transação encontrada.")
    else:
        st.session_state.ofx_raw_df = df

        st.subheader("🖊️ Marcação Manual de Pagamentos de Empréstimo")
        if "Marcar_Como_Emprestimo" not in df.columns:
            df["Marcar_Como_Emprestimo"] = False

        df['Valor (R$) - BR'] = df['Valor (R$)'].apply(
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
        colunas_exibir = [col for col in colunas_exibir if col in df.columns]
        df_exibir = df[colunas_exibir].copy()

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

        df['Marcar_Como_Emprestimo'] = edited_df['Marcar_Como_Emprestimo']
        df_marcado = df[df["Marcar_Como_Emprestimo"] == True].copy()
        st.session_state.emprestimos_df = df_marcado

        if not st.session_state.emprestimos_df.empty:
            st.subheader("🔗 Vinculação de Contrato Para Pagamentos")
            contratos_existentes = st.session_state.gerenciador_contratos.listar_contratos()
            for idx, row in st.session_state.emprestimos_df.iterrows():
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

    # Para cada contrato, exibe tabela das transações vinculadas, ordenadas por data
    for contrato_num in st.session_state.emprestimos_df['Contrato'].unique():
        if not contrato_num or contrato_num == "SEM_CONTRATO":
            continue
        st.markdown(f"#### Contrato {contrato_num}")

        df_contrato = st.session_state.emprestimos_df[
            st.session_state.emprestimos_df['Contrato'] == contrato_num
        ].copy()

        # Ordena por data (se a coluna existir)
        if 'Data' in df_contrato.columns:
            df_contrato['Data'] = pd.to_datetime(df_contrato['Data'], errors='coerce')
            df_contrato = df_contrato.sort_values('Data')

        # Define as colunas para exibir na tabela final
        colunas_tabela = [
            'Arquivo', 'Data', 'Valor (R$) - BR', 'Num Doc', 'Tipo', 'Banco', 'Conta', 'Descrição'
        ]
        colunas_tabela = [col for col in colunas_tabela if col in df_contrato.columns]

        st.dataframe(df_contrato[colunas_tabela], use_container_width=True)

with st.expander("📊 Ver todas as transações importadas"):
    if st.session_state.ofx_raw_df is not None:
        st.dataframe(st.session_state.ofx_raw_df, use_container_width=True)
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
st.title("💼 Validador de Pagamentos de Empréstimos")

# ---------------------- Funções Auxiliares ----------------------

def corrigir_ofx_valores(file_obj):
    conteudo = file_obj.read().decode("latin-1", errors="ignore")
    conteudo_corrigido = re.sub(r"<TRNAMT>(-?\d+),(\d+)", r"<TRNAMT>\1.\2", conteudo)
    return io.BytesIO(conteudo_corrigido.encode("latin-1", errors="ignore"))

def carregar_dados_ofx(uploaded_files):
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
    # Remove possíveis duplicidades
    colunas_unicas = ['Data', 'Descrição', 'Valor (R$)', 'Num Doc']
    colunas_unicas = [col for col in colunas_unicas if col in df.columns]
    if colunas_unicas:
        df = df.drop_duplicates(subset=colunas_unicas, keep='first')
    # Padroniza nome da coluna de documento
    if "Num Doc." in df.columns and "Num Doc" not in df.columns:
        df = df.rename(columns={"Num Doc.": "Num Doc"})
    # Recuperar marcações salvas
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
    return df

def salvar_marcacoes(df_marcado):
    os.makedirs(os.path.dirname(CAMINHO_MARCACOES), exist_ok=True)
    colunas_salvar = ["Arquivo", "Data", "Descrição", "Valor (R$)", "Num Doc", "Num Doc."]
    colunas_presentes = [col for col in colunas_salvar if col in df_marcado.columns]
    if not colunas_presentes:
        st.warning("Nenhuma coluna identificadora encontrada para salvar marcações.")
        return
    df_marcado = df_marcado.drop_duplicates(subset=colunas_presentes, keep='first')
    df_marcado[colunas_presentes].drop_duplicates().to_csv(
        CAMINHO_MARCACOES,
        mode='a',
        header=not os.path.exists(CAMINHO_MARCACOES),
        index=False
    )
    st.success("Marcações salvas! Da próxima vez, elas serão recuperadas automaticamente.")

def marcar_emprestimos():
    df = st.session_state.ofx_raw_df.copy()
    st.subheader("📜 Marcação Manual de Pagamentos de Empréstimo")
    modo_visualizacao = st.radio(
        "Escolha o modo de visualização:",
        options=["Editar", "Ordenar"],
        index=1,
        horizontal=True
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filtro_descricao = st.text_input("🔍 Filtrar pela descrição:")
    with col2:
        filtro_datas = st.date_input(
            "📅 Filtrar por data (deixe vazio para não filtrar):", 
            value=[],
            format="DD/MM/YYYY"
        )
    with col3:
        arquivos_disponiveis = df['Arquivo'].unique().tolist()
        arquivos_disponiveis.insert(0, "<Todos>")
        filtro_arquivo = st.selectbox("📄 Filtrar por arquivo:", options=arquivos_disponiveis)
    with col4:
        filtro_valor = st.number_input("💰 Filtrar por valor exato (R$)", value=0.0)

    df_filtrado = df.copy()

    # Filtro por descrição
    if filtro_descricao:
        df_filtrado = df_filtrado[df_filtrado['Descrição'].str.contains(filtro_descricao, case=False, na=False)]
    # Filtro por arquivo
    if filtro_arquivo and filtro_arquivo != "<Todos>":
        df_filtrado = df_filtrado[df_filtrado['Arquivo'] == filtro_arquivo]
    # Filtro por valor exato
    if filtro_valor != 0.0:
        df_filtrado['Valor_Numerico'] = pd.to_numeric(df_filtrado['Valor (R$)'], errors='coerce')
        tolerancia = 0.05
        df_filtrado = df_filtrado[
            (
                (df_filtrado['Valor_Numerico'] >= filtro_valor - tolerancia) &
                (df_filtrado['Valor_Numerico'] <= filtro_valor + tolerancia)
            ) |
            (
                (df_filtrado['Valor_Numerico'] >= -filtro_valor - tolerancia) &
                (df_filtrado['Valor_Numerico'] <= -filtro_valor + tolerancia)
            )
        ].drop(columns=['Valor_Numerico'])
    # Filtro por data
    if filtro_datas:
        df_filtrado['Data'] = pd.to_datetime(df_filtrado['Data'], errors='coerce')
        if isinstance(filtro_datas, tuple):
            start_date, end_date = filtro_datas
            df_filtrado = df_filtrado[
                (df_filtrado['Data'].dt.date >= start_date) &
                (df_filtrado['Data'].dt.date <= end_date)
            ]
        else:
            filtro_data_unica = filtro_datas
            df_filtrado = df_filtrado[df_filtrado['Data'].dt.date == filtro_data_unica]
        df_filtrado['Data'] = df_filtrado['Data'].dt.strftime('%d/%m/%Y')

    # Ordena por data real para garantir exibição correta
    if 'Data' in df_filtrado.columns:
        df_filtrado['Data_dt'] = pd.to_datetime(df_filtrado['Data'], format='%d/%m/%Y', errors='coerce')
        df_filtrado = df_filtrado.sort_values('Data_dt').drop(columns=['Data_dt'])

    df_filtrado['Valor (R$) - BR'] = df_filtrado['Valor (R$)'].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notnull(x) else ""
    )

    colunas_exibir = [
        'Arquivo', 'Data', 'Descrição', 'Valor (R$) - BR', 'Num Doc',
        'Tipo', 'Banco', 'Conta', 'Marcar_Como_Emprestimo'
    ]
    colunas_exibir = [col for col in colunas_exibir if col in df_filtrado.columns]
    df_exibir = df_filtrado[colunas_exibir].copy()

    # Exibição conforme modo escolhido
    if modo_visualizacao == "Editar":
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
        # Atualiza a coluna no DataFrame original
        df_filtrado['Marcar_Como_Emprestimo'] = edited_df['Marcar_Como_Emprestimo']
        df.loc[df_filtrado.index, 'Marcar_Como_Emprestimo'] = df_filtrado['Marcar_Como_Emprestimo']
    else:
        st.dataframe(df_exibir, use_container_width=True)

    df_marcado = df[df["Marcar_Como_Emprestimo"] == True].copy()
    if not df_marcado.empty and 'Contrato' not in df_marcado.columns:
        df_marcado['Contrato'] = ""

    if st.button("💾 Salvar marcações atuais"):
        st.session_state.emprestimos_df = df_marcado
        salvar_marcacoes(df_marcado)

    st.info(f"{len(df_marcado)} pagamentos de empréstimo marcados.")
    return df_marcado

def associar_contratos():
    df = st.session_state.emprestimos_df.copy()
    df_possiveis = df[df['Contrato'].isnull() | (df['Contrato'] == "")]
    if df_possiveis.empty:
        st.info("Todos os lançamentos já foram associados a contratos.")
        return
    st.subheader("🔗 Associar múltiplos lançamentos a um contrato")
    indices_disponiveis = df_possiveis.index.tolist()
    with st.form("associacao_em_lote"):
        selecionados = st.multiselect(
            "Selecione os lançamentos para associar a um contrato:",
            options=indices_disponiveis,
            format_func=lambda x: f"{df_possiveis.loc[x, 'Data']} | {df_possiveis.loc[x, 'Descrição']} | R$ {df_possiveis.loc[x, 'Valor (R$)']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        contratos_existentes = st.session_state.gerenciador_contratos.listar_contratos()
        contrato_escolhido = st.selectbox(
            "Selecione o contrato para associar os lançamentos selecionados:",
            options=["<Novo>"] + contratos_existentes,
            key="contrato_escolhido"
        )
        novo_num = None
        if contrato_escolhido == "<Novo>":
            novo_num = st.text_input("Informe o número do novo contrato:", key="novo_num_lote")
        submitted = st.form_submit_button("Associar contrato")
        if submitted and selecionados:
            if contrato_escolhido != "<Novo>":
                for idx in selecionados:
                    df.at[idx, 'Contrato'] = contrato_escolhido
            elif novo_num:
                for idx in selecionados:
                    df.at[idx, 'Contrato'] = novo_num
            st.session_state.emprestimos_df = df
            st.success(f"{len(selecionados)} lançamentos associados.")

def gerar_resumo_contratos():
    df = st.session_state.emprestimos_df
    if 'Contrato' in df.columns:
        resumo = (
            df.groupby('Contrato')
            .agg(
                Total_Credito=pd.NamedAgg(column='Valor (R$)', aggfunc=lambda x: x[df.loc[x.index, 'Tipo'] == 'Crédito'].sum()),
                Total_Debito=pd.NamedAgg(column='Valor (R$)', aggfunc=lambda x: x[df.loc[x.index, 'Tipo'] == 'Débito'].sum()),
                Qtd_Lancamentos=('Valor (R$)', 'count')
            )
            .reset_index()
        )
        st.subheader("📊 Resumo por Contrato")
        st.dataframe(resumo, use_container_width=True)

def cadastrar_contratos():
    df = st.session_state.emprestimos_df
    contratos_detectados = df['Contrato'].unique()
    st.divider()
    st.subheader("📝 Cadastro de Contratos de Empréstimo")
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

def exibir_transacoes():
    df = st.session_state.emprestimos_df
    st.divider()
    st.subheader("📋 Tabelas de Transações por Contrato")
    for contrato_num in df['Contrato'].unique():
        if not contrato_num or contrato_num == "SEM_CONTRATO":
            continue
        st.markdown(f"#### Contrato {contrato_num}")
        df_contrato = df[df['Contrato'] == contrato_num].copy()
        if 'Data' in df_contrato.columns:
            df_contrato['Data_dt'] = pd.to_datetime(df_contrato['Data'], format='%d/%m/%Y', errors='coerce')
            df_contrato = df_contrato.sort_values('Data_dt').drop(columns=['Data_dt'])
        colunas_tabela = [
            'Arquivo', 'Data', 'Valor (R$) - BR', 'Num Doc', 'Tipo', 'Banco', 'Conta', 'Descrição'
        ]
        colunas_tabela = [col for col in colunas_tabela if col in df_contrato.columns]
        st.dataframe(df_contrato[colunas_tabela], use_container_width=True)

# ---------------------- Relatório Descritivo dos Contratos ----------------------
def gerar_relatorio_contratos():
    st.divider()
    st.subheader("📄 Relatório Descritivo dos Contratos")

    for contrato in st.session_state.gerenciador_contratos.contratos.values():
        data_inicio = contrato.data_primeira_parcela.strftime('%d/%m/%Y')
        data_fim = (contrato.data_primeira_parcela + pd.DateOffset(months=contrato.prazo_meses-1)).strftime('%d/%m/%Y')
        try:
            parcela = contrato.valor_parcela
        except AttributeError:
            valor = contrato.valor_contratado
            taxa = contrato.taxa_juros / 100 if contrato.taxa_juros > 1 else contrato.taxa_juros
            n = contrato.prazo_meses
            parcela = valor * (taxa * (1 + taxa)**n) / ((1 + taxa)**n - 1) if taxa != 0 else valor / n

        st.markdown(f"""
**CONTRATO {contrato.numero_contrato}**

Emissão: {contrato.data_contrato.strftime('%d/%m/%Y')} – Valor: R$ {contrato.valor_contratado:,.2f} – {contrato.tipo_contrato}

Encargos Financeiros: Juros anuais de {contrato.taxa_juros*12:.2f}% / {contrato.taxa_juros:.2f}% ao mês

Forma de pagamento: {contrato.prazo_meses} parcelas de R$ {parcela:,.2f} – {data_inicio} a {data_fim}

Taxa Média: {contrato.taxa_juros:.2f}% ao mês
        """)

# ---------------------- Inicialização de Estado ----------------------
if 'ofx_raw_df' not in st.session_state:
    st.session_state.ofx_raw_df = None
if 'emprestimos_df' not in st.session_state:
    st.session_state.emprestimos_df = None
if 'gerenciador_contratos' not in st.session_state:
    st.session_state.gerenciador_contratos = GerenciadorContratos()

# ---------------------- Fluxo Principal ----------------------

uploaded_files = st.file_uploader(
    "📁 Envie arquivos OFX para análise",
    type=["ofx"],
    accept_multiple_files=True
)

# 1. Upload + leitura OFX → atualiza somente st.session_state.ofx_raw_df
if uploaded_files:
    df = carregar_dados_ofx(uploaded_files)
    if not df.empty:
        st.session_state.ofx_raw_df = df
    else:
        st.warning("Nenhuma transação encontrada.")

# 2. Marcação de empréstimos → cria/atualiza st.session_state.emprestimos_df (filtrado)
if st.session_state.ofx_raw_df is not None:
    st.info("Marque manualmente os pagamentos de empréstimo abaixo e clique em 'Salvar marcações atuais' para persistir a seleção.")
    marcar_emprestimos()

# 3. Associação de lançamentos → altera somente st.session_state.emprestimos_df
if st.session_state.emprestimos_df is not None and not st.session_state.emprestimos_df.empty:
    associar_contratos()

# 4. Cadastro de contratos → usa st.session_state.gerenciador_contratos
if st.session_state.emprestimos_df is not None and not st.session_state.emprestimos_df.empty:
    cadastrar_contratos()

# 5. Relatórios e tabelas → leitura apenas, sem sobrescrever session_state
if st.session_state.emprestimos_df is not None and not st.session_state.emprestimos_df.empty:
    gerar_resumo_contratos()

    exibir_transacoes()
    gerar_relatorio_contratos()

# 6. Exibe todas as transações importadas (apenas leitura)
with st.expander("📑 Ver todas as transações importadas"):
    if st.session_state.ofx_raw_df is not None:
        st.dataframe(st.session_state.ofx_raw_df, use_container_width=True)
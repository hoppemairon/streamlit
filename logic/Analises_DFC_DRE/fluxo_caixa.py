import pandas as pd
import streamlit as st
from datetime import datetime
import io
import os
import plotly.express as px
import plotly.graph_objects as go

def formatar_brl(valor):
    """Formata um valor numérico para o formato brasileiro (R$)"""
    if pd.isna(valor) or valor is None:
        return ""
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)

def calcular_variacao_percentual(valor_atual, valor_anterior):
    """Calcula a variação percentual entre dois valores"""
    if valor_anterior == 0:
        return float('inf') if valor_atual > 0 else float('-inf') if valor_atual < 0 else 0
    return ((valor_atual - valor_anterior) / abs(valor_anterior)) * 100

def exibir_fluxo_caixa(df_transacoes, path_faturamento="./logic/CSVs/faturamentos.csv", path_estoque="./logic/CSVs/estoques.csv"):
    """
    Gera e exibe o fluxo de caixa por categoria e mês a partir das transações categorizadas.
    """
    st.markdown("## 📊 Fluxo de Caixa (por Categoria e Mês)")

    # Verificar se o DataFrame está vazio
    if df_transacoes.empty:
        st.warning("⚠️ Não há transações para gerar o fluxo de caixa.")
        return pd.DataFrame()

    # Verificar se as colunas necessárias existem
    colunas_necessarias = ["Considerar", "Valor (R$)", "Data", "Categoria"]
    colunas_faltantes = [col for col in colunas_necessarias if col not in df_transacoes.columns]

    if colunas_faltantes:
        st.error(f"❌ Colunas necessárias ausentes: {', '.join(colunas_faltantes)}")
        return pd.DataFrame()

    # Criar cópia para não modificar o original
    df_filtrado = df_transacoes.copy()

    # Filtrar apenas transações a considerar
    if "Considerar" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Considerar"].astype(str).str.lower() == "sim"].copy()

    # Converter valores para numérico
    with st.spinner("Processando valores..."):
        try:
            df_filtrado["Valor (R$)"] = pd.to_numeric(
                df_filtrado["Valor (R$)"].astype(str)
                .replace("R$", "", regex=False)
                .replace(".", "", regex=False)
                .replace(",", ".", regex=False)
                .str.strip(),
                errors="coerce"
            )
        except Exception as e:
            st.error(f"❌ Erro ao converter valores: {e}")
            st.dataframe(df_filtrado.head())
            return pd.DataFrame()

    # Converter datas
    with st.spinner("Processando datas..."):
        try:
            for formato in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"]:
                try:
                    df_filtrado["Data"] = pd.to_datetime(df_filtrado["Data"], format=formato, errors="raise")
                    break
                except:
                    continue
            if not pd.api.types.is_datetime64_any_dtype(df_filtrado["Data"]):
                df_filtrado["Data"] = pd.to_datetime(df_filtrado["Data"], errors="coerce")
            df_filtrado = df_filtrado.dropna(subset=["Data"])
            df_filtrado["Mes"] = df_filtrado["Data"].dt.to_period("M").astype(str)
        except Exception as e:
            st.error(f"❌ Erro ao processar datas: {e}")
            st.dataframe(df_filtrado.head())
            return pd.DataFrame()

    # Criar tabela pivô
    with st.spinner("Gerando tabela de fluxo de caixa..."):
        try:
            df_pivot = pd.pivot_table(
                df_filtrado,
                values="Valor (R$)",
                index="Categoria",
                columns="Mes",
                aggfunc="sum",
                fill_value=0
            )
        except Exception as e:
            st.error(f"❌ Erro ao criar tabela pivô: {e}")
            return pd.DataFrame()

    # Carregar plano de contas para ordenação
    try:
        plano = pd.read_csv("./logic/CSVs/plano_de_contas.csv")
        ordem_map = plano.set_index("Categoria")["Ordem"].to_dict()
        tipo_map = plano.set_index("Categoria")["Tipo"].to_dict()
        grupo_map = plano.set_index("Categoria")["Grupo"].to_dict()
    except Exception as e:
        st.warning(f"⚠️ Plano de contas não encontrado ou inválido: {e}")
        ordem_map = {}
        tipo_map = {}
        grupo_map = {}

    # Adicionar colunas de ordenação
    df_pivot["__ordem__"] = df_pivot.index.map(ordem_map).fillna(999)
    df_pivot["__tipo__"] = df_pivot.index.map(tipo_map).fillna("")
    df_pivot["__grupo__"] = df_pivot.index.map(grupo_map).fillna("Outros")
    df_pivot = df_pivot.sort_values("__ordem__")

    # Obter lista de meses
    meses = [col for col in df_pivot.columns if col not in ["__ordem__", "__tipo__", "__grupo__"]]

    if not meses:
        st.warning("⚠️ Não há dados suficientes para gerar o fluxo de caixa.")
        return pd.DataFrame()

    # Calcular totais
    receitas = df_pivot[df_pivot["__tipo__"] == "Crédito"][meses].sum()
    despesas = df_pivot[df_pivot["__tipo__"] == "Débito"][meses].sum()
    resultado = receitas + despesas  # Despesas já são negativas

    # Carregar dados de faturamento
    if os.path.exists(path_faturamento):
        try:
            df_fat = pd.read_csv(path_faturamento)
            linha_fat = df_fat.set_index("Mes").T.reindex(columns=meses).fillna(0)
            linha_fat.index = ["💰 Faturamento Bruto"]
        except Exception as e:
            st.warning(f"⚠️ Erro ao carregar dados de faturamento: {e}")
            linha_fat = pd.DataFrame(0, index=["💰 Faturamento Bruto"], columns=meses)
    else:
        linha_fat = pd.DataFrame(0, index=["💰 Faturamento Bruto"], columns=meses)

    # Carregar dados de estoque
    if os.path.exists(path_estoque):
        try:
            df_estoque = pd.read_csv(path_estoque)
            linha_estoque = df_estoque.set_index("Mes").T.reindex(columns=meses).fillna(0)
            linha_estoque.index = ["📦 Estoque Final"]
        except Exception as e:
            st.warning(f"⚠️ Erro ao carregar dados de estoque: {e}")
            linha_estoque = pd.DataFrame(0, index=["📦 Estoque Final"], columns=meses)
    else:
        linha_estoque = pd.DataFrame(0, index=["📦 Estoque Final"], columns=meses)

    # Separar receitas e despesas
    df_receitas = df_pivot[df_pivot["__tipo__"] == "Crédito"].drop(columns=["__ordem__", "__tipo__", "__grupo__"])
    df_despesas = df_pivot[df_pivot["__tipo__"] == "Débito"].drop(columns=["__ordem__", "__tipo__", "__grupo__"])

    # Criar linhas de divisão
    linha_div_receitas = pd.DataFrame([[None]*len(meses)], index=["🟦 Receitas"], columns=meses)
    linha_div_despesas = pd.DataFrame([[None]*len(meses)], index=["🟥 Despesas"], columns=meses)

    # Criar linhas de totais
    linha_total_receitas = pd.DataFrame([receitas], index=["🔷 Total de Receitas"])
    linha_total_despesas = pd.DataFrame([despesas], index=["🔻 Total de Despesas"])
    linha_resultado = pd.DataFrame([resultado], index=["🏦 Resultado do Período"])

    # Concatenar tudo na ordem
    df_final = pd.concat([
        linha_fat,
        linha_div_receitas,
        df_receitas,
        linha_div_despesas,
        df_despesas,
        linha_total_receitas,
        linha_total_despesas,
        linha_resultado,
        linha_estoque
    ])

    # Calcular variações percentuais mês a mês
    if len(meses) > 1:
        df_variacoes = pd.DataFrame(index=df_final.index, columns=[f"Var. {meses[-1]}" if len(meses) == 2 
                                                                  else f"Var. {meses[-2]}/{meses[-1]}"])
        for idx in df_final.index:
            if idx in ["🟦 Receitas", "🟥 Despesas"] or pd.isna(df_final.loc[idx, meses[-1]]) or pd.isna(df_final.loc[idx, meses[-2]]):
                df_variacoes.loc[idx] = None
            else:
                variacao = calcular_variacao_percentual(df_final.loc[idx, meses[-1]], df_final.loc[idx, meses[-2]])
                df_variacoes.loc[idx] = variacao
        df_variacoes_fmt = df_variacoes.applymap(lambda x: f"{x:+.1f}%" if pd.notnull(x) else "")
        df_final_com_var = pd.concat([df_final, df_variacoes_fmt], axis=1)
    else:
        df_final_com_var = df_final

    # Formatar valores para exibição
    df_formatado = df_final_com_var.copy()
    for col in meses:
        df_formatado[col] = df_formatado[col].apply(lambda x: formatar_brl(x) if pd.notnull(x) else "")

    # Exibir tabela formatada
    st.markdown("### 📋 Tabela de Fluxo de Caixa")
    st.dataframe(df_formatado, use_container_width=True)

    # ---------------------- GRÁFICOS EM ABAS ----------------------
    st.markdown("### 📈 Visualização Gráfica")
    abas = st.tabs([
        "Resultado Mensal",
        "Receitas vs Despesas",
        "Composição de Receitas",
        "Composição de Despesas"
    ])

    # 1. Resultado Mensal
    with abas[0]:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=meses,
            y=resultado.values,
            name="Resultado",
            marker_color=['green' if x >= 0 else 'red' for x in resultado.values]
        ))
        fig.update_layout(
            title="Resultado Mensal",
            xaxis_title="Mês",
            yaxis_title="Valor (R$)",
            template="plotly_white",
            height=500
        )
        fig.add_shape(
            type="line",
            x0=meses[0],
            y0=0,
            x1=meses[-1],
            y1=0,
            line=dict(color="black", width=1, dash="dash")
        )
        for i, valor in enumerate(resultado.values):
            fig.add_annotation(
                x=meses[i],
                y=valor,
                text=formatar_brl(valor),
                showarrow=False,
                yshift=10 if valor >= 0 else -20
            )
        st.plotly_chart(fig, use_container_width=True)

    # 2. Receitas vs Despesas
    with abas[1]:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=meses,
            y=receitas.values,
            name="Receitas",
            marker_color="blue"
        ))
        fig.add_trace(go.Bar(
            x=meses,
            y=abs(despesas.values),
            name="Despesas",
            marker_color="red"
        ))
        fig.update_layout(
            title="Receitas vs Despesas",
            xaxis_title="Mês",
            yaxis_title="Valor (R$)",
            barmode="group",
            template="plotly_white",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

    # 3. Composição de Receitas
    with abas[2]:
        if df_receitas.empty:
            st.info("Não há dados de receitas para exibir.")
        else:
            if "__grupo__" in df_pivot.columns:
                df_receitas_grupo = df_pivot[df_pivot["__tipo__"] == "Crédito"].groupby("__grupo__")[meses].sum()
                fig = px.bar(
                    df_receitas_grupo.T,
                    barmode="stack",
                    title="Composição de Receitas por Grupo",
                    labels={"value": "Valor (R$)", "index": "Mês"},
                    height=500,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_layout(template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            else:
                fig = px.bar(
                    df_receitas.T,
                    barmode="stack",
                    title="Composição de Receitas por Categoria",
                    labels={"value": "Valor (R$)", "index": "Mês"},
                    height=500,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_layout(template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)

    # 4. Composição de Despesas
    with abas[3]:
        if df_despesas.empty:
            st.info("Não há dados de despesas para exibir.")
        else:
            if "__grupo__" in df_pivot.columns:
                df_despesas_grupo = df_pivot[df_pivot["__tipo__"] == "Débito"].groupby("__grupo__")[meses].sum()
                df_despesas_grupo_abs = df_despesas_grupo.abs()
                fig = px.bar(
                    df_despesas_grupo_abs.T,
                    barmode="stack",
                    title="Composição de Despesas por Grupo",
                    labels={"value": "Valor (R$)", "index": "Mês"},
                    height=500,
                    color_discrete_sequence=px.colors.qualitative.Set1
                )
                fig.update_layout(template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            else:
                df_despesas_abs = df_despesas.abs()
                fig = px.bar(
                    df_despesas_abs.T,
                    barmode="stack",
                    title="Composição de Despesas por Categoria",
                    labels={"value": "Valor (R$)", "index": "Mês"},
                    height=500,
                    color_discrete_sequence=px.colors.qualitative.Set1
                )
                fig.update_layout(template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
    # ---------------------- FIM DAS ABAS ----------------------

    # Opções de download
    st.markdown("### 📥 Download dos Dados")
    col1, col2 = st.columns(2)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_formatado.to_excel(writer, sheet_name="Fluxo de Caixa")
        df_final.to_excel(writer, sheet_name="Dados Numéricos")
        df_filtrado.to_excel(writer, sheet_name="Transações Detalhadas", index=False)
    output.seek(0)

    col1.download_button(
        label="📄 Baixar Fluxo de Caixa (Excel)",
        data=output,
        file_name=f"fluxo_caixa_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if col2.button("💾 Salvar na pasta do sistema"):
        try:
            df_formatado.to_excel("./logic/CSVS/transacoes_categorizadas.xlsx", index=True)
            df_final.to_excel("./logic/CSVs/transacoes_numericas.xlsx", index=True)
            col2.success("✅ Arquivos salvos com sucesso!")
        except Exception as e:
            col2.error(f"❌ Erro ao salvar arquivos: {e}")

    return df_final
import os
import streamlit as st
import openai
from dotenv import load_dotenv

load_dotenv()

# Configura a chave da API
openai.api_key = os.getenv("OPENAI_API_KEY")

def preparar_fluxo_para_prompt(df_fluxo, max_linhas=50):
    if df_fluxo is None or df_fluxo.empty:
        return "Fluxo de caixa indisponível."
    
    # Se houver muitas linhas, pega só as últimas N linhas
    if len(df_fluxo) > max_linhas:
        df_fluxo = df_fluxo.tail(max_linhas)

    # Formatar como uma tabela mais compacta
    texto_fluxo = df_fluxo.to_markdown(index=False)
    return texto_fluxo

def analisar_dfs_com_gpt(df_dre, df_fluxo, descricao_empresa):
    # Ajusta se vier como tuple (erro comum em Streamlit file_uploader)
    if isinstance(df_dre, tuple):
        df_dre = df_dre[0]
    if isinstance(df_fluxo, tuple):
        df_fluxo = df_fluxo[0]

    # Converte os DataFrames para texto
    texto_dre = df_dre.to_string(index=False) if df_dre is not None else "DRE indisponível."
    texto_fluxo = preparar_fluxo_para_prompt(df_fluxo)

    # Prepara o prompt
    prompt = f"""
    Você é um analista financeiro. Com base nas informações a seguir, gere um parecer financeiro completo, identifique pontos positivos, negativos, tendências e sugestões de melhorias.

    Descrição da Empresa:
    {descricao_empresa}

    Fluxo de Caixa:
    {texto_fluxo}
    
    Demonstrativo de Resultados (DRE):
    {texto_dre}

    Siga uma estrutura organizada:
    1. Introdução sobre o contexto da empresa
    2. Pontos Positivos
    3. Pontos Negativos
    4. Tendências observadas
    5. Sugestões de Melhorias
    """

    placeholder = st.empty()
    full_response = ""

    try:
        # Faz a chamada OpenAI com streaming
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "Você é um analista financeiro especializado."},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )

        # Atualiza dinamicamente
        for chunk in response:
            if "choices" in chunk and chunk.choices[0].delta.get("content"):
                content = chunk.choices[0].delta.content
                full_response += content
                placeholder.markdown(full_response)

    except Exception as e:
        st.error(f"Erro ao gerar análise financeira: {e}")
        full_response = f"Erro: {str(e)}"

    return full_response

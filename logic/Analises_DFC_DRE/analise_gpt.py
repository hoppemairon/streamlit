import os
import streamlit as st
import openai
from dotenv import load_dotenv
import pandas as pd

# Carrega variáveis de ambiente
load_dotenv()

# Cria o client da nova API
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def preparar_fluxo_para_prompt(df_fluxo, max_linhas=50):
    if df_fluxo is None or df_fluxo.empty:
        return "Fluxo de caixa indisponível."
    if len(df_fluxo) > max_linhas:
        df_fluxo = df_fluxo.tail(max_linhas)
    return df_fluxo.to_markdown(index=False)

def preparar_dre_para_prompt(df_dre, max_linhas=50):
    if df_dre is None or df_dre.empty:
        return "DRE indisponível."
    if len(df_dre) > max_linhas:
        df_dre = df_dre.tail(max_linhas)
    return df_dre.to_markdown(index=False)

def analisar_dfs_com_gpt(df_dre, df_fluxo, descricao_empresa, modelo="gpt-4-turbo", temperatura=0.2):
    if isinstance(df_dre, tuple): df_dre = df_dre[0]
    if isinstance(df_fluxo, tuple): df_fluxo = df_fluxo[0]

    texto_dre = preparar_dre_para_prompt(df_dre)
    texto_fluxo = preparar_fluxo_para_prompt(df_fluxo)

    prompt = f"""
Você é um analista financeiro sênior. Analise os dados a seguir e gere um parecer consultivo, claro e detalhado para gestores e sócios. Use linguagem acessível, destaque oportunidades e riscos, e traga sugestões práticas.

**Descrição da Empresa:**
{descricao_empresa}

**Fluxo de Caixa (últimos meses):**
{texto_fluxo}

**Demonstrativo de Resultados (DRE):**
{texto_dre}

Siga esta estrutura:
1. Breve introdução contextualizando a empresa e o cenário.
2. Pontos positivos (com exemplos dos dados).
3. Pontos de atenção/negativos (com exemplos dos dados).
4. Tendências e alertas (com base em evolução dos números).
5. Sugestões práticas de melhoria e próximos passos.
6. Finalize com um resumo executivo de até 3 linhas.

Seja objetivo, evite jargões técnicos excessivos e use listas sempre que possível.
"""

    with st.spinner("🔎 Gerando análise financeira personalizada com IA..."):
        placeholder = st.empty()
        full_response = ""
        try:
            # Chamada com streaming usando a nova API
            stream = client.chat.completions.create(
                model=modelo,
                messages=[
                    {"role": "system", "content": "Você é um analista financeiro consultivo, claro e didático."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperatura,
                max_tokens=1200,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    placeholder.markdown(full_response)
        except Exception as e:
            st.error(f"Erro ao gerar análise financeira: {e}")
            full_response = f"Erro: {str(e)}"
    # Botão para baixar análise
    if full_response and len(full_response) > 20:
        st.markdown("---")
        st.code(full_response, language="markdown")
        st.download_button(
            "📥 Baixar análise em TXT",
            data=full_response,
            file_name="parecer_financeiro.txt",
            mime="text/plain"
        )
    return full_response

# Exemplo de uso:
# parecer = analisar_dfs_com_gpt(df_dre, df_fluxo, "Empresa de tecnologia focada em SaaS B2B.")
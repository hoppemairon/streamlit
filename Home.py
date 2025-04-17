
import streamlit as st

st.set_page_config(page_title="Início - Projeto Bancário", layout="centered")

st.title("🏠 Página Inicial")
st.markdown("""
Bem-vindo ao sistema de leitura e correção de arquivos bancários.

Selecione uma das páginas no menu lateral:

- 📄 **Retorno Bancário**: Para processar arquivos `.RET` CNAB240
- 💸 **Leitura de Arquivos OFX**: Para extrair e corrigir lançamentos OFX
""")

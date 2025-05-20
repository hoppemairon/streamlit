import streamlit as st

# Configuração da página
st.set_page_config(page_title="Sistema Bancário MR", layout="wide")

# Inicializa a página atual
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'Home'

# Função para definir a página atual
def set_page(page_name):
    st.session_state['current_page'] = page_name

# Páginas do sistema
def home():
    st.title("💼 Painel Principal - Sistema Bancário MR")
    st.markdown("""
    ## Bem-vindo ao Sistema Bancário MR

    Este sistema foi desenvolvido para facilitar o processamento de arquivos bancários, integrando CNAB240, OFX e APIs externas como Netunna e Argo.

    **Navegue pelo menu lateral para explorar as funcionalidades disponíveis.**

    ### Funcionalidades Principais:
    - **Dados Netunna e Argo:** Integração e comparação de dados externos.

    ### Atualizações:
    - **Versão 1.0** • Última atualização: 20/05/2025
    """)

home()
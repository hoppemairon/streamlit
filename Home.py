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
    - **Pré Análise:** Ferramentas para análise preliminar de dados OFX.
    - **Leitura de Arquivos OFX:** Importação e extração de arquivos OFX.
    - **Retorno Bancário:** Processamento e análise de retornos bancários.
    - **Plano de Contas:** Gestão e organização de planos de contas para a Pré Análise.
    - **Palavras Chaves:** Configuração de palavras-chave para categorização para a Pré Análise.
    - **Análise de Empréstimos:** Avaliação de empréstimos.
    - **Dados Netunna e Argo:** Integração e comparação de dados externos.

    ### Atualizações:
    - **Versão 2.0** • Última atualização: 14/05/2025
    """)

home()
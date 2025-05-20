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
        st.title("📊 Comparador de Vendas entre Netunna e Argo")

        st.markdown("""
        ## Bem-vindo ao sistema de comparação entre APIs da Netunna e Argo

        Esta aplicação foi desenvolvida para simplificar a integração, análise e validação de dados provenientes das plataformas **Netunna** e **Argo**.

        Utilize o **menu lateral** para acessar as diferentes funcionalidades disponíveis no sistema.

        ---

        ### 🔧 Funcionalidades Principais:
        - **Busca via API:** Consulte e carregue dados diretamente das APIs da Netunna e Argo.
        - **Comparativo de Transações:** Identifique diferenças e conciliação de vendas entre os sistemas.
        - **Validação Manual:** Revise transações pendentes com opções de correção e justificativa.

        ---

        ### 🆕 Últimas Atualizações:
        - Simulação de barra de progresso por dia nas requisições da Netunna e Argo.
        - Tradução automática dos IDs de bandeiras da Netunna para nomes amigáveis.
        - Melhorias na interface para acompanhamento do processo de carregamento.

                    
        - **Versão 1.0** • Desenvolvedor: Mairon Hoppe • Última atualização: 20/05/2025
        """)
    ### Atualizações:

home()
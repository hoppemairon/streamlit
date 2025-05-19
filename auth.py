import streamlit as st
import streamlit_authenticator as stauth

# Configuração dos usuários
names = ["Usuário1", "Usuário2"]
usernames = ["usuario1", "usuario2"]
passwords = ["senha1", "senha2"]  # Use hashes para senhas em produção

# Permissões
permissions = {
    "usuario1": [
        "1_Pré_Analise",
        "2_Comparador_Argo_Netunna",
        "3_Mapeamento_Operadoras",
        "4_Conversor_OFX",
        "5_Retorno_Pgto_Banrisul"
    ],
    "usuario2": [
        "6_Plano_de_Contas",
        "7_Palavras_Chaves",
        "8_Análise_de_Empréstimos",
        "9_Dados_Netunna",
        "10_Dados_Argo",
        "11_Comparativo_API_Netunna_Argo"
    ]
}

# Função para autenticar
def authenticate():
    authenticator = stauth.Authenticate(names, usernames, passwords, "cookie_name", "signature_key", cookie_expiry_days=30)
    name, authentication_status, username = authenticator.login("Login", "main")
    return name, authentication_status, username, permissions
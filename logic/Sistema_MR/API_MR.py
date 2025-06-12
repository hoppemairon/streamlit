import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

api_url = os.getenv("API_MR_URL")
chave_api = os.getenv("API_MR_KEY")

def buscar_lancamentos_api(ids_empresa: str, anos: str = "2025") -> pd.DataFrame:
    headers = {
        "Content-Type": "application/json",
        "mr-key": chave_api
    }

    todos_dados = []

    for id_empresa in ids_empresa.split(","):
        url = f"{api_url}/api/export/lancamentos/{id_empresa}?anos={anos}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            try:
                json_response = response.json()
                if isinstance(json_response, dict) and "result" in json_response:
                    dados = json_response["result"]
                    if isinstance(dados, list):
                        df_parcial = pd.json_normalize(dados)
                        todos_dados.append(df_parcial)
                else:
                    print(f"⚠️ Estrutura inesperada: {json_response}")
            except Exception as e:
                print(f"❌ Erro ao processar JSON da empresa {id_empresa}: {e}")
        else:
            print(f"❌ Erro HTTP {response.status_code} para empresa {id_empresa}: {response.text}")

    return pd.concat(todos_dados, ignore_index=True) if todos_dados else pd.DataFrame()
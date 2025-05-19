import pandas as pd
from extractors.utils import normalizar_descricao

def remover_duplicatas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove linhas duplicadas com base em Data, Descrição e Valor (R$), se essas colunas existirem.
    """
    colunas_necessarias = {"Data", "Descrição", "Valor (R$)"}
    if not colunas_necessarias.issubset(set(df.columns)):
        return df  # Retorna sem modificar se não tiver colunas esperadas

    df["__desc"] = df["Descrição"].apply(normalizar_descricao)
    df["__valor"] = df["Valor (R$)"].astype(float).round(2)
    df["__chave"] = (
        df["Data"].astype(str).str.strip() +
        df["__desc"] +
        df["__valor"].astype(str)
    )

    df_final = df.drop_duplicates(subset="__chave").drop(columns=["__chave", "__desc", "__valor"])
    return df_final
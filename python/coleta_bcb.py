import requests
import pandas as pd
from sqlalchemy import create_engine

# Séries mensais do Ipeadata
SERIES = {
    "ipca_mensal": "PRECOS12_IPCAG12",   # IPCA, variação % no mês
    "selic_mensal": "BM12_TJOVER12",     # Selic, % ao mês
    "dolar_venda": "BM12_ERC12",         # Dólar comercial, venda, média do mês (R$)
}
INICIO = pd.Timestamp.today() - pd.DateOffset(years=9)

def baixar_serie(nome, codigo):
    url = f"http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{codigo}')"
    resposta = requests.get(url, timeout=60)
    resposta.raise_for_status()
    df = pd.DataFrame(resposta.json()["value"])[["VALDATA", "VALVALOR"]]
    df.columns = ["data", "valor"]
    df["data"] = pd.to_datetime(df["data"].str[:10])
    df = df[df["data"] >= INICIO].dropna()
    df["indicador"] = nome
    return df

engine = create_engine(
    "mssql+pyodbc://@localhost/Indicadores"
    "?driver=ODBC+Driver+18+for+SQL+Server"
    "&trusted_connection=yes&TrustServerCertificate=yes"
)

dados = pd.concat([baixar_serie(n, c) for n, c in SERIES.items()])
dados.to_sql("indicadores", engine, if_exists="replace", index=False)
print(f"{len(dados)} linhas gravadas em dbo.indicadores")

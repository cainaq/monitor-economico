Monitor de Indicadores Econômicos

Pipeline de coleta e análise de indicadores econômicos brasileiros (IPCA, Selic e dólar), com coleta automatizada em Python, armazenamento e cálculos em SQL Server e visualização em Power BI (em desenvolvimento).

Este é o segundo projeto do meu portfólio de transição para a área de Análise de Dados. O primeiro, Despesas Públicas Federais, foca em SQL e Power BI; este acrescenta Python e consumo de APIs.

Período coberto: nov/2017 a set/2026 · séries mensais.

Objetivo

Acompanhar a relação entre inflação, juros e câmbio e responder:

Qual a inflação acumulada em 12 meses (IPCA 12m) e como ela evoluiu?
Qual o juro real (Selic descontada da inflação) ao longo do tempo?
Como o dólar se comportou no período?
Habilidades demonstradas
Área	O que foi aplicado
Python	Consumo de API com requests, tratamento com pandas, gravação no SQL Server com SQLAlchemy + pyodbc
SQL	Pivotamento com MAX(CASE WHEN ...), funções de janela (OVER, ROWS BETWEEN), acumulado de taxas com EXP(SUM(LOG(...))), CTE, views
Qualidade de dados	Exclusão do mês em andamento, acumulados calculados só com 12 meses completos, validação contra a fonte original
Resolução de problemas	Migração da fonte de dados quando a API original ficou indisponível
Fonte dos dados

Os dados vêm da API do Ipeadata (Instituto de Pesquisa Econômica Aplicada), que republica as séries oficiais:

Indicador	Código Ipeadata	Unidade
IPCA – variação mensal	PRECOS12_IPCAG12	% no mês
Selic – taxa mensal	BM12_TJOVER12	% no mês
Dólar comercial – venda, média do mês	BM12_ERC12	R$

Por que Ipeadata e não o Banco Central? O projeto foi planejado para usar a API SGS do Banco Central. Durante o desenvolvimento, ela ficou inacessível (o domínio não era encontrado nem pela rede móvel). Migrei a coleta para o Ipeadata e conferi que os valores mensais do IPCA são idênticos aos que a API do Banco Central publicava. Detalhes em docs/problemas_e_solucoes.md.

Estrutura do repositório
monitor-indicadores-economicos/
├── README.md
├── requirements.txt
├── .gitignore
├── python/
│   └── coleta_bcb.py
├── sql/
│   ├── 01_criar_banco.sql
│   └── 02_criar_views.sql
└── docs/
    └── problemas_e_solucoes.md
Pipeline passo a passo
Etapa 1 — Criar o banco

sql/01_criar_banco.sql

sql
IF DB_ID('Indicadores') IS NULL
    CREATE DATABASE Indicadores;
GO
Etapa 2 — Coleta em Python

python/coleta_bcb.py

O script consulta a API do Ipeadata para cada série, mantém os últimos 9 anos, padroniza as colunas (data, valor, indicador) e grava tudo na tabela dbo.indicadores.

Resultado: 321 linhas (cerca de 107 meses por indicador).

Etapa 3 — Views de análise

sql/02_criar_views.sql

vw_indicadores_mensais — uma linha por mês, com IPCA, Selic e dólar lado a lado. Descarta o mês em andamento, que ainda está incompleto.
vw_indicadores_12m — calcula, com funções de janela:
IPCA 12m e Selic 12m: taxas acumuladas nos últimos 12 meses. Como taxas se acumulam multiplicando (1 + taxa), o cálculo usa EXP(SUM(LOG(1 + taxa))).
Juro real 12m: (1 + Selic 12m) / (1 + IPCA 12m) − 1.
Os acumulados só aparecem quando há 12 meses completos; caso contrário, ficam vazios em vez de mostrar um valor errado.
Como rodar
Instale as bibliotecas:
bash
   pip install -r requirements.txt

É necessário ter o ODBC Driver 18 for SQL Server instalado.

No SQL Server Management Studio (SSMS), execute sql/01_criar_banco.sql.
Rode a coleta:
bash
   python python/coleta_bcb.py
Execute sql/02_criar_views.sql.
Consulte o resultado:
sql
   SELECT TOP 12 * FROM dbo.vw_indicadores_12m ORDER BY mes DESC;
Resultados

Último mês com todos os indicadores disponíveis: agosto/2026.

Indicador	Valor
IPCA acumulado em 12 meses	4,22%
Selic acumulada em 12 meses	14,63%
Juro real (12 meses)	9,98%
Dólar (média de agosto)	R$ 5,15
Principais conclusões
Com a Selic acumulada em 14,63% e a inflação em 4,22%, o juro real ficou perto de 10% ao ano em agosto/2026.
[Conclusão sobre a evolução do IPCA 12m ao longo do período — preencher com o dashboard]
[Conclusão sobre o dólar — preencher com o dashboard]
Próximos passos
 Power BI + DAX — dashboard com IPCA 12m × Selic 12m, juro real por ano e evolução do dólar.
 Power Automate — fluxo que roda a coleta e envia alerta por e-mail quando o IPCA 12m passa do teto da meta.
 Carga incremental — gravar apenas os meses novos, em vez de recriar a tabela a cada execução.
Referências
Ipeadata
Documentação OVER (funções de janela) — Microsoft
pandas to_sql
Autor

Cainã Queiroz Silva — em transição para Análise de Dados.

GitHub: @cainaq
LinkedIn: linkedin.com/in/seu-usuario
Licença

Este projeto está sob a licença MIT. Consulte o arquivo LICENSE para mais detalhes.

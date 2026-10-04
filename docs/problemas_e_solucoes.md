**Problemas e soluções**

Registro dos problemas encontrados durante a construção do Monitor de Indicadores Econômicos e de como cada um foi resolvido.

**1. API do Banco Central inacessível**

**Problema**: o projeto foi planejado para coletar os dados da API SGS do Banco Central (api.bcb.gov.br). Ao rodar o script de coleta, a requisição falhou antes de chegar ao servidor:

NameResolutionError: Failed to resolve 'api.bcb.gov.br'

**Diagnóstico**: o erro indicava que o computador não conseguia encontrar o endereço do site. Testei as causas possíveis, da mais simples para a mais ampla:

**Teste	Resultado	Conclusão**
nslookup api.bcb.gov.br (DNS do roteador)	Domínio inexistente	Poderia ser falha do DNS local
nslookup api.bcb.gov.br 8.8.8.8 (DNS do Google)	Domínio inexistente	Não era o roteador
Cabeçalho User-Agent de navegador no requests	Mesmo erro	Não era bloqueio por identificação do script
Acesso pelo celular, na rede 5G	Site não encontrado	Não era a minha rede

Ao acessar o site do Banco Central pelo navegador, também recebi uma mensagem de requisição rejeitada pelo firewall da instituição.

**Solução**: como o problema estava na fonte e não no meu ambiente, migrei a coleta para a API do Ipeadata, que republica as mesmas séries oficiais:

Indicador	Série no Banco Central (SGS)	Série no Ipeadata
IPCA mensal	433	PRECOS12_IPCAG12
Selic	432 (meta, % a.a.)	BM12_TJOVER12 (% a.m.)
Dólar comercial, venda	1 (diária)	BM12_ERC12 (média mensal)

**Validação**: comparei os valores mensais do IPCA do Ipeadata com os que a API do Banco Central publicava antes de ficar fora do ar. Junho (0,16%), julho (0,07%) e agosto de 2026 (-0,32%) são idênticos nas duas fontes.

**Aprendizado**: antes de mexer no código, vale isolar onde está o problema (meu computador, minha rede ou a fonte). E um pipeline de dados precisa ter uma fonte alternativa em mente quando depende de um serviço externo.

**2. Séries com datas de término diferentes**

**Problema**: depois da carga, cada indicador terminava num mês diferente:

Indicador	Último mês
IPCA	agosto/2026
Dólar	setembro/2026
Selic	outubro/2026

**Causa**:

O IBGE divulga o IPCA de cada mês só por volta do dia 10 do mês seguinte.
A Selic de outubro/2026 já aparecia, mas com poucos dias: o mês ainda estava em andamento.

**Solução**:

A view vw_indicadores_mensais descarta o mês em andamento:
sql
  WHERE data < DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
Meses sem IPCA ficam com valor vazio (NULL), em vez de serem excluídos, para não perder os dados de Selic e dólar daquele mês.
**3. Acumular taxas: somar ou multiplicar?**

**Problema**: para calcular a inflação acumulada em 12 meses, somar as taxas mensais dá um resultado errado, porque taxas se acumulam de forma composta. Uma inflação de 1% em dois meses seguidos não dá 2%, e sim 2,01%.

**Solução**: o acumulado é o produto de (1 + taxa) de cada mês. Como o SQL Server não tem uma função de produto, usei a propriedade do logaritmo (o log de um produto é a soma dos logs):

sql
EXP(SUM(LOG(1 + ipca_mes / 100))
    OVER (ORDER BY mes ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)) - 1

A cláusula ROWS BETWEEN 11 PRECEDING AND CURRENT ROW define a janela: o mês atual e os 11 anteriores.

**4. Acumulados com menos de 12 meses**

**Problema:** a função de janela calcula o acumulado mesmo quando a janela tem menos de 12 meses, como nos primeiros meses da série ou quando falta um IPCA. Isso gerava valores que pareciam corretos, mas não eram acumulados de 12 meses.

**Solução**: contei quantos meses com valor existem em cada janela e só exibi o acumulado quando são exatamente 12:

sql
COUNT(ipca_mes) OVER (ORDER BY mes ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS meses_ipca
...
CASE WHEN meses_ipca = 12 THEN ipca_12m_fator * 100 END AS ipca_12m

Nos outros casos, o resultado fica vazio em vez de mostrar um número errado.

**5. Selic em % ao mês**

Problema: no Ipeadata, a Selic vem em % ao mês, e não em % ao ano, como a meta definida pelo Copom. Comparar diretamente com a inflação de 12 meses não faria sentido.

Solução: calculei a Selic acumulada em 12 meses com o mesmo método do IPCA. Assim os dois indicadores ficam na mesma base, e o juro real pode ser calculado:

sql
((1 + selic_12m_fator) / (1 + ipca_12m_fator) - 1) * 100 AS juro_real_12m
6. Organização dos bancos de dados

Decisão: cada projeto do portfólio tem o próprio banco de dados (Transparencia no primeiro projeto, Indicadores neste). Assim as tabelas e views de um projeto não se misturam com as do outro, e cada repositório pode ser recriado do zero de forma independente.

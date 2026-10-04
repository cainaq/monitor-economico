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

**Ao acessar o site do Banco Central pelo navegador, também recebi uma mensagem de requisição rejeitada pelo firewall da instituição.**

**Solução**: como o problema estava na fonte e não no meu ambiente, migrei a coleta para a API do Ipeadata, que republica as mesmas séries oficiais:

Indicador	Série no Banco Central (SGS)	Série no Ipeadata
IPCA mensal	433	PRECOS12_IPCAG12
Selic	432 (meta, % a.a.)	BM12_TJOVER12 (% a.m.)
Dólar comercial, venda	1 (diária)	BM12_ERC12 (média mensal)

**Validação**: comparei os valores mensais do IPCA do Ipeadata com os que a API do Banco Central publicava antes de ficar fora do ar. Junho (0,16%), julho (0,07%) e agosto de 2026 (-0,32%) são idênticos nas duas fontes.

**Aprendizado:** antes de mexer no código, vale isolar onde está o problema (meu computador, minha rede ou a fonte). E um pipeline de dados precisa ter uma fonte alternativa em mente quando depende de um serviço externo.

**2. Séries com datas de término diferentes**

**Problema:** depois da carga, cada indicador terminava num mês diferente:

Indicador	Último mês
IPCA	agosto/2026
Dólar	setembro/2026
Selic	outubro/2026

**Causa:**

O IBGE divulga o IPCA de cada mês só por volta do dia 10 do mês seguinte.
A Selic de outubro/2026 já aparecia, mas com poucos dias: o mês ainda estava em andamento.

**Solução:**

A view vw_indicadores_mensais descarta o mês em andamento:
sql
  WHERE data < DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
Meses sem IPCA ficam com valor vazio (NULL), em vez de serem excluídos, para não perder os dados de Selic e dólar daquele mês.
**3. Acumular taxas: somar ou multiplicar?**

**Problema**: para calcular a inflação acumulada em 12 meses, somar as taxas mensais dá um resultado errado, porque taxas se acumulam de forma composta. Uma inflação de 1% em dois meses seguidos não dá 2%, e sim 2,01%.

**Solução:** o acumulado é o produto de (1 + taxa) de cada mês. Como o SQL Server não tem uma função de produto, usei a propriedade do logaritmo (o log de um produto é a soma dos logs):

sql
EXP(SUM(LOG(1 + ipca_mes / 100))
    OVER (ORDER BY mes ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)) - 1

A cláusula ROWS BETWEEN 11 PRECEDING AND CURRENT ROW define a janela: o mês atual e os 11 anteriores.

**4. Acumulados com menos de 12 meses**

**Problema:** a função de janela calcula o acumulado mesmo quando a janela tem menos de 12 meses, como nos primeiros meses da série ou quando falta um IPCA. Isso gerava valores que pareciam corretos, mas não eram acumulados de 12 meses.

Solução: contei quantos meses com valor existem em cada janela e só exibi o acumulado quando são exatamente 12:

sql
COUNT(ipca_mes) OVER (ORDER BY mes ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS meses_ipca
...
CASE WHEN meses_ipca = 12 THEN ipca_12m_fator * 100 END AS ipca_12m

Nos outros casos, o resultado fica vazio em vez de mostrar um número errado.

**5. Selic em % ao mês**

**Problema:** no Ipeadata, a Selic vem em % ao mês, e não em % ao ano, como a meta definida pelo Copom. Comparar diretamente com a inflação de 12 meses não faria sentido.

**Solução**: calculei a Selic acumulada em 12 meses com o mesmo método do IPCA. Assim os dois indicadores ficam na mesma base, e o juro real pode ser calculado:

sql
((1 + selic_12m_fator) / (1 + ipca_12m_fator) - 1) * 100 AS juro_real_12m
**6. Organização dos bancos de dados**

Decisão: cada projeto do portfólio tem o próprio banco de dados (Transparencia no primeiro projeto, Indicadores neste). Assim as tabelas e views de um projeto não se misturam com as do outro, e cada repositório pode ser recriado do zero de forma independente.

**7. Power Automate não conectava ao SQL Server**

**Problema:** a ação Abrir conexão SQL do Power Automate Desktop falhava com a mensagem:

[DBNETLIB][ConnectionOpen (Connect()).]SQL Server inexistente ou acesso negado.

O SSMS e o script Python conectavam normalmente ao mesmo servidor.

**Causa:** o provedor SQLOLEDB, usado pelo Power Automate, é um provedor antigo do Windows que se conecta pelo protocolo TCP/IP. Na instalação padrão do SQL Server 2025 Developer, esse protocolo vem desabilitado. O SSMS e o Python funcionavam porque usam outro meio de conexão local.

Tentativa que não funcionou: usar o mesmo driver do Python (ODBC Driver 18) por meio do provedor MSDASQL. O Power Automate só aceita provedores OLE DB e bloqueia essa "ponte" para ODBC.

**Solução:** habilitar o TCP/IP no SQL Server:

SQL Server 2025 Configuration Manager → Configuração de Rede do SQL Server → Protocolos para MSSQLSERVER.
TCP/IP → Habilitar.
Reiniciar o serviço SQL Server (MSSQLSERVER).

Cadeia de conexão usada no fluxo:

Provider=SQLOLEDB;Data Source=localhost;Initial Catalog=Indicadores;Integrated Security=SSPI;

Habilitar o TCP/IP não expõe o banco para a rede: sem liberar a porta no firewall do Windows, só o próprio computador consegue se conectar.

**8. Erro de sintaxe com o símbolo % no Power Automate**

**Problema:** a mensagem de alerta IPCA de %QueryResult[0]['ipca_12m']%, acima do teto de 4,5% gerava erro de sintaxe.

**Causa:** no Power Automate, o símbolo % marca o início e o fim de uma variável. O % sozinho em "4,5%" era interpretado como o início de uma variável que nunca terminava.

**Solução:** retirei o símbolo do texto fixo ("4,5 por cento"). Outra opção seria escrever %%, que o Power Automate exibe como um único %.

Também arredondei o IPCA na própria consulta SQL, para o e-mail mostrar 4,22 em vez de 4,22345273706826:

sql
SELECT TOP 1 mes, ROUND(ipca_12m, 2) AS ipca_12m
FROM dbo.vw_indicadores_12m
WHERE ipca_12m IS NOT NULL
ORDER BY mes DESC;
**9. Instabilidade do Ipeadata**

**Problema:** em alguns momentos, a API do Ipeadata não respondia e o script falhava com:

ConnectTimeout: Connection to www.ipeadata.gov.br timed out.

O teste pela rede móvel mostrou que, em alguns horários, o problema era da minha rede; em outros, do próprio Ipeadata, que não respondia em nenhuma rede.

**Solução:** o script passou a fazer até 3 tentativas, com espera crescente entre elas (10 e 20 segundos), antes de desistir:

python
def requisitar_com_tentativas(url, tentativas=3, espera=10):
    for i in range(1, tentativas + 1):
        try:
            resposta = requests.get(url, timeout=60)
            resposta.raise_for_status()
            return resposta
        except requests.RequestException as erro:
            print(f"Tentativa {i} falhou: {erro}")
            if i == tentativas:
                raise
            time.sleep(espera * i)

Também passei a usar https:// no endereço da API.

Proteção dos dados: o script só grava no SQL Server depois de baixar todas as séries. Se a coleta falhar no meio, a tabela continua com os dados da última coleta bem-sucedida, em vez de ficar vazia ou incompleta.

**10. Detectar falha na coleta dentro do Power Automate**

**Problema:** o Power Automate rodava o script Python e seguia para as próximas etapas mesmo quando a coleta falhava. Nesse caso, o fluxo consultava o banco e enviava o e-mail com dados antigos, sem avisar que algo tinha dado errado.

Diagnóstico: a ação Executar aplicativo guarda o código de saída do Python na variável %AppExitCode%:

Código	Significado
0	Script terminou com sucesso
1	Script deu erro durante a execução (ex.: falha de conexão com a API)
2	Python não encontrou o arquivo do script

Foi esse código que revelou dois problemas durante os testes: um caminho de arquivo errado (código 2) e a instabilidade do Ipeadata (código 1).

Solução: logo depois de rodar o script, o fluxo verifica o código:

IF AppExitCode <> 0 THEN
    (aviso de falha na coleta)
    EXIT
END

Se a coleta falhar, o fluxo avisa e encerra, sem consultar o banco nem enviar o e-mail com dados desatualizados.

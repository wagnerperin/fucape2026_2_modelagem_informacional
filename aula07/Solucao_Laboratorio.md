# Guia do Professor & Resolução Comentada — Laboratório Aula 07

**FUCAPE Business School**  
**Curso:** Graduação em Ciência de Dados para Negócios  
**Disciplina:** Modelagem Informacional  
**Professor:** Prof. Dr. Wagner Perin  
**Tema:** Integração de Dados, Paradigmas ETL vs. ELT, `dbt` e Orquestração Idempotente com Apache Airflow  

---

## 1. Visão Geral & Racional Pedagógico (PBL / Conflito Cognitivo)

Este laboratório foi concebido para que os estudantes desenvolvam **competências de confiabilidade de engenharia de dados (*Data Reliability Engineering*)** antes de aprenderem ferramentas modernas. A didática baseia-se no princípio de que:
> *"O estudante só valoriza verdadeiramente a elegância e o rigor do dbt e do Airflow depois de experimentar o atrito e a dor financeira de um pipeline legado que quebra por Rate Limit e corrompe o balanço contábil ao ser reexecutado."*

### Objetivos Pedagógicos Específicos:
1. **Conflito Cognitivo:** Testar empiricamente a quebra de um pipeline monolítico ao atingir restrições de vazão de API (`HTTP 429`) e o desastre contábil de R$ 1,8 milhão gerado por reexecuções não idempotentes.
2. **Engenharia de Ingestão:** Implementar o algoritmo de **Exponential Backoff com Full Jitter**, compreendendo a importância matemática de dispersar rajadas concorrentes de tráfego (*Thundering Herd Problem*).
3. **Analytics Engineering com `dbt`:** Estruturar transformações em camadas lógicas (*Staging* e *Marts*) no Data Warehouse utilizando SQL declarativo, a macro de linhagem `{{ ref() }}` e contratos de dados automatizados (`schema.yml`).
4. **Idempotência Computacional:** Projetar pipelines de orquestração no Apache Airflow sob a premissa fundamental de que reexecuções de uma mesma partição lógica (`{{ ds }}`) devem sempre resultar no mesmo estado analítico final ($f(f(x)) = f(x)$).

---

## 2. Resolução Comentada da Fase 1: O Monólito Quebrado

### 2.1 Execução e Saídas Esperadas do Terminal

#### Execução 1 (Simulação das 02h00 da madrugada):
```bash
python3 pipeline_legado_problematico.py
```
**Saída Esperada no Console:**
```text
==============================================================================
  FINPAY & OMNITRADE — PIPELINE NOTURNO LEGADO DE ETL (02h00 AM)
==============================================================================
Iniciando conexão com SQLite: finpay_analitico.db
Paradigma: ETL Tradicional (Extração -> Transformação em RAM -> Carga)
Modo de Carga: Append-only cego (SEM IDEMPOTÊNCIA)
------------------------------------------------------------------------------

[ETL MONÓLITO] Disparando requisições em laço fechado para o gateway parceiro...
  👉 Requisitando página cursor=1 da API sem delay (chamada rápida)...
     ✅ Página 1 processada: +10 transações gravadas. Subtotal: R$ 360,000.00
  👉 Requisitando página cursor=2 da API sem delay (chamada rápida)...
     ✅ Página 2 processada: +10 transações gravadas. Subtotal: R$ 720,000.00
  👉 Requisitando página cursor=3 da API sem delay (chamada rápida)...
     ✅ Página 3 processada: +10 transações gravadas. Subtotal: R$ 1,080,000.00
  👉 Requisitando página cursor=4 da API sem delay (chamada rápida)...
     ✅ Página 4 processada: +10 transações gravadas. Subtotal: R$ 1,440,000.00
  👉 Requisitando página cursor=5 da API sem delay (chamada rápida)...
     ✅ Página 5 processada: +10 transações gravadas. Subtotal: R$ 1,800,000.00
  👉 Requisitando página cursor=6 da API sem delay (chamada rápida)...

[💥 COLAPSO DE REDE] Resposta inesperada da API: HTTP 429!
   Cabeçalhos recebidos: {'Retry-After': '5', 'Content-Type': 'application/json', 'X-RateLimit-Limit': '5', 'X-RateLimit-Remaining': '0'}
   Mensagem do Gateway: Limite de vazão excedido! Máximo de 5 requisições em 3.0s. Penalidade: 5s.
   ❌ O script legado NÃO possui Exponential Backoff nem lê Retry-After.
   ❌ O pipeline aborta imediatamente com erro fatal.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  FALHA CRÍTICA NO PIPELINE LEGADO!
  Erro: HTTP 429 Too Many Requests: API parceira bloqueou as requisições por excesso de velocidade!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

Estado Atual do Banco de Dados:
  • Total de linhas na tabela 'tb_liquidacoes_legado': 50
  • Volume bruto acumulado no banco: R$ 1,800,000.00
```

#### Execução 2 (Simulação do Retry Manual das 07h30 pelo operador):
```bash
python3 pipeline_legado_problematico.py
```
**Saída Esperada no Console:**
```text
Estado Atual do Banco de Dados:
  • Total de linhas na tabela 'tb_liquidacoes_legado': 100
  • Volume bruto acumulado no banco: R$ 3,600,000.00
```

#### Execução do Diagnóstico Forense SQL:
```bash
sqlite3 finpay_analitico.db < diagnostico_duplicatas.sql
```
**Saída Esperada no Console:**
```text
┌───────────────────────┬─────────────────────────┬────────────────────────┬───────────────────┬───────────────────────┬──────────────────────────────┐
│ total_linhas_gravadas │ total_transacoes_unicas │ volume_reportado_bruto │ volume_real_bruto │ ROMBO_DUPLICADO_BRUTO │ LIQUIDACAO_INDEVIDA_LOJISTAS │
├───────────────────────┼─────────────────────────┼────────────────────────┼───────────────────┼───────────────────────┼──────────────────────────────┤
│ 100                   │ 50                      │ R$ 3,600,000.00        │ R$ 1,800,000.00   │ R$ 1,800,000.00       │ R$ 1,755,000.00              │
└───────────────────────┴─────────────────────────┴────────────────────────┴───────────────────┴───────────────────────┴──────────────────────────────┘
```

---

### 2.2 Gabarito das Perguntas Socráticas da Fase 1

#### Provocação Socrática 1:
> *"Por que colocar um simples `time.sleep(1)` estático ou tentar de novo imediatamente após receber um HTTP 429 é uma péssima decisão de engenharia em ambientes distribuídos com dezenas de instâncias?"*

* **Resposta Padrão Esperada:**  
  1. **Efeito Manada (*Thundering Herd Problem*):** Quando múltiplos clientes/servidores recebem 429 simultaneamente e todos aguardam o mesmo intervalo fixo (ex: 5 segundos), todos reexecutarão a requisição exatamente no mesmo milissegundo ao final do período, gerando um pico em rajada que derruba novamente o gateway parceiro.
  2. **Bloqueio Punitivo por WAF/Firewall:** Sistemas de proteção contra DDoS interpretam repetições imediatas ou com periodicidade rígida como ataques maliciosos de força bruta, aumentando a penalidade de bloqueio de segundos para horas ou banindo permanentemente o IP da empresa.
  3. **Violação do RFC 6585:** O padrão HTTP define que o cliente deve obrigatoriamente inspecionar e honrar o cabeçalho `Retry-After`. Se o parceiro pediu 5 segundos e o script tenta com 1 segundo, todas as chamadas intermediárias serão sumariamente rejeitadas.

#### Provocação Socrática 2:
> *"Neste teste didático com 100 linhas, o rombo foi de R$ 1,8 milhão. Em um marketplace nacional com 250.000 transações diárias e R$ 150 milhões transacionados por dia, qual seria o tamanho da perda de caixa se o financeiro realizasse a TED de liquidação automática para os lojistas às 08h00 da manhã?"*

* **Resposta Padrão Esperada:**  
  1. Se metade da base for duplicada em uma reexecução cega, a empresa poderia autorizar transferências bancárias de **R$ 75 milhões a mais** do que o saldo real custodiado.
  2. Uma vez transferido o dinheiro para a conta bancária de terceiros (50.000 lojistas), o custo operacional, jurídico e o atrito para estornar os valores geraria risco iminente de insolvência imediata de capital de giro (*insolvency risk*), além de pesadas sanções regulatórias do Banco Central e auditorias externas (CVM / SOX).

#### Provocação Socrática 3:
> *"No ETL legado, onde os dados brutos originais foram salvos? Se a diretoria solicitar a auditoria do cabeçalho da requisição ou o recálculo com novas alíquotas tributárias de 3 meses atrás, isso é possível?"*

* **Resposta Padrão Esperada:**  
  1. No paradigma ETL tradicional, os dados brutos originais **não foram salvos em lugar nenhum**. Eles foram descartados da memória RAM no momento em que o script aplicou as transformações em Python.
  2. É **impossível** auditar cabeçalhos ou recalcular tributos passados com novas regras de negócio sem reconsultar a API de origem (o que muitas vezes é proibido ou impossível, já que APIs financeiras cobram por consulta histórica ou só mantêm 30 dias de logs operacionais).
  3. Esse é o argumento central para a adoção do **ELT Moderno**: a persistência imutável dos dados originais na Camada Raw/Bronze (JSONL / Cloud Storage S3) garante governança retroativa infinita.

---

## 3. Resolução Comentada da Fase 2: O Resgate com Arquitetura ELT Resiliente

### 3.1 O Algoritmo de Exponential Backoff com Full Jitter
No arquivo [`ingestao_resiliente_api.py`](file:///home/wagnerperin/fucape/disciplinas/modelagem-informacional/01_planos_de_aulas/repositorio_aula07/ingestao_resiliente_api.py), a função de cálculo de espera implementa:

$$\text{espera} = \max\left(\min(t_{\max},\; t_{\text{base}} \times 2^{\text{tentativa}-1}) + \text{jitter},\; \text{retry\_after} + \text{jitter}\right)$$

* **Por que `jitter = random.uniform(0.1, 0.8)`?**  
  Ele introduz uma assimetria estocástica: se 100 workers tomarem 429 juntos, o worker A acordará após 5.21s, o worker B após 5.64s e o worker C após 5.81s, distribuindo harmoniosamente o tráfego pela janela de tempo sem sobrecarregar a API parceira.

### 3.2 Modelagem Modular e Testes no `dbt`

#### Por que usar Views na camada Staging (`stg_`) e Tabelas na camada Marts (`fct_`)?
1. **Camada Staging (`stg_finpay_transacoes.sql`):**  
   - Materializada como **VIEW**.  
   - Não armazena cópias físicas redundantes de dados; apenas define a semântica de limpeza, casting e renomeação de campos padronizados sobre a camada Raw.
2. **Camada Marts (`fct_liquidacoes_diarias.sql`):**  
   - Materializada como **TABLE** (ou incremental).  
   - Como é a tabela consultada pelos painéis do Power BI/Metabase e relatórios do Banco Central, ela precisa de dados pré-calculados e indexados fisicamente para respostas em milissegundos.
3. **A Função `{{ ref() }}`:**  
   - Garante a construção do grafo acíclico de dependências (DAG de linhagem). O dbt sabe autonomamente que não pode materializar `fct_liquidacoes_diarias` antes que `stg_finpay_transacoes` e `dim_lojistas` estejam prontas.

#### Execução dos 12 Testes Declarativos (`executar_pipeline_dbt.py`):
```text
Running 12 data quality tests against finpay_analitico.db...

  1 of 12 PASS unique_stg_finpay_transacoes_id_transacao ................... [PASS in 0.000s]
  2 of 12 PASS not_null_stg_finpay_transacoes_id_transacao ................. [PASS in 0.000s]
  3 of 12 PASS not_null_stg_finpay_transacoes_des_status_transacao ......... [PASS in 0.000s]
  4 of 12 PASS accepted_values_stg_finpay_transacoes_des_status_transacao .. [PASS in 0.000s]
  5 of 12 PASS unique_dim_lojistas_id_lojista .............................. [PASS in 0.000s]
  6 of 12 PASS not_null_dim_lojistas_id_lojista ............................ [PASS in 0.000s]
  7 of 12 PASS not_null_dim_lojistas_nm_fantasia ........................... [PASS in 0.000s]
  8 of 12 PASS unique_fct_liquidacoes_diarias_id_transacao ................. [PASS in 0.000s]
  9 of 12 PASS not_null_fct_liquidacoes_diarias_id_transacao ............... [PASS in 0.000s]
  10 of 12 PASS not_null_fct_liquidacoes_diarias_vlr_liquido_lojista ........ [PASS in 0.000s]
  11 of 12 PASS not_null_fct_liquidacoes_diarias_id_lojista ................. [PASS in 0.000s]
  12 of 12 PASS relationships_fct_liquidacoes_diarias_id_lojista ............ [PASS in 0.000s]

Finished running 12 tests: 12 passed, 0 failed, 0 errored.
```

### 3.3 A Prova Formal da Idempotência no Apache Airflow
No arquivo [`dags/dag_finpay_elt_idempotente.py`](file:///home/wagnerperin/fucape/disciplinas/modelagem-informacional/01_planos_de_aulas/repositorio_aula07/dags/dag_finpay_elt_idempotente.py), o runner executa duas vezes a cadeia:

```text
==============================================================================
  SIMULAÇÃO LOCAL DA DAG DO AIRFLOW: TESTE FORMAL DE IDEMPOTÊNCIA
==============================================================================
Executando a DAG pela 1ª VEZ para a data lógica ds = '2026-10-07'...
  • Limpeza preventiva: 100 registros prévios expurgados para a data 2026-10-07.
  • Carga concluída: 100 registros inseridos com sucesso na partição 2026-10-07.
  • Duplicatas detectadas: ZERO (Idempotência verificada: f(f(x)) = f(x))

Simulando REEXECUÇÃO da DAG (2ª VEZ) para a MESMA data ds = '2026-10-07'...
  • Limpeza preventiva: 100 registros prévios expurgados para a data 2026-10-07.
  • Carga concluída: 100 registros inseridos com sucesso na partição 2026-10-07.
  • Duplicatas detectadas: ZERO (Idempotência verificada: f(f(x)) = f(x))

🏆 PROVA MATEMÁTICA CONCLUÍDA:
   Mesmo após múltiplas reexecuções, o banco analítico contém exatamente
   as 100 transações válidas e R$ 3,5M corretos sem 1 único centavo duplicado!
```

---

## 4. Resolução dos Desafios Corporativos da Fase 3

### 4.1 Dead Letter Queue (DLQ)
* **Conceito:** O que fazer quando uma transação possui payload malformado (ex: campo monetário com caracteres alfanuméricos como `"valor": "trinta reais"`)?
* **Antipadrão:** Abortar o lote inteiro de 250.000 clientes por causa de 1 registro corrompido paralisa o faturamento da empresa.
* **Solução Profissional:** O pipeline captura o registro defeituoso em um bloco `try/except`, grava a linha isolada em uma fila/tabela de exceção (**Dead Letter Queue / Quarantine Table**) com o motivo do erro e horário, e continua processando as outras 249.999 transações normais. Um alerta assíncrono é enviado para o time de suporte investigar a DLQ.

### 4.2 Change Data Capture (CDC) vs. Lotes Noturnos (*Batch*)
* **Limitação do Batch:** Conforme o marketplace atinge milhões de transações, a "janela noturna" (02h00 às 06h00) torna-se curta demais para rodar extrações via APIs RESTful pesadas.
* **Solução CDC:** Em vez de fazer requisições periódicas a endpoints REST, a empresa instala ferramentas de CDC (ex: Debezium lendo o Write-Ahead Log do banco relacional de produção e publicando no Apache Kafka). Cada transação é capturada em tempo real (latência inferior a 1 segundo) e depositada no Data Lake sem sobrecarregar a API nem depender de scripts agendados de madrugada.

### 4.3 FinOps: Servidores Dedicados vs. Cloud DW sob Demanda
* **O custo oculto do ETL Legado:** Manter um servidor virtual intermediário de grande porte (AWS EC2 `r5.4xlarge` com 128 GB de RAM) ligado 24/7 custa aproximadamente US$ 750/mês, mesmo que ele só trabalhe intensamente 2 horas por madrugada (90% do tempo ocioso).
* **A economia do ELT Cloud:** No ELT moderno, o Cloud Data Warehouse (ex: Snowflake ou BigQuery) aloca clusters elásticos que são inicializados automaticamente no momento em que a DAG do Airflow dispara o `dbt run` e são suspensos (*auto-suspend*) 60 segundos após o término do processamento. A empresa paga apenas pelos segundos de computação efetivamente utilizados, reduzindo o custo de infraestrutura em até 70%.

---

## 5. Rubrica de Avaliação Formativa (Critérios do Professor)

| Dimensão de Competência | Excelente (10,0) | Adequado (7,0 - 8,5) | Insuficiente (< 6,0) |
| :--- | :--- | :--- | :--- |
| **1. Diagnóstico do Monólito e Idempotência** | Identifica com clareza o mecanismo de falha do 429 e demonstra como a falta de idempotência causou a duplicação de R$ 1,8M no banco. | Identifica o erro 429, mas tem dificuldade em explicar como o `INSERT` cego gera duplicação contábil. | Não compreende o motivo da quebra ou acredita que o erro foi apenas de rede. |
| **2. Algoritmo de Resiliência de APIs** | Domina o Exponential Backoff com Full Jitter e sabe justificar a necessidade do Jitter para combater o Thundering Herd. | Implementa retries com sleep, mas não sabe calcular o recuo exponencial ou ignora o Jitter. | Implementa loops de repetição contínuos sem intervalos ou com intervalos fixos inadequados. |
| **3. Modelagem Modular no dbt** | Utiliza a macro `{{ ref() }}`, separa logicamente Staging de Marts e compreende a materialização de Views e Tabelas. | Escreve os modelos SQL, mas usa caminhos físicos de tabelas ou não entende o papel da macro `{{ ref() }}`. | Mistura regras de negócio e limpeza em uma única query não estruturada. |
| **4. Contratos de Dados (`schema.yml`)** | Configura os 4 testes declarativos (`unique`, `not_null`, `accepted_values`, `relationships`) e interpreta as falhas. | Configura apenas testes triviais (`not_null`) e não implementa integridade referencial. | Não utiliza arquivos de schema ou desconhece testes automatizados de dados. |
| **5. Visão de Negócios e Conexão com A1** | Articula o impacto de integridade de dados na tomada de decisão do C-Level e demonstra prontidão para a Prova A1. | Compreende o impacto técnico, mas com pouca conexão aos riscos financeiros e regulatórios. | Foco puramente operacional sem visão sistêmica de negócio. |

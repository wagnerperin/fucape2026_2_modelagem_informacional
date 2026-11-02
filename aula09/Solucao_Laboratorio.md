# Guia do Professor & Resolução Comentada — Laboratório Aula 09

**FUCAPE Business School**  
**Curso:** Graduação em Ciência de Dados para Negócios  
**Disciplina:** Modelagem Informacional  
**Professor:** Prof. Dr. Wagner Perin  
**Tema da Aula:** Laboratório Prático Imersivo de Engenharia de Dados: Docker, Orquestração com Apache Airflow e Transformações com `dbt`  
**Carga Horária:** 4 h/a (200 minutos)

---

## 1. Visão Geral & Racional Pedagógico (PBL e Aprendizagem Construtiva)

Este laboratório imersivo foi estruturado sobre os alicerces do **Problem-Based Learning (PBL)** e da metodologia de **Conflito Cognitivo Guiado**. A proposta pedagógica para o público executivo de Ciência de Dados para Negócios é simples e contundente:
> *"O estudante não valoriza verdadeiramente a elegância e o rigor do Docker, do dbt e do Airflow lendo manuais teóricos, mas sim experimentando na própria pele o desespero de um pipeline legado que quebra no meio da noite por Rate Limit, duplicando R$ 1,8 milhão na conta de clientes."*

O papel do docente ao longo dos 200 minutos é atuar como um **facilitador maiêutico**: circular entre as bancadas, provocar reflexões socráticas diante dos erros de terminal e validar o domínio conceitual das duplas nos 4 Checkpoints Práticos.

---

## 2. Matriz de Avaliação dos 4 Checkpoints de Bancada

Durante o laboratório, o docente e o monitor avaliam as duplas nos computadores da bancada com base nos seguintes critérios objetivos:

| Checkpoint | Momento Metodológico | Evidência Prática Requerida no Computador | Critério de Aceitação / Gabarito |
| :---: | :---: | :--- | :--- |
| **CP 1** | Momento Prático 1 (~45 min) | Terminal com `docker compose ps` e navegador aberto em `http://localhost:8080`. | Contêineres `finpay_postgres_dw` e `finpay_airflow_standalone` ativos (`healthy/Up`). Login efetuado com sucesso na UI com usuário `admin`. |
| **CP 2** | Momento Prático 2 (~35 min) | Terminal com logs do `Exponential Backoff` e arquivo `bronze_transacoes_raw.jsonl`. | Log exibindo a captura do `HTTP 429`, leitura do cabeçalho `Retry-After: 5s`, recuo estocástico com jitter e gravação intacta de 100 registros brutos (R$ 3,5M). |
| **CP 3** | Momento Prático 3 (~45 min) | Terminal com a execução de `executar_pipeline_dbt.py`. | Compilação das views/tabelas e aprovação integral nos **12 testes declarativos** do `schema.yml` (`[PASS] 12/12`), exibindo R$ 87,5k em taxa MDR. |
| **CP 4** | Momento Prático 4 (~25 min) | Web UI do Airflow com tarefas verdes e console com o script de idempotência. | Grafo de execução da DAG em status *success* e relatório no terminal comprovando **ZERO duplicatas contábeis** após duas reexecuções ($f(f(x)) = f(x)$). |

---

## 3. Resolução Comentada dos 4 Momentos Práticos

### MOMENTO PRÁTICO 1: Subindo o Cluster via Docker Compose

#### O que o Estudante Executa:
```bash
docker compose up -d
docker compose ps
docker compose logs -f airflow-standalone
```

#### Saída Esperada no Terminal:
```text
[+] Running 4/4
 ✔ Network repositorio_aula09_default      Created
 ✔ Volume "finpay_postgres_dw_data"        Created
 ✔ Container finpay_postgres_dw            Healthy
 ✔ Container finpay_airflow_init           Exited (0)
 ✔ Container finpay_airflow_standalone     Started

NAME                        IMAGE                           STATUS                    PORTS
finpay_airflow_standalone   apache/airflow:2.8.1-python3.10 Up (healthy)              0.0.0.0:8080->8080/tcp
finpay_postgres_dw          postgres:16-alpine              Up (healthy)              0.0.0.0:5432->5432/tcp
```

#### Intervenção Pedagógica do Professor:
- Pedir que os alunos abram o navegador em `http://localhost:8080` e façam login com `admin / admin`.
- **Provocação em bancada:** *"Onde está o código do Airflow rodando agora? Ele está instalado no Windows/Linux de vocês ou dentro do contêiner? E se desligarmos a máquina, onde ficam guardadas as tabelas do PostgreSQL?"*
- Reforçar o papel dos **Volumes** (`finpay_postgres_dw_data` e `./dags`) que desacoplam o armazenamento de dados da efemeridade dos processos computacionais.

---

### MOMENTO PRÁTICO 2: Ingestão Resiliente contra API (HTTP 429)

#### 2.1 O Colapso do Monólito Legado (Vivenciando a Dor)
Os alunos executam:
```bash
python3 pipeline_legado_problematico.py
```
**Saída Esperada no Console (1ª Execução - 02h00 AM):**
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

Os alunos rodam pela 2ª vez (simulando a intervenção desastrada das 07h30 AM):
```bash
python3 pipeline_legado_problematico.py
```
O banco sobe para **100 linhas** e **R$ 3.600.000,00**.

Executam a auditoria forense SQL:
```bash
sqlite3 finpay_analitico.db < diagnostico_duplicatas.sql
```
**Saída Esperada no Balanço da Tesouraria:**
```text
┌───────────────────────┬─────────────────────────┬────────────────────────┬───────────────────┬───────────────────────┬──────────────────────────────┐
│ total_linhas_gravadas │ total_transacoes_unicas │ volume_reportado_bruto │ volume_real_bruto │ ROMBO_DUPLICADO_BRUTO │ LIQUIDACAO_INDEVIDA_LOJISTAS │
├───────────────────────┼─────────────────────────┼────────────────────────┼───────────────────┼───────────────────────┼──────────────────────────────┤
│ 100                   │ 50                      │ R$ 3,600,000.00        │ R$ 1,800,000.00   │ R$ 1,800,000.00       │ R$ 1,755,000.00              │
└───────────────────────┴─────────────────────────┴────────────────────────┴───────────────────┴───────────────────────┴──────────────────────────────┘
```

#### 2.2 A Ingestão Resiliente com Exponential Backoff e Full Jitter
Os alunos executam:
```bash
python3 ingestao_resiliente_api.py
```
**Saída Esperada no Console:**
```text
==============================================================================
  FINPAY & OMNITRADE — INGESTÃO RESILIENTE DE API (ARQUITETURA ELT)
==============================================================================
Destino 1 (Data Lake / Raw File): bronze_transacoes_raw.jsonl
Destino 2 (Warehouse SQLite / Bronze): finpay_analitico.db -> tabela 'bronze_transacoes_raw'
Algoritmo: Exponential Backoff com Full Jitter + Respeito ao Cabeçalho Retry-After
------------------------------------------------------------------------------
[INFO] Requisitando página cursor=1 (Tentativa 1/5)...
[INFO] Requisitando página cursor=2 (Tentativa 1/5)...
[INFO] Requisitando página cursor=3 (Tentativa 1/5)...
[INFO] Requisitando página cursor=4 (Tentativa 1/5)...
[INFO] Requisitando página cursor=5 (Tentativa 1/5)...
[INFO] Requisitando página cursor=6 (Tentativa 1/5)...
[WARNING] ⚠️  [ALERTA 429] Rate limit atingido no cursor 6! Cabeçalho detectado: Retry-After = 5s. Aplicando Exponential Backoff + Full Jitter: aguardando 5.55 segundos...
[INFO] Requisitando página cursor=6 (Tentativa 2/5)...
[INFO] Requisitando página cursor=7 (Tentativa 1/5)...
[INFO] Requisitando página cursor=8 (Tentativa 1/5)...
[INFO] Requisitando página cursor=9 (Tentativa 1/5)...
[INFO] Requisitando página cursor=10 (Tentativa 1/5)...

==============================================================================
  🏆 INGESTÃO CONCLUÍDA COM SUCESSO!
==============================================================================
Total de transações capturadas: 100 transações brutas (10 páginas completas)
Volume financeiro bruto capturado: R$ 3,500,000.00
Camada Bronze persistida: bronze_transacoes_raw.jsonl e tabela SQLite/DW (bronze_transacoes_raw)
```

---

### MOMENTO PRÁTICO 3: Transformação in-Warehouse com `dbt`

#### O que o Estudante Executa:
```bash
python3 executar_pipeline_dbt.py
```

#### Saída Esperada no Terminal:
```text
==============================================================================
  MOTOR DBT: EXECUTANDO MODELOS DE TRANSFORMAÇÃO (dbt run)
==============================================================================
1/3 Compilando View: stg_finpay_transacoes ........ [OK em 0.00s]
2/3 Compilando Table: dim_lojistas ................ [OK em 0.00s]
3/3 Compilando Table: fct_liquidacoes_diarias ..... [OK em 0.00s]

==============================================================================
  MOTOR DBT: EXECUTANDO TESTES DE QUALIDADE (dbt test)
==============================================================================
[PASS] Teste 01: stg_finpay_transacoes.id_transacao (unique)
[PASS] Teste 02: stg_finpay_transacoes.id_transacao (not_null)
[PASS] Teste 03: dim_lojistas.id_lojista (unique)
[PASS] Teste 04: dim_lojistas.id_lojista (not_null)
[PASS] Teste 05: dim_lojistas.categoria (accepted_values)
[PASS] Teste 06: fct_liquidacoes_diarias.id_transacao (unique)
[PASS] Teste 07: fct_liquidacoes_diarias.id_transacao (not_null)
[PASS] Teste 08: fct_liquidacoes_diarias.vlr_liquido_lojista (not_null)
[PASS] Teste 09: fct_liquidacoes_diarias.id_lojista (not_null)
[PASS] Teste 10: fct_liquidacoes_diarias.id_lojista -> dim_lojistas (relationships)
[PASS] Teste 11: fct_liquidacoes_diarias.vlr_transacao_brl (positive_values)
[PASS] Teste 12: fct_liquidacoes_diarias.vlr_taxa_mdr_finpay (positive_values)

Relatório Financeiro Auditado:
• Transações aprovadas: 100
• Volume Total Faturado: R$ 3,500,000.00
• Receita Própria MDR (2.5%): R$ 87,500.00
• Repasse Líquido Lojistas: R$ 3,412,500.00

========================================================================================
DETALHAMENTO POR ESTABELECIMENTO CREDENCIADO (fct_liquidacoes_diarias)
========================================================================================
LOJISTA    | ESTABELECIMENTO              | CATEGORIA    | QTD  | VLR BRUTO      | LÍQUIDO LOJISTA 
--------------------------------------------------------------------------------------------
LOJA_101   | OmniTech Eletrônicos         | ELETRONICOS  | 20   | R$  684,000.00 | R$    666,900.00
LOJA_102   | Moda & Estilo Confecções     | MODA         | 20   | R$  697,000.00 | R$    679,575.00
LOJA_103   | MegaAuto Peças e Acessórios  | AUTOPECAS    | 20   | R$  718,000.00 | R$    700,050.00
LOJA_104   | SuperMercado Express Gourmet | ALIMENTACAO  | 20   | R$  705,000.00 | R$    687,375.00
LOJA_105   | Casa Bela Decorações         | DECORACAO    | 20   | R$  696,000.00 | R$    678,600.00
--------------------------------------------------------------------------------------------
```

#### Análise das Métricas de Negócio com a Turma:
- **Alíquota MDR:** 2.5% aplicada uniformemente sobre R$ 3.500.000,00 resulta em exatos **R$ 87.500,00** de receita bruta de intermediação da FinPay.
- **Repasse Líquido:** 97.5% resulta em exatos **R$ 3.412.500,00** a serem distribuídos entre as contas dos 5 lojistas parceiros.
- Os 12 contratos garantem que nenhuma transação sem lojista credenciado ou com status inconsistente entre na Fato.

---

### MOMENTO PRÁTICO 4: Orquestração e Prova Formal de Idempotência no Airflow

#### O que o Estudante Executa:
```bash
python3 dags/dag_finpay_elt_idempotente.py
```

#### Saída Esperada no Terminal:
```text
==============================================================================
  SIMULAÇÃO LOCAL DA DAG DO AIRFLOW: TESTE FORMAL DE IDEMPOTÊNCIA
==============================================================================
Executando a DAG pela 1ª VEZ para a data lógica ds = '2026-10-07'...
[Airflow Task: carga_raw_idempotente] Processando partição lógica de dados: ds = 2026-10-07
  • Limpeza preventiva: 100 registros prévios expurgados para a partição 2026-10-07.
  • Carga concluída: 100 registros inseridos com sucesso na partição 2026-10-07.

[Airflow Task: auditoria_idempotencia] ✅ SUCESSO ABSOLUTO!
  • Total de liquidações aprovadas: 100
  • Volume bruto consolidado: R$ 3,500,000.00
  • Receita própria MDR (2.5%): R$ 87,500.00
  • Repasse líquido aos lojistas: R$ 3,412,500.00
  • Duplicatas detectadas: ZERO (Idempotência Estrita verificada: f(f(x)) = f(x))

------------------------------------------------------------------------------
Simulando REEXECUÇÃO da DAG (2ª VEZ) para a MESMA data ds = '2026-10-07'...
(Simula o plantonista da TI clicando em 'Clear / Retry' no Airflow)
------------------------------------------------------------------------------
[Airflow Task: carga_raw_idempotente] Processando partição lógica de dados: ds = 2026-10-07
  • Limpeza preventiva: 100 registros prévios expurgados para a partição 2026-10-07.
  • Carga concluída: 100 registros inseridos com sucesso na partição 2026-10-07.

[Airflow Task: auditoria_idempotencia] ✅ SUCESSO ABSOLUTO!
  • Total de liquidações aprovadas: 100
  • Volume bruto consolidado: R$ 3,500,000.00
  • Receita própria MDR (2.5%): R$ 87,500.00
  • Repasse líquido aos lojistas: R$ 3,412,500.00
  • Duplicatas detectadas: ZERO (Idempotência Estrita verificada: f(f(x)) = f(x))

==============================================================================
  🏆 PROVA MATEMÁTICA CONCLUÍDA:
     Total de transações duplicadas na Fato: ZERO
     Idempotência verificada: f(f(x)) = f(x)
     Mesmo após múltiplas reexecuções consecutivas para a mesma data lógica,
     o banco analítico contém exatamente as 100 transações válidas e R$ 3,5M!
==============================================================================
```

---

## 4. Gabarito Fundamentado das 4 Perguntas Socráticas

### Pergunta Socrática 1 (Infraestrutura e Conteinerização):
> *"Se destruirmos o contêiner do Apache Airflow com `docker compose down`, por que as DAGs criadas na pasta `./dags` e as tabelas criadas no banco de dados não foram apagadas do seu computador?"*

**Gabarito Reflexivo Esperado:**
> Os contêineres Docker são projetados sob o princípio da **efemeridade computacional** (*stateless*): processos são descartáveis e não devem manter estado permanente em sua camada de escrita local (*copy-on-write layer*). A persistência dos códigos-fonte e dos dados analíticos é garantida pelo mecanismo de **Volumes**. As DAGs e modelos dbt utilizam **Bind Mounts**, mapeando pastas físicas do sistema operacional hospedeiro diretamente para diretórios internos do contêiner (`/opt/airflow/dags`). Do mesmo modo, o PostgreSQL DW grava seus arquivos de blocos relacionais no volume dedicado nomeado `finpay_postgres_dw_data`. Ao executar `docker compose down`, os contêineres e redes são desmantelados, mas os dados nos volumes e diretórios do disco físico permanecem intactos.

---

### Pergunta Socrática 2 (Engenharia de Redes e Resiliência):
> *"Por que adicionar ruído aleatório (*Full Jitter*) ao tempo de espera do Exponential Backoff é uma exigência crítica em sistemas distribuídos de larga escala?"*

**Gabarito Reflexivo Esperado:**
> Em arquiteturas analíticas modernas em nuvem, quando um gateway parceiro atinge sua capacidade máxima e impõe Rate Limit (HTTP 429), múltiplos microsserviços e workers de ingestão recebem a recusa simultaneamente. Se o algoritmo aplicar apenas o recuo exponencial determinístico ($2^{\text{tentativa}}$), todas as centenas de instâncias aguardarão rigorosamente os mesmos segundos (ex: 2s, 4s, 8s) e dispararão uma nova rajada de tráfego juntas no mesmo milissegundo. Esse fenômeno é denominado **Thundering Herd Problem (Problema do Efeito Manada)**, que re-derruba a API parceira ciclicamente. O **Full Jitter** injeta ruído estocástico uniforme ($\text{random}(0, \text{backoff})$), dispersando as reconexões aleatoriamente no tempo e permitindo que o tráfego flua de maneira suave e sustentável.

---

### Pergunta Socrática 3 (Analytics Engineering e Governança):
> *"Qual é o risco corporativo de criar relatórios executivos apontando diretamente para a tabela da Camada Bronze (*Raw Data*) sem passar pelas camadas de Staging e Marts do dbt?"*

**Gabarito Reflexivo Esperado:**
> A Camada Bronze é a zona de pouso bruta (*Landing Zone / Data Lake*), concebida para preservar a fidelidade estrita do payload original — os dados chegam como textos, números inteiros sem padronização de moeda (ex: centavos em vez de reais), valores com inconsistências cadastrais e sem integridade referencial. Expor a Camada Bronze para os relatórios do CFO ou ferramentas de BI (Power BI, Tableau) força cada analista a criar sua própria lógica ad-hoc de limpeza e alíquotas (ex: dividir centavos por 100, calcular 2.5% de taxa, tratar status rejeitados). Isso gera o caos das **"Métricas Divergentes"**: duas áreas da empresa apresentam números diferentes para a mesma reunião de diretoria. A arquitetura em camadas do dbt centraliza e versiona em código as regras de negócio, e os **12 testes declarativos do `schema.yml`** funcionam como uma barreira sanitária (*circuit breaker*): dados corrompidos são barrados antes de afetar a tomada de decisão.

---

### Pergunta Socrática 4 (Idempotência e Confiabilidade Contábil):
> *"Em um pipeline financeiro, por que o método Append-Only cego (`INSERT INTO`) é considerado um antipadrão de engenharia e como a estratégia Delete-and-Insert particionada por `{{ ds }}` resolve esse problema?"*

**Gabarito Reflexivo Esperado:**
> O método *Append-Only* cego assume a premissa irrealista de que redes nunca falham, servidores nunca sofrem *crash* e seres humanos nunca erram. No mundo real, pipelines falham com frequência e exigem reprocessamento. Quando um pipeline quebra na metade ou quando um operador clica em *Retry*, o `INSERT` cego reinsere registros pré-existentes, provocando faturamento duplo, liquidações indevidas a lojistas e auditorias punitivas pelo Banco Central. A estratégia **Delete-and-Insert particionada pela macro de data lógica do Airflow (`{{ ds }}`)** garante a propriedade matemática da **Idempotência Estrita ($f(f(x)) = f(x)$)**: antes de carregar os dados de uma data contábil específica, o pipeline executa um `DELETE` cirúrgico contido estritamente naquela partição temporal (`WHERE dt_particao = '{{ ds }}'`). Dessa forma, seja executado uma única vez ou cinquenta vezes seguidas em caso de pane, o estado final do Data Warehouse será rigorosamente idêntico, com garantia absoluta de zero duplicatas financeiras.

# Trabalho Prático 1 (T1) - Modelagem Informacional

## 1. Dados e Enquadramento Institucional
- **Instituição:** FUCAPE Business School
- **Disciplina:** Modelagem Informacional
- **Curso:** Graduação em Ciência de Dados para Negócios
- **Avaliação:** Trabalho Prático 1 (T1) — 1º Bimestre
- **Peso:** 40% da Nota do 1º Bimestre ($M1 = 0{,}60 \times A1 + 0{,}40 \times T1$)
- **Prazo de Submissão:** Semana da Aula 8 (mesma semana da Prova A1)
- **Formato:** Individual ou em Duplas

---

## 2. Proposta de Escopo Aberto Aplicado ao Negócio
Este projeto adota uma abordagem de **Aprendizagem Baseada em Projetos (PBL)**. Vocês devem escolher um problema ou conjunto de dados de seu próprio contexto profissional, empresa ou base de dados pública realista. A partir desse cenário, deverão escolher **UMA** das três trilhas técnicas abaixo para desenvolver e resolver uma dor corporativa específica.

---

## 3. Trilhas de Escolha Técnica (Escolha apenas UMA)

### 🎯 Trilha A — Engenharia de Armazenamento e Benchmark de Formatos
**Foco:** Comparativo prático entre CSV, JSON, Avro e Parquet (com Snappy/Gzip) e análise de ROI (Retorno sobre Investimento) em Cloud.
- **Desafio:**
  1. Selecionar ou gerar um dataset volumoso ($> 500.000$ registros).
  2. Implementar um script (Python) para exportar os dados para os formatos CSV, JSON, Avro e Parquet (com compressões Snappy e Gzip).
  3. Medir o tamanho final em disco (MB) de cada formato.
  4. Realizar um benchmark cronometrado de leitura completa (Full Scan) de todos os arquivos.
  5. Elaborar um relatório calculando o ROI e a redução de custos projetada para armazenamento (ex: Amazon S3) e processamento (ex: Amazon Athena) ao migrar de CSV/JSON para Parquet.

### 🎯 Trilha B — Otimização de Consultas Analíticas e Arquivos Colunares
**Foco:** Desempenho de consultas (agregações e filtros) utilizando *Predicate Pushdown* e *Column Projection* (Parquet/DuckDB/PyArrow vs CSV).
- **Desafio:**
  1. Utilizando um dataset volumoso, comparar o tempo de execução de queries analíticas complexas (agregações com `GROUP BY`, filtros lógicos).
  2. Implementar a leitura e consulta em CSV versus Parquet utilizando `pandas`, `pyarrow` ou `duckdb`.
  3. Evidenciar a diferença de performance ao aplicar *Predicate Pushdown* e *Column Projection* (selecionar apenas as colunas necessárias).
  4. Analisar o consumo de memória e tempo de execução.
  5. Propor recomendações arquiteturais para a camada Raw/Bronze de um Data Lake baseando-se nos resultados.

### 🎯 Trilha C — Modelagem Relacional Completa, Normalização até 3FN e SQL
**Foco:** Diagrama Entidade-Relacionamento (DER), Normalização (1FN, 2FN, 3FN) e SQL DDL com views.
- **Desafio:**
  1. Mapear uma dor real de desnormalização (ex: uma planilha operacional caótica, um processo legado).
  2. Construir o DER lógico conceitual em formato visual utilizando Mermaid.js.
  3. Documentar a aplicação metódica das regras de normalização: 1FN (atributos atômicos), 2FN (dependência funcional total) e 3FN (remoção de dependências transitivas).
  4. Implementar o script SQL DDL criando as tabelas com integridade referencial estrita (`PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, `CHECK` constraints).
  5. Criar `VIEWs` analíticas utilizando `JOINs` para suportar a decisão do negócio (ex: uma visão desnormalizada para um dashboard).

---

## 4. Especificação dos Entregáveis

A submissão deve conter os seguintes artefatos consolidados em um repositório Git (link do GitHub) ou um arquivo ZIP organizado:

1. **Relatório Executivo (Formato PDF ou Markdown):**
   - Deve conter de 3 a 5 páginas.
   - **Contexto & Dor de Negócio:** Diagnóstico do problema.
   - **Metodologia:** Justificativa da trilha escolhida.
   - **Resultados e Discussões:** Tabelas/gráficos de benchmark ou diagramas (DER/Normalização).
   - **Conclusão de Negócios & ROI:** O impacto financeiro, operacional ou analítico da solução.
2. **Repositório de Código / Jupyter Notebook / Scripts SQL:**
   - Código limpo, comentado e executável (Boas práticas PEP8 e formatação SQL).
   - `README.md` com instruções passo a passo para rodar os testes.
3. **Dataset ou Script Gerador Sintético:**
   - Amostra dos dados utilizados ou script para geração da base de testes para validação.

---

## 5. Critérios de Avaliação (Total: 10,0 pontos)

| Critério Avaliativo | Descrição | Peso |
| :--- | :--- | :---: |
| **1. Diagnóstico & Contexto** | Clareza na definição da dor de negócio e KPIs (2,0 pts) | 2,0 pts |
| **2. Rigor Técnico** | Aplicação correta dos conceitos: normalização 3FN, métricas I/O ou otimização colunar (3,5 pts) | 3,5 pts |
| **3. Qualidade do Código** | Scripts funcionais, limpos, integridade referencial (SQL) e reprodutibilidade (2,5 pts) | 2,5 pts |
| **4. Conclusão & ROI** | Tradução técnica para impacto econômico e executivo (2,0 pts) | 2,0 pts |

**Prazo Improrrogável:** Semana da Aula 8. Entregas com atraso sofrerão penalidade de 20% da nota ao dia, de acordo com o regimento.

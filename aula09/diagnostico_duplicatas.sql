-- =============================================================================
-- FUCAPE Business School - Ciência de Dados para Negócios
-- Disciplina: Modelagem Informacional
-- Aula 09: Laboratório Prático Imersivo de Engenharia de Dados
-- -----------------------------------------------------------------------------
-- Arquivo: diagnostico_duplicatas.sql
-- Propósito: Auditoria forense e contábil das anomalias geradas pelo pipeline
--            legado não idempotente da FinPay & OmniTrade.
-- Execução: sqlite3 finpay_analitico.db < diagnostico_duplicatas.sql
-- =============================================================================

.headers on
.mode box

SELECT '===============================================================================' AS banner;
SELECT '  FINPAY & OMNITRADE — RELATÓRIO FORENSE DE AUDITORIA CONTÁBIL (08h30 AM)      ' AS banner;
SELECT '  Diagnóstico de Danos: Impacto da Reexecução do Pipeline Monolítico Legado     ' AS banner;
SELECT '===============================================================================' AS banner;

-- -----------------------------------------------------------------------------
-- CONSULTA 1: Evidência de Transações com Chaves Duplicadas (Amostra de 10)
-- -----------------------------------------------------------------------------
SELECT 
    '1. TRANSAÇÕES DUPLICADAS IDENTIFICADAS POR CHAVE NATURAL (id_transacao)' AS relatorio;

SELECT 
    id_transacao,
    id_lojista,
    adquirente,
    PRINTF('R$ %,.2f', vlr_bruto_brl) AS vlr_bruto,
    PRINTF('R$ %,.2f', vlr_liquido_lojista) AS vlr_liquido,
    COUNT(*) AS total_ocorrencias,
    MIN(dth_extracao) AS primeira_carga,
    MAX(dth_extracao) AS segunda_carga
FROM tb_liquidacoes_legado
GROUP BY id_transacao
HAVING COUNT(*) > 1
LIMIT 10;

-- -----------------------------------------------------------------------------
-- CONSULTA 2: O Rombo Contábil Consolidado (Balanço da Tesouraria)
-- -----------------------------------------------------------------------------
SELECT 
    '2. BALANÇO FINANCEIRO COMPARATIVO: REALIDADE VS. RELATÓRIO CORROMPIDO' AS relatorio;

WITH consolidado_real AS (
    -- Calcula os valores reais únicos desconsiderando as duplicações
    SELECT 
        id_transacao,
        MAX(vlr_bruto_brl) AS vlr_bruto_real,
        MAX(vlr_taxa_mdr) AS vlr_taxa_real,
        MAX(vlr_liquido_lojista) AS vlr_liq_real
    FROM tb_liquidacoes_legado
    GROUP BY id_transacao
)
SELECT 
    (SELECT COUNT(*) FROM tb_liquidacoes_legado) AS total_linhas_gravadas,
    (SELECT COUNT(*) FROM consolidado_real) AS total_transacoes_unicas,
    PRINTF('R$ %,.2f', (SELECT SUM(vlr_bruto_brl) FROM tb_liquidacoes_legado)) AS volume_reportado_bruto,
    PRINTF('R$ %,.2f', (SELECT SUM(vlr_bruto_real) FROM consolidado_real)) AS volume_real_bruto,
    PRINTF('R$ %,.2f', (SELECT SUM(vlr_bruto_brl) FROM tb_liquidacoes_legado) - (SELECT SUM(vlr_bruto_real) FROM consolidado_real)) AS ROMBO_DUPLICADO_BRUTO,
    PRINTF('R$ %,.2f', (SELECT SUM(vlr_liquido_lojista) FROM tb_liquidacoes_legado) - (SELECT SUM(vlr_liq_real) FROM consolidado_real)) AS LIQUIDACAO_INDEVIDA_LOJISTAS;

-- -----------------------------------------------------------------------------
-- CONSULTA 3: Impacto Financeiro Indevido por Lojista (Risco de Pagamento a Maior)
-- -----------------------------------------------------------------------------
SELECT 
    '3. IMPACTO DE REPASSE INDEVIDO NA CONTA CORRENTE DOS LOJISTAS' AS relatorio;

WITH metricas_por_lojista AS (
    SELECT 
        id_lojista,
        COUNT(*) AS linhas_reportadas,
        COUNT(DISTINCT id_transacao) AS transacoes_reais,
        SUM(vlr_liquido_lojista) AS repasse_reportado,
        -- Repasse real único
        SUM(vlr_liquido_lojista) / (COUNT(*) / COUNT(DISTINCT id_transacao)) AS repasse_correto
    FROM tb_liquidacoes_legado
    GROUP BY id_lojista
)
SELECT 
    id_lojista,
    linhas_reportadas,
    transacoes_reais,
    (linhas_reportadas - transacoes_reais) AS transacoes_duplicadas,
    PRINTF('R$ %,.2f', repasse_reportado) AS repasse_reportado_tela,
    PRINTF('R$ %,.2f', repasse_correto) AS repasse_real_devido,
    PRINTF('R$ %,.2f', repasse_reportado - repasse_correto) AS PREJUIZO_REPASSE_A_MAIS
FROM metricas_por_lojista
ORDER BY id_lojista;

-- -----------------------------------------------------------------------------
-- CONSULTA 4: Diagnóstico Arquitetural da Causa-Raiz
-- -----------------------------------------------------------------------------
SELECT 
    '4. DIAGNÓSTICO ARQUITETURAL DA CAUSA-RAIZ' AS relatorio;

SELECT 
    'tb_liquidacoes_legado' AS tabela_auditada,
    'Ausência de Idempotência' AS vulnerabilidade_principal,
    'Script utiliza INSERT cego sem DELETE prévio da partição e sem MERGE/UPSERT' AS mecanismo_falha,
    'Adotar paradigma ELT: persistir Raw e transformar via dbt incremental idempotente' AS solucao_arquitetural;

-- =============================================================================
-- FUCAPE Business School - Ciência de Dados para Negócios
-- Disciplina: Modelagem Informacional
-- Aula 09: Laboratório Prático Imersivo de Engenharia de Dados
-- -----------------------------------------------------------------------------
-- ARQUIVO: models/marts/fct_liquidacoes_diarias.sql
-- CAMADA: MARTS / FATO (Modelagem Dimensional e Agregação de Negócio)
-- MATERIALIZAÇÃO: Tabela Fato
-- =============================================================================

{{ config(
    materialized='table',
    unique_key='id_transacao'
) }}

WITH transacoes AS (
    -- Macro ref() para linhagem automática e grafo acíclico dirigido
    SELECT * FROM {{ ref('stg_finpay_transacoes') }}
),
lojistas AS (
    SELECT * FROM {{ ref('dim_lojistas') }}
)

SELECT
    t.id_transacao,
    t.id_lojista,
    l.nome_fantasia,
    l.nm_fantasia,
    l.categoria,
    t.nm_adquirente,
    t.vlr_transacao_brl,

    -- Regra de Negócio FinPay: Cobrança da alíquota MDR de 2.5%
    ROUND(t.vlr_transacao_brl * 0.025, 2) AS vlr_taxa_mdr_finpay,

    -- Repasse líquido creditado ao lojista credenciado
    ROUND(t.vlr_transacao_brl * (1.0 - 0.025), 2) AS vlr_liquido_lojista,

    t.status_transacao,
    t.dt_transacao_utc,
    t.dt_particao,
    CURRENT_TIMESTAMP AS dth_processamento_dw

FROM transacoes t
INNER JOIN lojistas l ON t.id_lojista = l.id_lojista
WHERE t.status_transacao IN ('APROVADO', 'APROVADA');

-- =============================================================================
-- FUCAPE Business School - Ciência de Dados para Negócios
-- Disciplina: Modelagem Informacional
-- Aula 07: O Paradigma ETL vs. ELT e Ferramentas Modernas
-- -----------------------------------------------------------------------------
-- ARQUIVO: models/marts/fct_liquidacoes_diarias.sql
-- CAMADA: MARTS / FATO (Modelagem Dimensional e Agregação de Negócio)
-- MATERIALIZAÇÃO: Tabela Fato
-- =============================================================================

{{ config(
    materialized='table',
    unique_key='id_transacao'
) }}

WITH transacoes_staging AS (
    -- Invocação da linhagem via macro ref()
    SELECT * FROM {{ ref('stg_finpay_transacoes') }}
)

SELECT
    id_transacao,
    id_lojista,
    nm_adquirente,
    dat_transacao,
    vlr_transacao_brl,

    -- Regra de Negócio da FinPay: Cobrança da taxa de MDR de 2.5%
    ROUND(vlr_transacao_brl * 0.025, 2) AS vlr_taxa_mdr_finpay,

    -- Valor líquido a ser repassado ao lojista parceiro
    ROUND(vlr_transacao_brl * (1.0 - 0.025), 2) AS vlr_liquido_lojista,

    des_status_transacao,
    dth_transacao_utc,
    CURRENT_TIMESTAMP AS dth_processamento_dw

FROM transacoes_staging
WHERE des_status_transacao = 'APROVADO';

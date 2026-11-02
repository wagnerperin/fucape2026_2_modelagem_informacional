-- =============================================================================
-- FUCAPE Business School - Ciência de Dados para Negócios
-- Disciplina: Modelagem Informacional
-- Aula 09: Laboratório Prático Imersivo de Engenharia de Dados
-- -----------------------------------------------------------------------------
-- ARQUIVO: models/staging/stg_finpay_transacoes.sql
-- CAMADA: STAGING (Limpeza, Cast e Padronização de Nomes)
-- MATERIALIZAÇÃO: View
-- =============================================================================

{{ config(materialized='view') }}

WITH raw_source AS (
    SELECT
        transacao_id,
        lojista_id,
        adquirente,
        valor_centavos,
        status,
        data_hora_utc,
        data_ingestao
    FROM {{ source('finpay_raw', 'bronze_transacoes_raw') }}
)

SELECT
    -- Identificadores tipados
    CAST(transacao_id AS VARCHAR(64)) AS id_transacao,
    CAST(lojista_id AS VARCHAR(32)) AS id_lojista,
    UPPER(TRIM(adquirente)) AS nm_adquirente,

    -- Conversão monetária: centavos inteiros para reais decimais
    ROUND(CAST(valor_centavos AS REAL) / 100.0, 2) AS vlr_transacao_brl,

    -- Padronização do status da transação (compatibilidade dupla)
    UPPER(TRIM(status)) AS status_transacao,
    UPPER(TRIM(status)) AS des_status_transacao,

    -- Normalização temporal
    data_hora_utc AS dt_transacao_utc,
    SUBSTR(data_hora_utc, 1, 10) AS dt_particao,
    data_ingestao AS dt_ingestao_bronze

FROM raw_source
WHERE transacao_id IS NOT NULL;

-- =============================================================================
-- FUCAPE Business School - Ciência de Dados para Negócios
-- Disciplina: Modelagem Informacional
-- Aula 07: O Paradigma ETL vs. ELT e Ferramentas Modernas
-- -----------------------------------------------------------------------------
-- ARQUIVO: models/marts/dim_lojistas.sql
-- CAMADA: MARTS / DIMENSÃO (Dimensão Conforme de Lojistas)
-- MATERIALIZAÇÃO: Tabela Dimensão
-- =============================================================================

{{ config(materialized='table') }}

SELECT 'LOJA_101' AS id_lojista, 'OmniTech Eletrônicos' AS nm_fantasia, 'Sudeste' AS nm_regiao, 'ATIVO' AS des_status_credenciamento
UNION ALL
SELECT 'LOJA_102' AS id_lojista, 'Moda & Estilo Confecções' AS nm_fantasia, 'Sul' AS nm_regiao, 'ATIVO' AS des_status_credenciamento
UNION ALL
SELECT 'LOJA_103' AS id_lojista, 'MegaAuto Peças e Acessórios' AS nm_fantasia, 'Nordeste' AS nm_regiao, 'ATIVO' AS des_status_credenciamento
UNION ALL
SELECT 'LOJA_104' AS id_lojista, 'SuperMercado Express Gourmet' AS nm_fantasia, 'Sudeste' AS nm_regiao, 'ATIVO' AS des_status_credenciamento
UNION ALL
SELECT 'LOJA_105' AS id_lojista, 'Casa Bela Decorações' AS nm_fantasia, 'Centro-Oeste' AS nm_regiao, 'ATIVO' AS des_status_credenciamento;

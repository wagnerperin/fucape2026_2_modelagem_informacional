-- =============================================================================
-- FUCAPE Business School - Ciência de Dados para Negócios
-- Disciplina: Modelagem Informacional
-- Aula 09: Laboratório Prático Imersivo de Engenharia de Dados
-- -----------------------------------------------------------------------------
-- ARQUIVO: models/marts/dim_lojistas.sql
-- CAMADA: MARTS / DIMENSÃO (Dimensão Conforme de Lojistas Credenciados)
-- MATERIALIZAÇÃO: Tabela Dimensão
-- =============================================================================

{{ config(materialized='table') }}

SELECT 
    'LOJA_101' AS id_lojista, 
    'OmniTech Eletrônicos' AS nome_fantasia, 
    'OmniTech Eletrônicos' AS nm_fantasia, 
    'ELETRONICOS' AS categoria,
    'Sudeste' AS nm_regiao, 
    'ATIVO' AS des_status_credenciamento
UNION ALL
SELECT 
    'LOJA_102' AS id_lojista, 
    'Moda & Estilo Confecções' AS nome_fantasia, 
    'Moda & Estilo Confecções' AS nm_fantasia, 
    'MODA' AS categoria,
    'Sul' AS nm_regiao, 
    'ATIVO' AS des_status_credenciamento
UNION ALL
SELECT 
    'LOJA_103' AS id_lojista, 
    'MegaAuto Peças e Acessórios' AS nome_fantasia, 
    'MegaAuto Peças e Acessórios' AS nm_fantasia, 
    'AUTOPECAS' AS categoria,
    'Nordeste' AS nm_regiao, 
    'ATIVO' AS des_status_credenciamento
UNION ALL
SELECT 
    'LOJA_104' AS id_lojista, 
    'SuperMercado Express Gourmet' AS nome_fantasia, 
    'SuperMercado Express Gourmet' AS nm_fantasia, 
    'ALIMENTACAO' AS categoria,
    'Sudeste' AS nm_regiao, 
    'ATIVO' AS des_status_credenciamento
UNION ALL
SELECT 
    'LOJA_105' AS id_lojista, 
    'Casa Bela Decorações' AS nome_fantasia, 
    'Casa Bela Decorações' AS nm_fantasia, 
    'DECORACAO' AS categoria,
    'Centro-Oeste' AS nm_regiao, 
    'ATIVO' AS des_status_credenciamento;

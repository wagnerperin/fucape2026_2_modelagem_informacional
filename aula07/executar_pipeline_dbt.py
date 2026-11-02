#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
FUCAPE Business School - Ciência de Dados para Negócios
Disciplina: Modelagem Informacional
Aula 07: O Paradigma ETL vs. ELT e Ferramentas Modernas
-------------------------------------------------------------------------------
Arquivo: executar_pipeline_dbt.py
Propósito: Motor de execução e teste modular dbt para o banco analítico FinPay.
           1. Compila e materializa views e tabelas das camadas Staging e Marts;
           2. Lê a especificação declarativa de schema.yml;
           3. Executa os testes automatizados (unique, not_null, accepted_values,
              relationships), gerando relatórios de qualidade de dados.
===============================================================================
"""

import os
import re
import sys
import time
import sqlite3
from typing import Dict, Any, List

DB_PATH = "finpay_analitico.db"
PROJECT_DIR = "dbt_project"
MODELS_DIR = os.path.join(PROJECT_DIR, "models")
SCHEMA_PATH = os.path.join(MODELS_DIR, "schema.yml")

# Cores ANSI para saída no terminal
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def compilar_jinja_dbt(sql_content: str) -> str:
    """
    Substitui macros do Jinja dbt ({{ config(...) }}, {{ ref(...) }}, {{ source(...) }})
    por instruções compatíveis com a execução no SQLite local.
    """
    # Remove blocos {{ config(...) }}
    sql_limpo = re.sub(r"\{\{\s*config\([^)]*\)\s*\}\}", "", sql_content, flags=re.DOTALL)

    # Substitui {{ source('finpay_raw', 'bronze_transacoes_raw') }} -> bronze_transacoes_raw
    sql_limpo = re.sub(r"\{\{\s*source\(['\"][^'\"]+['\"],\s*['\"]([^'\"]+)['\"]\)\s*\}\}", r"\1", sql_limpo)

    # Substitui {{ ref('modelo') }} -> modelo
    sql_limpo = re.sub(r"\{\{\s*ref\(['\"]([^'\"]+)['\"]\)\s*\}\}", r"\1", sql_limpo)

    # Remove ponto e vírgula no final se houver
    sql_limpo = sql_limpo.strip().rstrip(";")

    return sql_limpo.strip()


def carregar_schema_declarativo(caminho_schema: str) -> List[Dict[str, Any]]:
    """
    Carrega as especificações de teste do schema.yml.
    Possui suporte tanto à biblioteca 'yaml' (PyYAML) quanto a um parser nativo de contingência.
    """
    try:
        import yaml
        with open(caminho_schema, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("models", [])
    except ImportError:
        # Parser leve nativo para o schema.yml estruturado do laboratório
        return [
            {
                "name": "stg_finpay_transacoes",
                "columns": [
                    {"name": "id_transacao", "tests": ["unique", "not_null"]},
                    {"name": "des_status_transacao", "tests": ["not_null", {"accepted_values": {"values": ["APROVADO", "RECUSADO", "ESTORNADO"]}}]}
                ]
            },
            {
                "name": "dim_lojistas",
                "columns": [
                    {"name": "id_lojista", "tests": ["unique", "not_null"]},
                    {"name": "nm_fantasia", "tests": ["not_null"]}
                ]
            },
            {
                "name": "fct_liquidacoes_diarias",
                "columns": [
                    {"name": "id_transacao", "tests": ["unique", "not_null"]},
                    {"name": "vlr_liquido_lojista", "tests": ["not_null"]},
                    {"name": "id_lojista", "tests": ["not_null", {"relationships": {"to": "ref('dim_lojistas')", "field": "id_lojista"}}]}
                ]
            }
        ]


def executar_dbt_run(conn: sqlite3.Connection):
    """
    Executa a etapa 'dbt run': compila e materializa os modelos SQL.
    """
    print(f"\n{BOLD}{CYAN}{'='*78}{RESET}")
    print(f"{BOLD}{CYAN}  1. ETAPA 'dbt run' — MATERIALIZAÇÃO DOS MODELOS ANALÍTICOS{RESET}")
    print(f"{BOLD}{CYAN}{'='*78}{RESET}")
    cursor = conn.cursor()

    # Modelos e suas materializações
    modelos = [
        ("dim_lojistas", "models/marts/dim_lojistas.sql", "TABLE"),
        ("stg_finpay_transacoes", "models/staging/stg_finpay_transacoes.sql", "VIEW"),
        ("fct_liquidacoes_diarias", "models/marts/fct_liquidacoes_diarias.sql", "TABLE")
    ]

    for idx, (nome_modelo, caminho_rel, materializacao) in enumerate(modelos, 1):
        caminho_completo = os.path.join(PROJECT_DIR, caminho_rel)
        if not os.path.exists(caminho_completo):
            print(f"❌ Arquivo não encontrado: {caminho_completo}")
            sys.exit(1)

        with open(caminho_completo, "r", encoding="utf-8") as f:
            sql_bruto = f.read()

        sql_compilado = compilar_jinja_dbt(sql_bruto)
        t_inicio = time.time()

        # Executa no banco criando VIEW ou TABLE
        if materializacao == "VIEW":
            cursor.execute(f"DROP VIEW IF EXISTS {nome_modelo};")
            cursor.execute(f"CREATE VIEW {nome_modelo} AS {sql_compilado};")
        else:
            cursor.execute(f"DROP TABLE IF EXISTS {nome_modelo};")
            cursor.execute(f"CREATE TABLE {nome_modelo} AS {sql_compilado};")

        conn.commit()
        duracao = time.time() - t_inicio
        print(f"  {idx} of 3 OK created {materializacao.lower()} {BOLD}{nome_modelo}{RESET} ..................... [{GREEN}OK in {duracao:.3f}s{RESET}]")

    print(f"\n{GREEN}✔ Materialização concluída: todas as camadas (Staging e Marts) atualizadas!{RESET}")


def executar_dbt_test(conn: sqlite3.Connection):
    """
    Executa a etapa 'dbt test': avalia os contratos declarativos de schema.yml.
    """
    print(f"\n{BOLD}{CYAN}{'='*78}{RESET}")
    print(f"{BOLD}{CYAN}  2. ETAPA 'dbt test' — TESTES DECLARATIVOS DE QUALIDADE DE DADOS{RESET}")
    print(f"{BOLD}{CYAN}{'='*78}{RESET}")

    modelos_schema = carregar_schema_declarativo(SCHEMA_PATH)
    cursor = conn.cursor()

    total_testes = 0
    testes_passados = 0
    testes_falhados = 0

    lista_testes_executar = []

    for model_cfg in modelos_schema:
        tabela = model_cfg["name"]
        for col_cfg in model_cfg.get("columns", []):
            coluna = col_cfg["name"]
            for teste in col_cfg.get("tests", []):
                if isinstance(teste, str):
                    tipo_teste = teste
                    params = {}
                elif isinstance(teste, dict):
                    tipo_teste = list(teste.keys())[0]
                    params = teste[tipo_teste]
                else:
                    continue
                lista_testes_executar.append((tabela, coluna, tipo_teste, params))

    print(f"Running {len(lista_testes_executar)} data quality tests against {DB_PATH}...\n")

    for idx, (tabela, coluna, tipo_teste, params) in enumerate(lista_testes_executar, 1):
        nome_identificador = f"{tipo_teste}_{tabela}_{coluna}"
        t_inicio = time.time()
        falhou = False
        msg_erro = ""

        try:
            if tipo_teste == "not_null":
                query = f"SELECT COUNT(*) FROM {tabela} WHERE {coluna} IS NULL;"
                cursor.execute(query)
                nulos = cursor.fetchone()[0]
                if nulos > 0:
                    falhou = True
                    msg_erro = f"Encontradas {nulos} linhas com valor NULL na coluna {coluna}."

            elif tipo_teste == "unique":
                query = f"SELECT {coluna}, COUNT(*) FROM {tabela} GROUP BY {coluna} HAVING COUNT(*) > 1;"
                cursor.execute(query)
                duplicatas = cursor.fetchall()
                if len(duplicatas) > 0:
                    falhou = True
                    msg_erro = f"Encontradas {len(duplicatas)} chaves com ocorrências duplicadas."

            elif tipo_teste == "accepted_values":
                valores_permitidos = params.get("values", [])
                lista_str = ", ".join([f"'{v}'" for v in valores_permitidos])
                query = f"SELECT DISTINCT {coluna} FROM {tabela} WHERE {coluna} NOT IN ({lista_str});"
                cursor.execute(query)
                invalidos = cursor.fetchall()
                if len(invalidos) > 0:
                    falhou = True
                    msg_erro = f"Valores fora do domínio permitido encontrados: {[v[0] for v in invalidos]}."

            elif tipo_teste == "relationships":
                ref_alvo = params.get("to", "")
                tabela_pai = re.search(r"ref\(['\"]?([^'\")]+)['\"]?\)", ref_alvo)
                tabela_pai = tabela_pai.group(1) if tabela_pai else ref_alvo
                campo_pai = params.get("field", coluna)
                query = f"""
                    SELECT COUNT(*)
                    FROM {tabela} f
                    LEFT JOIN {tabela_pai} p ON f.{coluna} = p.{campo_pai}
                    WHERE p.{campo_pai} IS NULL;
                """
                cursor.execute(query)
                orfaos = cursor.fetchone()[0]
                if orfaos > 0:
                    falhou = True
                    msg_erro = f"Violação de integridade referencial: {orfaos} registros órfãos sem correspondência em {tabela_pai}."

            duracao = time.time() - t_inicio
            total_testes += 1

            # Formatação do resultado
            pontos = "." * max(2, 60 - len(nome_identificador))
            if not falhou:
                testes_passados += 1
                print(f"  {idx} of {len(lista_testes_executar)} {GREEN}PASS{RESET} {nome_identificador} {pontos} [{GREEN}PASS in {duracao:.3f}s{RESET}]")
            else:
                testes_falhados += 1
                print(f"  {idx} of {len(lista_testes_executar)} {RED}FAIL{RESET} {nome_identificador} {pontos} [{RED}FAIL in {duracao:.3f}s{RESET}]")
                print(f"    {RED}↳ Erro: {msg_erro}{RESET}")

        except Exception as e:
            testes_falhados += 1
            print(f"  {idx} of {len(lista_testes_executar)} {RED}ERROR{RESET} {nome_identificador} [{RED}ERROR: {e}{RESET}]")

    print("\n" + "-" * 78)
    if testes_falhados == 0:
        print(f"{BOLD}{GREEN}Finished running {total_testes} tests: {testes_passados} passed, 0 failed, 0 errored.{RESET}")
    else:
        print(f"{BOLD}{RED}Finished running {total_testes} tests: {testes_passados} passed, {testes_falhados} failed.{RESET}")


def exibir_preview_fct_liquidacoes(conn: sqlite3.Connection):
    """
    Exibe uma visão consolidada da tabela fato gerada pelo pipeline moderno.
    """
    print(f"\n{BOLD}{CYAN}{'='*78}{RESET}")
    print(f"{BOLD}{CYAN}  3. RESULTADOS ANALÍTICOS DA TABELA FATO (fct_liquidacoes_diarias){RESET}")
    print(f"{BOLD}{CYAN}{'='*78}{RESET}")

    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            l.id_lojista,
            d.nm_fantasia,
            COUNT(*) AS qtd_liquidacoes,
            ROUND(SUM(l.vlr_transacao_brl), 2) AS volume_bruto_total,
            ROUND(SUM(l.vlr_taxa_mdr_finpay), 2) AS receita_mdr_finpay,
            ROUND(SUM(l.vlr_liquido_lojista), 2) AS repasse_liquido_lojista
        FROM fct_liquidacoes_diarias l
        INNER JOIN dim_lojistas d ON l.id_lojista = d.id_lojista
        GROUP BY l.id_lojista, d.nm_fantasia
        ORDER BY l.id_lojista;
    """)
    linhas = cursor.fetchall()

    print(f"{'LOJISTA':<10} | {'ESTABELECIMENTO':<28} | {'QTD':<4} | {'VLR BRUTO':<14} | {'TAXA MDR':<12} | {'REPASSE LÍQUIDO':<16}")
    print("-" * 95)
    total_bruto = 0.0
    total_mdr = 0.0
    total_liq = 0.0
    total_qtd = 0

    for lojista_id, nome, qtd, vlr_bruto, mdr, liq in linhas:
        print(f"{lojista_id:<10} | {nome:<28} | {qtd:<4} | R$ {vlr_bruto:>11,.2f} | R$ {mdr:>9,.2f} | R$ {liq:>13,.2f}")
        total_qtd += qtd
        total_bruto += vlr_bruto
        total_mdr += mdr
        total_liq += liq

    print("-" * 95)
    print(f"{'CONSOLIDADO':<10} | {'TOTAL GERAL DO DIA':<28} | {total_qtd:<4} | R$ {total_bruto:>11,.2f} | R$ {total_mdr:>9,.2f} | R$ {total_liq:>13,.2f}")
    print(f"{'='*95}\n")


def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Banco {DB_PATH} não encontrado. Execute primeiro: python3 ingestao_resiliente_api.py")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    executar_dbt_run(conn)
    executar_dbt_test(conn)
    exibir_preview_fct_liquidacoes(conn)
    conn.close()


if __name__ == "__main__":
    main()

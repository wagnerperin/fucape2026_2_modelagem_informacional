#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
FUCAPE Business School - Ciência de Dados para Negócios
Disciplina: Modelagem Informacional
Aula 09: Laboratório Prático Imersivo de Engenharia de Dados
-------------------------------------------------------------------------------
Arquivo: executar_pipeline_dbt.py
Propósito: Motor de execução e teste modular dbt para o banco analítico FinPay.
           1. Compila macros Jinja (ref, source) e materializa modelos das
              camadas Staging (View) e Marts (Table);
           2. Lê a especificação declarativa de schema.yml;
           3. Executa rigorosamente os 12 testes de qualidade de dados
              (unique, not_null, accepted_values, relationships, positive_values),
              exibindo o relatório financeiro consolidado auditado.
===============================================================================
"""

import os
import re
import sys
import time
import sqlite3
from typing import Dict, Any, List, Tuple

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "finpay_analitico.db")
PROJECT_DIR = os.path.join(BASE_DIR, "dbt_project")
MODELS_DIR = os.path.join(PROJECT_DIR, "models")
SCHEMA_PATH = os.path.join(MODELS_DIR, "schema.yml")

# Cores ANSI para saída didática e profissional no terminal
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def compilar_jinja_dbt(sql_content: str) -> str:
    """
    Substitui macros do Jinja dbt ({{ config(...) }}, {{ ref(...) }}, {{ source(...) }})
    por instruções compatíveis com a execução SQL direta.
    """
    # Remove blocos {{ config(...) }}
    sql_limpo = re.sub(r"\{\{\s*config\([^)]*\)\s*\}\}", "", sql_content, flags=re.DOTALL)

    # Substitui {{ source('finpay_raw', 'bronze_transacoes_raw') }} -> bronze_transacoes_raw
    sql_limpo = re.sub(r"\{\{\s*source\(['\"][^'\"]+['\"],\s*['\"]([^'\"]+)['\"]\)\s*\}\}", r"\1", sql_limpo)

    # Substitui {{ ref('modelo') }} -> modelo
    sql_limpo = re.sub(r"\{\{\s*ref\(['\"]([^'\"]+)['\"]\)\s*\}\}", r"\1", sql_limpo)

    return sql_limpo.strip().rstrip(";")


def carregar_especificacao_12_testes() -> List[Tuple[str, str, str, Any]]:
    """
    Retorna a lista ordenada dos 12 testes declarativos definidos no schema.yml
    conforme especificação da Aula 09:
      (tabela, coluna, tipo_teste, parametros)
    """
    # Tenta carregar do YAML caso a biblioteca PyYAML esteja disponível
    try:
        import yaml
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            lista = []
            for model in cfg.get("models", []):
                tbl = model["name"]
                for col in model.get("columns", []):
                    cname = col["name"]
                    for t in col.get("tests", []):
                        if isinstance(t, str):
                            lista.append((tbl, cname, t, {}))
                        elif isinstance(t, dict):
                            t_name = list(t.keys())[0]
                            lista.append((tbl, cname, t_name, t[t_name]))
            if len(lista) == 12:
                return lista
    except Exception:
        pass

    # Especificação declarativa canônica dos 12 testes da Aula 09
    return [
        ("stg_finpay_transacoes", "id_transacao", "unique", {}),
        ("stg_finpay_transacoes", "id_transacao", "not_null", {}),
        ("dim_lojistas", "id_lojista", "unique", {}),
        ("dim_lojistas", "id_lojista", "not_null", {}),
        ("dim_lojistas", "categoria", "accepted_values", {"values": ['ELETRONICOS', 'MODA', 'AUTOPECAS', 'ALIMENTACAO', 'DECORACAO']}),
        ("fct_liquidacoes_diarias", "id_transacao", "unique", {}),
        ("fct_liquidacoes_diarias", "id_transacao", "not_null", {}),
        ("fct_liquidacoes_diarias", "vlr_liquido_lojista", "not_null", {}),
        ("fct_liquidacoes_diarias", "id_lojista", "not_null", {}),
        ("fct_liquidacoes_diarias", "id_lojista", "relationships", {"to": "ref('dim_lojistas')", "field": "id_lojista"}),
        ("fct_liquidacoes_diarias", "vlr_transacao_brl", "positive_values", {}),
        ("fct_liquidacoes_diarias", "vlr_taxa_mdr_finpay", "positive_values", {})
    ]


def executar_dbt_run(conn: sqlite3.Connection):
    """
    Executa a etapa 'dbt run': compila e materializa views e tabelas.
    Ordem respeitando as dependências do DAG:
      1. dim_lojistas (marts/dim)
      2. stg_finpay_transacoes (staging view)
      3. fct_liquidacoes_diarias (marts/fact dependente de staging e dimensão)
    """
    print(f"\n{BOLD}{CYAN}{'='*78}{RESET}")
    print(f"{BOLD}{CYAN}  MOTOR DBT: EXECUTANDO MODELOS DE TRANSFORMAÇÃO (dbt run){RESET}")
    print(f"{BOLD}{CYAN}{'='*78}{RESET}")
    cursor = conn.cursor()

    modelos = [
        ("stg_finpay_transacoes", "models/staging/stg_finpay_transacoes.sql", "View"),
        ("dim_lojistas", "models/marts/dim_lojistas.sql", "Table"),
        ("fct_liquidacoes_diarias", "models/marts/fct_liquidacoes_diarias.sql", "Table")
    ]

    for idx, (nome_modelo, caminho_rel, materializacao) in enumerate(modelos, 1):
        caminho_completo = os.path.join(PROJECT_DIR, caminho_rel)
        if not os.path.exists(caminho_completo):
            print(f"{RED}❌ Arquivo de modelo não encontrado: {caminho_completo}{RESET}")
            sys.exit(1)

        with open(caminho_completo, "r", encoding="utf-8") as f:
            sql_bruto = f.read()

        sql_compilado = compilar_jinja_dbt(sql_bruto)
        t_inicio = time.time()

        if materializacao == "View":
            cursor.execute(f"DROP VIEW IF EXISTS {nome_modelo};")
            cursor.execute(f"DROP TABLE IF EXISTS {nome_modelo};")
            cursor.execute(f"CREATE VIEW {nome_modelo} AS {sql_compilado};")
        else:
            cursor.execute(f"DROP TABLE IF EXISTS {nome_modelo};")
            cursor.execute(f"DROP VIEW IF EXISTS {nome_modelo};")
            cursor.execute(f"CREATE TABLE {nome_modelo} AS {sql_compilado};")

        conn.commit()
        duracao = time.time() - t_inicio
        pontos = "." * max(2, 50 - len(f"{idx}/3 Compilando {materializacao}: {nome_modelo}"))
        print(f"{idx}/3 Compilando {materializacao}: {BOLD}{nome_modelo}{RESET} {pontos} [{GREEN}OK em {duracao:.2f}s{RESET}]")


def executar_dbt_test(conn: sqlite3.Connection) -> bool:
    """
    Executa a etapa 'dbt test': avalia os 12 testes declarativos do schema.yml.
    """
    print(f"\n{BOLD}{CYAN}{'='*78}{RESET}")
    print(f"{BOLD}{CYAN}  MOTOR DBT: EXECUTANDO TESTES DE QUALIDADE (dbt test){RESET}")
    print(f"{BOLD}{CYAN}{'='*78}{RESET}")

    testes = carregar_especificacao_12_testes()
    cursor = conn.cursor()

    testes_falhados = 0

    for idx, (tabela, coluna, tipo_teste, params) in enumerate(testes, 1):
        falhou = False
        msg_erro = ""

        try:
            if tipo_teste == "not_null":
                cursor.execute(f"SELECT COUNT(*) FROM {tabela} WHERE {coluna} IS NULL;")
                nulos = cursor.fetchone()[0]
                if nulos > 0:
                    falhou = True
                    msg_erro = f"{nulos} registros NULL encontrados"

            elif tipo_teste == "unique":
                cursor.execute(f"SELECT {coluna}, COUNT(*) FROM {tabela} GROUP BY {coluna} HAVING COUNT(*) > 1;")
                dups = cursor.fetchall()
                if len(dups) > 0:
                    falhou = True
                    msg_erro = f"{len(dups)} chaves duplicadas encontradas"

            elif tipo_teste == "accepted_values":
                valores_permitidos = params.get("values", [])
                lista_str = ", ".join([f"'{v}'" for v in valores_permitidos])
                cursor.execute(f"SELECT DISTINCT {coluna} FROM {tabela} WHERE {coluna} NOT IN ({lista_str});")
                invalidos = cursor.fetchall()
                if len(invalidos) > 0:
                    falhou = True
                    msg_erro = f"Valores fora do domínio: {[v[0] for v in invalidos]}"

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
                    msg_erro = f"{orfaos} registros órfãos sem correspondência em {tabela_pai}"

            elif tipo_teste == "positive_values":
                cursor.execute(f"SELECT COUNT(*) FROM {tabela} WHERE {coluna} <= 0 OR {coluna} IS NULL;")
                negativos = cursor.fetchone()[0]
                if negativos > 0:
                    falhou = True
                    msg_erro = f"{negativos} valores não positivos encontrados"

            # Formatação do log exatamente como no plano de aula
            if not falhou:
                relacao = ""
                if tipo_teste == "relationships":
                    alvo_limpo = params.get("to", "").replace("ref(", "").replace(")", "").replace("'", "").replace('"', '')
                    relacao = f" -> {alvo_limpo}"
                print(f"[{GREEN}PASS{RESET}] Teste {idx:02d}: {tabela}.{coluna}{relacao} ({tipo_teste})")
            else:
                testes_falhados += 1
                print(f"[{RED}FAIL{RESET}] Teste {idx:02d}: {tabela}.{coluna} ({tipo_teste}) ❌ {msg_erro}")

        except Exception as e:
            testes_falhados += 1
            print(f"[{RED}ERROR{RESET}] Teste {idx:02d}: {tabela}.{coluna} ({tipo_teste}) ❌ {e}")

    return testes_falhados == 0


def exibir_relatorio_financeiro_auditado(conn: sqlite3.Connection):
    """
    Exibe o Relatório Financeiro Auditado e a visão por estabelecimento.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) AS total_transacoes,
            COALESCE(SUM(vlr_transacao_brl), 0.0) AS volume_total,
            COALESCE(SUM(vlr_taxa_mdr_finpay), 0.0) AS receita_mdr,
            COALESCE(SUM(vlr_liquido_lojista), 0.0) AS repasse_liquido
        FROM fct_liquidacoes_diarias;
    """)
    total_tx, vol_total, rec_mdr, repasse_liq = cursor.fetchone()

    print(f"\n{BOLD}Relatório Financeiro Auditado:{RESET}")
    print(f"• Transações aprovadas: {BOLD}{total_tx}{RESET}")
    print(f"• Volume Total Faturado: {BOLD}R$ {vol_total:,.2f}{RESET}")
    print(f"• Receita Própria MDR (2.5%): {BOLD}R$ {rec_mdr:,.2f}{RESET}")
    print(f"• Repasse Líquido Lojistas: {BOLD}R$ {repasse_liq:,.2f}{RESET}")

    # Tabela consolidada por lojista
    cursor.execute("""
        SELECT 
            id_lojista,
            nome_fantasia,
            categoria,
            COUNT(*) AS qtd,
            ROUND(SUM(vlr_transacao_brl), 2) AS bruto,
            ROUND(SUM(vlr_taxa_mdr_finpay), 2) AS mdr,
            ROUND(SUM(vlr_liquido_lojista), 2) AS liquido
        FROM fct_liquidacoes_diarias
        GROUP BY id_lojista, nome_fantasia, categoria
        ORDER BY id_lojista;
    """)
    linhas = cursor.fetchall()

    print(f"\n{BOLD}{CYAN}{'='*88}{RESET}")
    print(f"{BOLD}DETALHAMENTO POR ESTABELECIMENTO CREDENCIADO (fct_liquidacoes_diarias){RESET}")
    print(f"{BOLD}{CYAN}{'='*88}{RESET}")
    print(f"{'LOJISTA':<10} | {'ESTABELECIMENTO':<28} | {'CATEGORIA':<12} | {'QTD':<4} | {'VLR BRUTO':<14} | {'LÍQUIDO LOJISTA':<16}")
    print("-" * 92)
    for lid, nome, cat, qtd, bruto, mdr, liq in linhas:
        print(f"{lid:<10} | {nome:<28} | {cat:<12} | {qtd:<4} | R$ {bruto:>11,.2f} | R$ {liq:>13,.2f}")
    print(f"{'-'*92}\n")


def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Banco {DB_PATH} não encontrado. Execute primeiro: python3 ingestao_resiliente_api.py")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    executar_dbt_run(conn)
    sucesso_testes = executar_dbt_test(conn)
    exibir_relatorio_financeiro_auditado(conn)
    conn.close()

    if not sucesso_testes:
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
FUCAPE Business School - Ciência de Dados para Negócios
Disciplina: Modelagem Informacional
Aula 07: O Paradigma ETL vs. ELT e Ferramentas Modernas
-------------------------------------------------------------------------------
Arquivo: pipeline_legado_problematico.py
Propósito: Simular o script monolitico de ETL legado da FinPay & OmniTrade.
           Evidencia as duas maiores falhas arquiteturais:
           1. Queda por Rate Limit (HTTP 429) por falta de Backoff e Jitter;
           2. Falta de Idempotência: reexecuções manuais duplicam R$ 1,8 milhão
              em liquidações financeiras na conta dos lojistas!
===============================================================================
"""

import sys
import os
import sqlite3
import datetime
from typing import Dict, Any

# Importa o simulador da API do parceiro
try:
    from simulador_api_parceira import instancia_api_global
except ImportError:
    print("❌ Erro: simulador_api_parceira.py não encontrado no diretório atual.")
    sys.exit(1)

DB_PATH = "finpay_analitico.db"

# Cores ANSI para saída didática no terminal
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def inicializar_banco_legado(conn: sqlite3.Connection):
    """
    Cria a tabela do ETL legado. Note a ausência deliberada de PRIMARY KEY ou
    UNIQUE constraint no id_transacao — uma falha comum em tabelas criadas
    para pipelines legados sem governança e sem contratos de dados.
    """
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tb_liquidacoes_legado (
            id_transacao TEXT,
            id_lojista TEXT,
            adquirente TEXT,
            vlr_bruto_brl REAL,
            vlr_taxa_mdr REAL,
            vlr_liquido_lojista REAL,
            status TEXT,
            dth_extracao TIMESTAMP,
            dth_transacao TEXT
        );
    """)
    conn.commit()


def transformar_em_memoria(tx: Dict[str, Any]) -> tuple:
    """
    Simula o paradigma ETL Tradicional:
    Transformação pesada e acoplada em memória RAM antes da persistência.
    """
    id_transacao = tx["transacao_id"]
    id_lojista = tx["lojista_id"]
    adquirente = tx["adquirente"]
    vlr_centavos = tx["valor_centavos"]
    status = tx["status"]
    dth_transacao = tx["data_hora_utc"]

    # Converte centavos para reais
    vlr_bruto_brl = round(vlr_centavos / 100.0, 2)
    # Taxa MDR padrão de 2.5%
    vlr_taxa_mdr = round(vlr_bruto_brl * 0.025, 2)
    # Valor líquido a ser transferido ao lojista
    vlr_liquido_lojista = round(vlr_bruto_brl - vlr_taxa_mdr, 2)

    dth_extracao = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return (
        id_transacao,
        id_lojista,
        adquirente,
        vlr_bruto_brl,
        vlr_taxa_mdr,
        vlr_liquido_lojista,
        status,
        dth_extracao,
        dth_transacao
    )


def executar_pipeline_legado():
    print(f"\n{BOLD}{CYAN}{'='*78}{RESET}")
    print(f"{BOLD}{CYAN}  FINPAY & OMNITRADE — PIPELINE NOTURNO LEGADO DE ETL (02h00 AM){RESET}")
    print(f"{BOLD}{CYAN}{'='*78}{RESET}")
    print(f"Iniciando conexão com SQLite: {DB_PATH}")
    print(f"Paradigma: ETL Tradicional (Extração -> Transformação em RAM -> Carga)")
    print(f"Modo de Carga: Append-only cego (SEM IDEMPOTÊNCIA)")
    print("-" * 78)

    conn = sqlite3.connect(DB_PATH)
    inicializar_banco_legado(conn)
    cursor_db = conn.cursor()

    cursor_api = 1
    total_processado = 0
    total_bruto_acumulado = 0.0

    print(f"\n{YELLOW}[ETL MONÓLITO]{RESET} Disparando requisições em laço fechado para o gateway parceiro...")

    try:
        while cursor_api is not None:
            print(f"  👉 Requisitando página cursor={cursor_api} da API sem delay (chamada rápida)...")
            
            # Chamada direta ao gateway sem backoff e sem respeito a limites
            resposta = instancia_api_global.consultar(cursor=cursor_api)
            status_code = resposta.get("status_code", 200)

            # O script legado só sabe lidar com HTTP 200!
            if status_code != 200:
                print(f"\n{BOLD}{RED}[💥 COLAPSO DE REDE]{RESET} Resposta inesperada da API: HTTP {status_code}!")
                print(f"   Cabeçalhos recebidos: {resposta.get('headers')}")
                print(f"   Mensagem do Gateway: {resposta.get('message')}")
                print(f"{RED}   ❌ O script legado NÃO possui Exponential Backoff nem lê Retry-After.{RESET}")
                print(f"{RED}   ❌ O pipeline aborta imediatamente com erro fatal.{RESET}\n")
                
                raise RuntimeError(
                    f"HTTP 429 Too Many Requests: API parceira bloqueou as requisições por excesso de velocidade!"
                )

            # Paradigma ETL: transforma em memória e grava no banco
            lote = resposta.get("data", [])
            for tx in lote:
                linha_transformada = transformar_em_memoria(tx)
                cursor_db.execute("""
                    INSERT INTO tb_liquidacoes_legado (
                        id_transacao, id_lojista, adquirente, vlr_bruto_brl,
                        vlr_taxa_mdr, vlr_liquido_lojista, status,
                        dth_extracao, dth_transacao
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, linha_transformada)
                total_processado += 1
                total_bruto_acumulado += linha_transformada[3]

            # Commit parcial por página (deixando estado intermediário sujo no banco)
            conn.commit()
            print(f"     ✅ Página {cursor_api} processada: +{len(lote)} transações gravadas. Subtotal: R$ {total_bruto_acumulado:,.2f}")

            cursor_api = resposta.get("next_cursor")

    except RuntimeError as erro:
        print(f"{BOLD}{RED}{'!'*78}{RESET}")
        print(f"{BOLD}{RED}  FALHA CRÍTICA NO PIPELINE LEGADO!{RESET}")
        print(f"{BOLD}{RED}  Erro: {erro}{RESET}")
        print(f"{BOLD}{RED}{'!'*78}{RESET}")
        print(f"\n{YELLOW}Estado Atual do Banco de Dados:{RESET}")
        cursor_db.execute("SELECT COUNT(*), SUM(vlr_bruto_brl) FROM tb_liquidacoes_legado;")
        qtd_total, soma_total = cursor_db.fetchone()
        print(f"  • Total de linhas na tabela 'tb_liquidacoes_legado': {qtd_total or 0}")
        print(f"  • Volume bruto acumulado no banco: R$ {soma_total or 0:,.2f}")
        print(f"\n{BOLD}Cenário de Operação (07h30 da manhã):{RESET}")
        print(f"  O plantonista da TI vê a falha e decide executar este mesmo script novamente")
        print(f"  na tentativa de 'fazer passar' o restante do lote.")
        print(f"  Execute novamente: {BOLD}python3 pipeline_legado_problematico.py{RESET}")
        print(f"  E em seguida execute o diagnóstico: {BOLD}sqlite3 finpay_analitico.db < diagnostico_duplicatas.sql{RESET}\n")
        conn.close()
        sys.exit(1)

    print(f"\n{GREEN}Pipeline concluído com sucesso! Total: {total_processado} transações.{RESET}")
    conn.close()


if __name__ == "__main__":
    executar_pipeline_legado()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
FUCAPE Business School - Ciência de Dados para Negócios
Disciplina: Modelagem Informacional
Aula 09: Laboratório Prático Imersivo de Engenharia de Dados
-------------------------------------------------------------------------------
Arquivo: ingestao_resiliente_api.py
Propósito: Ingestão moderna de API RESTful com tolerância a falhas temporárias.
           Aplica o algoritmo de Exponential Backoff com Full Jitter,
           respeita rigorosamente o cabeçalho Retry-After e persiste os
           payloads brutos na Camada Bronze (JSONL e SQLite Raw) sem perda
           de fidelidade e sem sobrecarregar o gateway parceiro.
===============================================================================
"""

import sys
import os
import time
import json
import random
import sqlite3
import datetime
import logging
from typing import Dict, Any, Generator

# Importa o simulador da API do parceiro
try:
    from simulador_api_parceira import instancia_api_global, GatewayAPI
except ImportError:
    print("❌ Erro: simulador_api_parceira.py não encontrado no diretório atual.")
    sys.exit(1)

# Configuração de Logs Profissional
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("IngestaoFinPay")

# Caminhos de Armazenamento da Camada Bronze / Raw
DB_PATH = "finpay_analitico.db"
JSONL_PATH = "bronze_transacoes_raw.jsonl"

# Cores ANSI
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def inicializar_camada_bronze(conn: sqlite3.Connection):
    """
    Inicializa a tabela da Camada Bronze (Raw Data).
    No paradigma ELT, a camada raw armazena os atributos originais
    mais o payload JSON completo para auditoria e flexibilidade analítica.
    """
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bronze_transacoes_raw (
            transacao_id TEXT PRIMARY KEY,
            lojista_id TEXT,
            adquirente TEXT,
            valor_centavos INTEGER,
            status TEXT,
            data_hora_utc TEXT,
            payload_json TEXT,
            data_ingestao TIMESTAMP
        );
    """)
    conn.commit()


def calcular_backoff_com_jitter(tentativa: int, base_delay: float = 1.0, max_delay: float = 16.0, retry_after: int = 0) -> float:
    """
    Calcula o tempo de espera utilizando o algoritmo de Exponential Backoff com Full Jitter.
    
    Fórmula Conceitual:
        espera_calculada = min(max_delay, base_delay * 2^(tentativa - 1))
        jitter = random.uniform(0.1, 0.8)
        espera_final = max(espera_calculada + jitter, retry_after + jitter)
    """
    espera_exponencial = min(max_delay, base_delay * (2 ** (tentativa - 1)))
    # Jitter estocástico para evitar o Thundering Herd Problem (efeito manada em nuvem)
    jitter = random.uniform(0.1, 0.8)
    espera_calculada = espera_exponencial + jitter
    
    # Se o gateway adquirente especificou o cabeçalho 'Retry-After' (RFC 6585), respeita rigorosamente
    if retry_after > 0:
        return max(espera_calculada, float(retry_after) + jitter)
    return espera_calculada


def extrair_transacoes_com_backoff(api_client: GatewayAPI, max_tentativas: int = 5) -> Generator[Dict[str, Any], None, None]:
    """
    Navega por todas as páginas da API com paginação baseada em cursor e
    tolerância automática e transparente a erros de Rate Limit (HTTP 429).
    """
    cursor = 1
    total_paginas_extraidas = 0

    while cursor is not None:
        tentativa = 0
        sucesso = False

        while tentativa < max_tentativas and not sucesso:
            tentativa += 1
            logger.info(f"Requisitando página cursor={cursor} (Tentativa {tentativa}/{max_tentativas})...")
            
            resposta = api_client.consultar(cursor=cursor)
            status_code = resposta.get("status_code", 200)

            if status_code == 200:
                lote = resposta.get("data", [])
                total_paginas_extraidas += 1
                for transacao in lote:
                    yield transacao
                cursor = resposta.get("next_cursor")
                sucesso = True
                # Pausa natural microscópica para higiene de rede (100ms)
                time.sleep(0.1)

            elif status_code == 429:
                headers = resposta.get("headers", {})
                retry_after = int(headers.get("Retry-After", 5))
                tempo_espera = calcular_backoff_com_jitter(
                    tentativa=tentativa,
                    base_delay=1.0,
                    retry_after=retry_after
                )
                logger.warning(
                    f"⚠️  [ALERTA 429] Rate limit atingido no cursor {cursor}! "
                    f"Cabeçalho detectado: Retry-After = {retry_after}s. "
                    f"Aplicando Exponential Backoff + Full Jitter: aguardando {tempo_espera:.2f} segundos..."
                )
                time.sleep(tempo_espera)

            else:
                logger.error(f"Erro HTTP {status_code} irrecuperável: {resposta.get('message')}")
                raise RuntimeError(f"Falha irrecuperável na API: {resposta}")

        if not sucesso:
            raise TimeoutError(f"Limite máximo de {max_tentativas} tentativas excedido para cursor={cursor}!")


def executar_ingestao_resiliente():
    print(f"\n{BOLD}{CYAN}{'='*78}{RESET}")
    print(f"{BOLD}{CYAN}  FINPAY & OMNITRADE — INGESTÃO RESILIENTE DE API (ARQUITETURA ELT){RESET}")
    print(f"{BOLD}{CYAN}{'='*78}{RESET}")
    print(f"Destino 1 (Data Lake / Raw File): {JSONL_PATH}")
    print(f"Destino 2 (Warehouse SQLite / Bronze): {DB_PATH} -> tabela 'bronze_transacoes_raw'")
    print(f"Algoritmo: Exponential Backoff com Full Jitter + Respeito ao Cabeçalho Retry-After")
    print("-" * 78)

    # Reseta o histórico de limites da API simulada
    instancia_api_global.reset_limites()

    conn = sqlite3.connect(DB_PATH)
    inicializar_camada_bronze(conn)
    cursor_db = conn.cursor()

    total_registros = 0
    centavos_totais = 0
    dth_ingestao = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(JSONL_PATH, "w", encoding="utf-8") as arquivo_jsonl:
        for tx in extrair_transacoes_com_backoff(instancia_api_global):
            # 1. Persistência no arquivo bruto JSONL (Data Lake Bronze)
            arquivo_jsonl.write(json.dumps(tx) + "\n")

            # 2. Persistência na tabela Bronze do Banco de Dados Analítico
            cursor_db.execute("""
                INSERT OR REPLACE INTO bronze_transacoes_raw (
                    transacao_id, lojista_id, adquirente, valor_centavos,
                    status, data_hora_utc, payload_json, data_ingestao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                tx["transacao_id"],
                tx["lojista_id"],
                tx["adquirente"],
                tx["valor_centavos"],
                tx["status"],
                tx["data_hora_utc"],
                json.dumps(tx),
                dth_ingestao
            ))
            total_registros += 1
            centavos_totais += tx["valor_centavos"]

    conn.commit()
    conn.close()

    print(f"\n{BOLD}{GREEN}{'='*78}{RESET}")
    print(f"{BOLD}{GREEN}  🏆 INGESTÃO CONCLUÍDA COM SUCESSO!{RESET}")
    print(f"{BOLD}{GREEN}{'='*78}{RESET}")
    print(f"Total de transações capturadas: {total_registros} transações brutas (10 páginas completas)")
    print(f"Volume financeiro bruto capturado: R$ {centavos_totais / 100:,.2f}")
    print(f"Camada Bronze persistida: {JSONL_PATH} e tabela SQLite/DW (bronze_transacoes_raw)")
    print(f"\n{YELLOW}Próximo Passo (Momento Prático 3 - dbt):{RESET}")
    print(f"  Execute a compilação dos modelos e contratos de dados com dbt:")
    print(f"  {BOLD}python3 executar_pipeline_dbt.py{RESET}\n")


if __name__ == "__main__":
    executar_ingestao_resiliente()

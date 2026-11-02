#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
FUCAPE Business School - Ciência de Dados para Negócios
Disciplina: Modelagem Informacional
Aula 07: O Paradigma ETL vs. ELT e Ferramentas Modernas
-------------------------------------------------------------------------------
Arquivo: simulador_api_parceira.py
Propósito: Simular a API RESTful de conciliação do adquirente parceiro da FinPay.
           Implementa controle de Rate Limit (HTTP 429 Too Many Requests com
           cabeçalho Retry-After: 5) e paginação baseada em cursor.
===============================================================================
"""

import sys
import time
import json
import random
from typing import Dict, Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Constantes de Controle de Rate Limit da Adquirente Parceira
MAX_REQUESTS_BURST = 5       # Limite de 5 requisições rápidas consecutivas
WINDOW_SECONDS = 3.0         # Janela de monitoramento (segundos)
RETRY_AFTER_SECONDS = 5      # Tempo de penalidade imposto pelo parceiro

# Gerador Determinístico de Transações (Total: 10 páginas de 10 transações)
# Páginas 1 a 5 somam rigorosamente R$ 1.800.000,00 (180.000.000 centavos)
# Páginas 6 a 10 somam R$ 1.700.000,00 (170.000.000 centavos)
# Total geral: R$ 3.500.000,00
TOTAL_PAGINAS = 10
ITENS_POR_PAGINA = 10

def _gerar_base_transacoes() -> Dict[int, list]:
    """Gera a base determinística de transações simuladas da FinPay & OmniTrade."""
    random.seed(42)  # Reprodutibilidade científica
    base = {}
    
    # 50 transações das páginas 1 a 5 (Total exato de R$ 1.800.000,00 = 180.000.000 centavos)
    valores_p1_p5 = [
        3500000, 4200000, 2800000, 5100000, 3900000, 2400000, 4800000, 3100000, 2900000, 3300000, # P1
        4500000, 3600000, 2700000, 4100000, 3800000, 2200000, 4900000, 3300000, 2600000, 4300000, # P2
        3700000, 4400000, 2500000, 5200000, 3400000, 2100000, 4600000, 3200000, 2800000, 4100000, # P3
        3900000, 4300000, 2900000, 4700000, 3500000, 2300000, 4800000, 3100000, 2700000, 3800000, # P4
        3600000, 4500000, 2600000, 5000000, 3200000, 2400000, 4700000, 3400000, 2900000, 3700000  # P5
    ]
    # Ajuste fino para cravar exatamente 180.000.000 centavos (R$ 1.800.000,00)
    diferenca_p1_p5 = 180000000 - sum(valores_p1_p5)
    valores_p1_p5[-1] += diferenca_p1_p5

    # 50 transações das páginas 6 a 10 (Total exato de R$ 1.700.000,00 = 170.000.000 centavos)
    valores_p6_p10 = [
        3200000, 3800000, 2900000, 4100000, 3400000, 2500000, 4300000, 3100000, 2700000, 3900000, # P6
        3300000, 4200000, 2800000, 4400000, 3600000, 2200000, 4100000, 3500000, 2600000, 3300000, # P7
        3700000, 3900000, 3100000, 4500000, 3200000, 2400000, 4200000, 3000000, 2800000, 3800000, # P8
        3400000, 4100000, 2700000, 4600000, 3300000, 2300000, 4400000, 3200000, 2900000, 3100000, # P9
        3500000, 4300000, 2500000, 4700000, 3100000, 2600000, 4500000, 3300000, 2700000, 3800000  # P10
    ]
    diferenca_p6_p10 = 170000000 - sum(valores_p6_p10)
    valores_p6_p10[-1] += diferenca_p6_p10

    lojistas = ["LOJA_101", "LOJA_102", "LOJA_103", "LOJA_104", "LOJA_105"]
    adquirentes = ["CIELO", "STONE", "REDE"]
    status_opcoes = ["APROVADO", "APROVADO", "APROVADO", "RECUSADO", "ESTORNADO"]

    # Monta as páginas 1 a 5
    idx_val = 0
    for p in range(1, 6):
        batch = []
        for i in range(1, 11):
            tx_id = f"TXN_20261007_{((p - 1) * 10 + i):04d}"
            # Para as páginas 1 a 5, garantir status APROVADO para consolidar exatamente R$ 1,8M na liquidação líquida
            status = "APROVADO"
            batch.append({
                "transacao_id": tx_id,
                "lojista_id": lojistas[(p + i) % len(lojistas)],
                "adquirente": adquirentes[(p + i) % len(adquirentes)],
                "valor_centavos": valores_p1_p5[idx_val],
                "status": status,
                "data_hora_utc": "2026-10-07T02:15:00Z"
            })
            idx_val += 1
        base[p] = batch

    # Monta as páginas 6 a 10
    idx_val = 0
    for p in range(6, 11):
        batch = []
        for i in range(1, 11):
            tx_id = f"TXN_20261007_{((p - 1) * 10 + i):04d}"
            status = "APROVADO"
            batch.append({
                "transacao_id": tx_id,
                "lojista_id": lojistas[(p + i) % len(lojistas)],
                "adquirente": adquirentes[(p + i) % len(adquirentes)],
                "valor_centavos": valores_p6_p10[idx_val],
                "status": status,
                "data_hora_utc": "2026-10-07T02:45:00Z"
            })
            idx_val += 1
        base[p] = batch

    return base

# Base estática compartilhada
_DADOS_SIMULADOS = _gerar_base_transacoes()


class GatewayAPI:
    """
    Cliente / Engine de Simulação da API Adquirente com Política de Rate Limit.
    Pode ser instanciado em memória ou utilizado internamente por servidores HTTP.
    """
    def __init__(self, max_burst: int = MAX_REQUESTS_BURST, window_sec: float = WINDOW_SECONDS):
        self.max_burst = max_burst
        self.window_sec = window_sec
        self.historico_chamadas = []
        self.bloqueado_ate = 0.0

    def reset_limites(self):
        """Reseta o histórico de chamadas."""
        self.historico_chamadas.clear()
        self.bloqueado_ate = 0.0

    def consultar(self, cursor: int = 1) -> Dict[str, Any]:
        """
        Consulta transações da página identificada pelo cursor.
        Aplica verificação rigorosa de Rate Limiting.
        """
        agora = time.time()

        # Verifica se ainda está sob penalidade de bloqueio (Retry-After ativo)
        if agora < self.bloqueado_ate:
            segundos_restantes = max(1, int(self.bloqueado_ate - agora) + 1)
            return {
                "status_code": 429,
                "headers": {
                    "Retry-After": str(segundos_restantes),
                    "Content-Type": "application/json",
                    "X-RateLimit-Limit": str(self.max_burst),
                    "X-RateLimit-Remaining": "0"
                },
                "error": "Too Many Requests",
                "message": f"IP bloqueado temporariamente por excesso de velocidade. Aguarde {segundos_restantes}s."
            }

        # Remove chamadas que ocorreram fora da janela deslizante
        self.historico_chamadas = [t for t in self.historico_chamadas if agora - t < self.window_sec]

        # Verifica se estourou o limite de requisições na janela
        if len(self.historico_chamadas) >= self.max_burst:
            self.bloqueado_ate = agora + RETRY_AFTER_SECONDS
            return {
                "status_code": 429,
                "headers": {
                    "Retry-After": str(RETRY_AFTER_SECONDS),
                    "Content-Type": "application/json",
                    "X-RateLimit-Limit": str(self.max_burst),
                    "X-RateLimit-Remaining": "0"
                },
                "error": "Too Many Requests",
                "message": f"Limite de vazão excedido! Máximo de {self.max_burst} requisições em {self.window_sec}s. Penalidade: {RETRY_AFTER_SECONDS}s."
            }

        # Registra a requisição atual
        self.historico_chamadas.append(agora)
        restantes = self.max_burst - len(self.historico_chamadas)

        # Se o cursor solicitou uma página além do fim da base
        if cursor not in _DADOS_SIMULADOS:
            return {
                "status_code": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "X-RateLimit-Limit": str(self.max_burst),
                    "X-RateLimit-Remaining": str(restantes)
                },
                "data": [],
                "next_cursor": None,
                "total_registros": 0
            }

        batch = _DADOS_SIMULADOS[cursor]
        next_cursor = cursor + 1 if (cursor + 1) in _DADOS_SIMULADOS else None

        return {
            "status_code": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-RateLimit-Limit": str(self.max_burst),
                "X-RateLimit-Remaining": str(restantes)
            },
            "data": batch,
            "next_cursor": next_cursor,
            "total_registros": len(batch)
        }


# Instância singleton para simulação local sem necessidade de abrir porta TCP
instancia_api_global = GatewayAPI()


class APIHTTPRequestHandler(BaseHTTPRequestHandler):
    """Handler HTTP caso o usuário queira rodar o simulador como serviço de rede."""
    def log_message(self, format, *args):
        # Desativa logs verbosos automáticos do BaseHTTPRequestHandler
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/v1/transactions":
            params = parse_qs(parsed.query)
            cursor_str = params.get("cursor", ["1"])[0]
            try:
                cursor = int(cursor_str)
            except ValueError:
                cursor = 1

            resposta = instancia_api_global.consultar(cursor)
            status_code = resposta.get("status_code", 200)

            self.send_response(status_code)
            headers = resposta.get("headers", {})
            for k, v in headers.items():
                self.send_header(k, v)
            self.end_headers()

            corpo = json.dumps(resposta, indent=2).encode("utf-8")
            self.wfile.write(corpo)
        elif parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "UP", "servico": "FinPay Adquirente Mock"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Endpoint nao encontrado. Use /v1/transactions?cursor=1"}')


def iniciar_servidor_http(porta: int = 8080):
    """Inicia o servidor HTTP Standalone."""
    server_address = ("", porta)
    httpd = HTTPServer(server_address, APIHTTPRequestHandler)
    print(f"🚀 [FinPay Mock Gateway] Servidor HTTP ativo em http://localhost:{porta}/v1/transactions")
    print(f"⚠️  Rate Limit configurado: máximo de {MAX_REQUESTS_BURST} requisições rápidas.")
    print("Pressione Ctrl+C para encerrar o servidor.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor HTTP encerrado com sucesso.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        porta = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
        iniciar_servidor_http(porta)
    else:
        print("=" * 75)
        print("  FUCAPE Business School - Simulador de API Adquirente (FinPay)")
        print("=" * 75)
        print(f"Total de páginas cadastradas: {len(_DADOS_SIMULADOS)}")
        print(f"Total de transações: {sum(len(v) for v in _DADOS_SIMULADOS.values())}")
        
        # Teste de verificação dos valores das páginas 1 a 5
        centavos_p1_p5 = sum(tx["valor_centavos"] for p in range(1, 6) for tx in _DADOS_SIMULADOS[p])
        print(f"Volume financeiro Páginas 1 a 5: R$ {centavos_p1_p5 / 100:,.2f} (Alvo: R$ 1.800.000,00)")
        
        centavos_totais = sum(tx["valor_centavos"] for v in _DADOS_SIMULADOS.values() for tx in v)
        print(f"Volume financeiro Total (P1-P10): R$ {centavos_totais / 100:,.2f} (Alvo: R$ 3.500.000,00)")
        print("\nPara iniciar o servidor HTTP local:")
        print("  python3 simulador_api_parceira.py --server 8080")
        print("=" * 75)

#!/usr/bin/env python3
"""
==============================================================================
FUCAPE Business School - Disciplina: Modelagem Informacional
Aula 06: Modelagem para Sistemas NoSQL e Persistência Poliglota
Prof. Dr. Wagner Perin
==============================================================================
Script de Inicialização: O Monolito Relacional Problemático da OmniMarketplace

Objetivo Pedagógico:
Instanciar o banco de dados SQLite local 'omnimarketplace_monolito.db' a partir
do DDL 'monolito_problematico.sql' e guiar o estudante pelo diagnóstico empírico
das falhas de modelagem que causaram o colapso da plataforma na Black Friday.
==============================================================================
"""

import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQL_FILE = os.path.join(BASE_DIR, "monolito_problematico.sql")
DB_FILE = os.path.join(BASE_DIR, "omnimarketplace_monolito.db")

def criar_banco():
    print("=" * 78)
    print("  FUCAPE BUSINESS SCHOOL - ENGENHARIA DE DADOS E MODELAGEM INFORMACIONAL")
    print("  LABORATÓRIO AULA 06: DIAGNÓSTICO DO MONOLITO RELACIONAL PROBLEMÁTICO")
    print("=" * 78)

    if not os.path.exists(SQL_FILE):
        print(f"[ERRO CRÍTICO] Arquivo DDL não encontrado: {SQL_FILE}")
        sys.exit(1)

    print(f"[*] Lendo DDL e dados de teste de: {os.path.basename(SQL_FILE)}")
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        ddl_script = f.read()

    print(f"[*] Criando/Recriando banco de dados SQLite: {os.path.basename(DB_FILE)}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.executescript(ddl_script)
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERRO SQLITE] Falha ao executar DDL: {e}")
        conn.close()
        sys.exit(1)

    print("[✔] Banco de dados instanciado com sucesso!\n")
    print("-" * 78)
    print("  RESUMO DO BANCO DE DADOS CRIADO (ESTATÍSTICAS)")
    print("-" * 78)

    tabelas = [
        ("produtos", "Catálogo mestre de produtos"),
        ("atributos_eav", "Antipadrão Entity-Attribute-Value (Catálogo heterogêneo)"),
        ("clientes", "Cadastro de clientes e compradores"),
        ("pedidos", "Cabeçalho transacional de pedidos"),
        ("pedido_itens", "Itens adquiridos (base para recomendações)"),
        ("carrinhos_disco", "Carrinhos de compras persistidos em disco (sem TTL)")
    ]

    for tabela, desc in tabelas:
        cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
        qtd = cursor.fetchone()[0]
        print(f"  • Tabela '{tabela:<16}' : {qtd:>3} registros | {desc}")

    print("\n" + "=" * 78)
    print("  DIAGNÓSTICO ARQUITETURAL INICIAL — POR QUE ESSE MODELO COLAPSOU?")
    print("=" * 78)
    print("""
  [!] DOR 1: O ANTIPADRÃO EAV (Tabela 'atributos_eav')
      - Produtos de naturezas completamente distintas (TVs, Roupas, Pneus)
        foram forçados em um modelo chave-valor relacional.
      - Tente filtrar uma Smart TV por Voltagem, HDMI e Resolução simultaneamente.
        Quantos auto-JOINs serão necessários? O que acontece com 120M de linhas?

  [!] DOR 2: GRAFO RECURSIVO EM TABELAS TRANSACIONAIS (Tabela 'pedido_itens')
      - Para fazer recomendações sociais ("Quem comprou X também comprou Y"),
        o banco é forçado a realizar auto-JOINs recursivos na tabela de pedidos.
      - Em escala, isso gera table scans e starvation no checkout.

  [!] DOR 3: CARRINHO EFÊMERO PERSISTIDO NO DISCO (Tabela 'carrinhos_disco')
      - Carrinhos de compras são transitórios e voláteis. Gravá-los no disco rígido
        gera I/O lock massivo e exige rotinas pesadas de DELETE periódico.
      - Na Black Friday, 40.000 clientes receberam Timeout 504 por causa disso.
    """)
    print("=" * 78)
    print("  PRÓXIMO PASSO DO ESTUDANTE (MÉTODO CONSTRUTIVISTA):")
    print("  Abra o arquivo 'consultas_dor_relacional.sql' e execute as 3 consultas no")
    print(f"  banco '{os.path.basename(DB_FILE)}' para vivenciar o sofrimento técnico do RDBMS!")
    print("=" * 78)

    conn.close()

if __name__ == "__main__":
    criar_banco()

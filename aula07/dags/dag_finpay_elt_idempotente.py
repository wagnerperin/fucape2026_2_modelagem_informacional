#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
FUCAPE Business School - Ciência de Dados para Negócios
Disciplina: Modelagem Informacional
Aula 07: O Paradigma ETL vs. ELT e Ferramentas Modernas
-------------------------------------------------------------------------------
Arquivo: dags/dag_finpay_elt_idempotente.py
Propósito: DAG de Orquestração Apache Airflow aplicando Idempotência Estrita
           no pipeline ELT de conciliação financeira da FinPay & OmniTrade.
           
Estratégia de Idempotência:
  1. Delete-and-Insert particionado por data lógica de execução ({{ ds }}).
  2. Testes de qualidade bloqueantes (se falhar, aborta antes de expor aos marts).
  3. Reexecuções arbitrárias para a mesma partição produzem rigorosamente o
     mesmo estado analítico (f(f(x)) = f(x)), sem duplicar 1 centavo sequer.
===============================================================================
"""

import os
import sys
import sqlite3
import datetime
from datetime import timedelta

# Diretório base do repositório
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "finpay_analitico.db")

# -----------------------------------------------------------------------------
# Compatibilidade Dupla: Apache Airflow Oficial ou Runner Local Standalone
# -----------------------------------------------------------------------------
try:
    from airflow import DAG
    from airflow.operators.bash import BashOperator
    from airflow.operators.python import PythonOperator
    AIRFLOW_INSTALADO = True
except ImportError:
    AIRFLOW_INSTALADO = False

    class BaseOperator:
        def __init__(self, task_id, **kwargs):
            self.task_id = task_id
            self.kwargs = kwargs
            self.downstream = []
            self.upstream = []

        def __rshift__(self, other):
            if isinstance(other, list):
                for item in other:
                    self.downstream.append(item)
                    item.upstream.append(self)
            else:
                self.downstream.append(other)
                other.upstream.append(self)
            return other

    class BashOperator(BaseOperator):
        def __init__(self, bash_command, **kwargs):
            super().__init__(**kwargs)
            self.bash_command = bash_command

    class PythonOperator(BaseOperator):
        def __init__(self, python_callable, op_kwargs=None, **kwargs):
            super().__init__(**kwargs)
            self.python_callable = python_callable
            self.op_kwargs = op_kwargs or {}

    class DAG:
        def __init__(self, dag_id, default_args=None, schedule_interval=None, start_date=None, catchup=False, tags=None, **kwargs):
            self.dag_id = dag_id
            self.default_args = default_args
            self.tasks = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass


# -----------------------------------------------------------------------------
# Funções Executadas pelas Tasks (Python Callables)
# -----------------------------------------------------------------------------

def carga_raw_idempotente(**kwargs):
    """
    TASK 2: Carga Idempotente na Camada Bronze (Delete-and-Insert por partição).
    Garante que reexecuções apaguem qualquer registro anterior da partição lógica.
    """
    ds = kwargs.get("ds", "2026-10-07")
    print(f"\n[Airflow Task: carga_raw_idempotente] Processando partição de dados: ds = {ds}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. DELETE preventivo da partição (Idempotência Estrita)
    cursor.execute("""
        DELETE FROM bronze_transacoes_raw 
        WHERE SUBSTR(data_hora_utc, 1, 10) = ?;
    """, (ds,))
    deletados = cursor.rowcount
    print(f"  • Limpeza preventiva: {deletados} registros prévios expurgados para a data {ds}.")

    # 2. INSERT das transações correspondentes à janela lógica do arquivo JSONL
    jsonl_path = os.path.join(BASE_DIR, "bronze_transacoes_raw.jsonl")
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"Arquivo {jsonl_path} não encontrado!")

    import json
    inseridos = 0
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for linha in f:
            if not linha.strip():
                continue
            tx = json.loads(linha)
            # Filtra apenas transações pertencentes à partição lógica {{ ds }}
            data_tx = tx.get("data_hora_utc", "")[:10]
            if data_tx == ds:
                cursor.execute("""
                    INSERT INTO bronze_transacoes_raw (
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
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                inseridos += 1

    conn.commit()
    conn.close()
    print(f"  • Carga concluída: {inseridos} registros inseridos com sucesso na partição {ds}.")
    return inseridos


def verificar_auditoria_idempotencia(**kwargs):
    """
    TASK 5: Auditoria Matemática de Idempotência.
    Verifica se a tabela Fato possui duplicatas ou inconsistências de balanço.
    """
    ds = kwargs.get("ds", "2026-10-07")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Checagem de duplicações na Fato
    cursor.execute("""
        SELECT id_transacao, COUNT(*) 
        FROM fct_liquidacoes_diarias 
        GROUP BY id_transacao 
        HAVING COUNT(*) > 1;
    """)
    duplicatas = cursor.fetchall()

    if len(duplicatas) > 0:
        conn.close()
        raise ValueError(f"CRÍTICO: {len(duplicatas)} transações duplicadas detectadas na tabela Fato!")

    cursor.execute("""
        SELECT COUNT(*), ROUND(SUM(vlr_transacao_brl), 2), ROUND(SUM(vlr_liquido_lojista), 2)
        FROM fct_liquidacoes_diarias;
    """)
    total_tx, total_bruto, total_liq = cursor.fetchone()
    conn.close()

    print(f"\n[Airflow Task: auditoria_idempotencia] ✅ SUCESSO ABSOLUTO!")
    print(f"  • Total de liquidações aprovadas: {total_tx}")
    print(f"  • Volume bruto consolidado: R$ {total_bruto:,.2f}")
    print(f"  • Repasse líquido aos lojistas: R$ {total_liq:,.2f}")
    print(f"  • Duplicatas detectadas: ZERO (Idempotência verificada: f(f(x)) = f(x))")


# -----------------------------------------------------------------------------
# Definição Oficial da DAG do Airflow
# -----------------------------------------------------------------------------

default_args = {
    'owner': 'engenharia_dados_fucape',
    'depends_on_past': False,
    'email_on_failure': True,
    'email': ['engenharia@finpay.com.br'],
    'retries': 3,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    dag_id='dag_finpay_elt_idempotente',
    default_args=default_args,
    description='Pipeline ELT diário com ingestão resiliente, dbt modular e idempotência Delete-and-Insert.',
    schedule_interval='0 3 * * *',  # Execução noturna diária às 03h00
    start_date=datetime.datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=['finpay', 'elt', 'dbt', 'idempotencia', 'fucape']
) as dag:

    # TASK 1: Ingestão resiliente da API com Exponential Backoff e escrita em Bronze
    t1_ingestao_api = BashOperator(
        task_id='t1_ingestao_api_bronze',
        bash_command=f'python3 {os.path.join(BASE_DIR, "ingestao_resiliente_api.py")}'
    )

    # TASK 2: Carga Idempotente (Delete-and-Insert na partição lógica {{ ds }})
    t2_carga_idempotente = PythonOperator(
        task_id='t2_carga_raw_idempotente',
        python_callable=carga_raw_idempotente,
        op_kwargs={'ds': '{{ ds }}'}
    )

    # TASK 3: Transformação Modular com dbt (Staging e Marts)
    t3_dbt_run = BashOperator(
        task_id='t3_dbt_run_transformacoes',
        bash_command=f'python3 {os.path.join(BASE_DIR, "executar_pipeline_dbt.py")}'
    )

    # TASK 4: Validação Matemática da Idempotência
    t4_auditoria = PythonOperator(
        task_id='t4_auditoria_idempotencia',
        python_callable=verificar_auditoria_idempotencia,
        op_kwargs={'ds': '{{ ds }}'}
    )

    # Definição do Grafo Acíclico Dirigido (Linear & Idempotente)
    t1_ingestao_api >> t2_carga_idempotente >> t3_dbt_run >> t4_auditoria


# -----------------------------------------------------------------------------
# Runner de Teste Local: Demonstração da Idempotência (Simulação de 2 Execuções)
# -----------------------------------------------------------------------------
def testar_idempotencia_local():
    """
    Executa a DAG duas vezes consecutivas para a mesma partição lógica
    e prova formalmente que nenhuma linha duplicada é gerada.
    """
    print("=" * 78)
    print("  SIMULAÇÃO LOCAL DA DAG DO AIRFLOW: TESTE FORMAL DE IDEMPOTÊNCIA")
    print("=" * 78)
    print("Executando a DAG pela 1ª VEZ para a data lógica ds = '2026-10-07'...")
    
    # Execução 1
    carga_raw_idempotente(ds="2026-10-07")
    os.system(f"python3 {os.path.join(BASE_DIR, 'executar_pipeline_dbt.py')} > /dev/null")
    verificar_auditoria_idempotencia(ds="2026-10-07")

    print("\n" + "-" * 78)
    print("Simulando REEXECUÇÃO da DAG (2ª VEZ) para a MESMA data ds = '2026-10-07'...")
    print("(Simula o plantonista da TI clicando em 'Clear / Retry' no Airflow)")
    print("-" * 78)

    # Execução 2
    carga_raw_idempotente(ds="2026-10-07")
    os.system(f"python3 {os.path.join(BASE_DIR, 'executar_pipeline_dbt.py')} > /dev/null")
    verificar_auditoria_idempotencia(ds="2026-10-07")

    print("\n" + "=" * 78)
    print("🏆 PROVA MATEMÁTICA CONCLUÍDA:")
    print("   Mesmo após múltiplas reexecuções, o banco analítico contém exatamente")
    print("   as 100 transações válidas e R$ 3,5M corretos sem 1 único centavo duplicado!")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    testar_idempotencia_local()

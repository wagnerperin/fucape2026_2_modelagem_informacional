# Desafios e Reflexões (Aula 05)

## Dilema 1: Dimensão Combinada (Cliente-Loja)
**Cenário:** O estagiário sugeriu criar uma única dimensão chamada `Dim_ClienteLoja` para evitar 2 joins, já que todo cliente compra em uma loja.
**Reflexão:** Por que isso é um erro grave de modelagem dimensional?
**Gabarito Socrático:** O Produto Cartesiano. Clientes e Lojas são independentes. Um cliente pode comprar na loja SP hoje e na loja RJ amanhã. Se combinarmos, e tivermos 1 milhão de clientes e 100 lojas, a dimensão combinada poderia explodir para 100 milhões de registros, além de dificultar o reaproveitamento da `Dim_Cliente` e `Dim_Loja` em outros processos (ex: Fato_AcessosSite).

## Dilema 2: A Armadilha da Margem (Fatos Não-aditivos)
**Cenário:** O painel de BI está mostrando que a Margem de Lucro Média de eletrônicos é 55%, mas o financeiro afirma que foi de 30%. Ao analisar a query, viu-se um `AVG( (valor_venda - custo) / valor_venda )`.
**Reflexão:** Qual é a natureza matemática do erro de tirar média de porcentagens?
**Gabarito Socrático:** Taxas e proporções são *Fatos Não-Aditivos*. Você não pode somar nem tirar média aritmética simples de margens, pois isso desconsidera o "peso" absoluto de cada venda (uma balinha de R$1 com 90% de margem e uma TV de R$ 5000 com 10% de margem não geram uma média real de 50%). O BI sempre deve calcular `SUM(Lucro)/SUM(Venda)`.

## Dilema 3: A Falta do Grão Diário (Black Friday)
**Cenário:** Uma empresa decidiu economizar espaço no Data Warehouse agregando a Fato para a granularidade "Mensal" em vez de "Linha do Cupom (Diária)".
**Reflexão:** O que a diretoria perderá de capacidade analítica?
**Gabarito Socrático:** A empresa ficará cega para eventos intra-mês (ex: Black Friday, Dia das Mães, impacto de uma propaganda na TV em um dia específico). E pior: não poderá analisar cestas de compras (quais produtos são vendidos juntos no mesmo cupom). Agregações mensais devem ser tabelas auxiliares (Aggregate Tables), mas nunca substituir o grão atômico.

## Dilema 4: O Fan Trap e Chasm Trap (Produto Cartesiano em Análises)
**Cenário:** Um analista fez um SELECT juntando a Tabela Fato de Vendas e a Tabela Fato de Metas de Loja na mesma query. O resultado das vendas foi multiplicado acidentalmente.
**Reflexão:** Por que as ferramentas OLAP resolvem as Fatos separadamente (em *multipass queries*)?
**Gabarito Socrático:** Ligar duas tabelas de fatos através das dimensões (Conformed Dimensions) numa única query SQL tradicional pode causar "Double Counting" (contagem em dobro), pois as granularidades são diferentes. A prática correta (Drill Across) exige agregar (GROUP BY) as Vendas primeiro, agregar as Metas depois, e só então cruzar os resultados no nível da Loja.

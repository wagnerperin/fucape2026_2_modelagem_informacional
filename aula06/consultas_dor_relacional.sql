-- ==============================================================================
-- FUCAPE Business School - Disciplina: Modelagem Informacional
-- Aula 06: Modelagem para Sistemas NoSQL e Persistência Poliglota
-- Prof. Dr. Wagner Perin
-- ==============================================================================
-- ROTEIRO CONSTRUTIVISTA: AS 3 CONSULTAS DA DOR RELACIONAL
-- Execute este script contra o banco 'omnimarketplace_monolito.db'
-- Comando terminal: sqlite3 omnimarketplace_monolito.db < consultas_dor_relacional.sql
-- ==============================================================================

.headers on
.mode column
.width 10 25 20 12 15 15

-- ==============================================================================
-- CONSULTA DOR 1: O PESADELO DO CATÁLOGO HETEROGÊNEO (ANTIPADRÃO EAV)
-- ==============================================================================
-- Desafio de Negócio: O cliente entra na OmniMarketplace e busca no filtro:
-- "Smart TVs da categoria 'Eletrônicos' que sejam Bivolt E tenham 4 portas HDMI E resolução 4K (3840 x 2160)"
--
-- Por que dói no Relacional?
-- No modelo relacional EAV (Entity-Attribute-Value), cada par (chave, valor) é
-- uma linha isolada na tabela 'atributos_eav'. Para combinar 3 filtros do mesmo
-- produto, o motor SQL precisa realizar 3 auto-JOINs na mesmíssima tabela!
-- ==============================================================================

SELECT 
    p.sku,
    p.nome AS produto,
    p.preco,
    a_volt.valor_atributo AS voltagem,
    a_hdmi.valor_atributo AS portas_hdmi,
    a_res.valor_atributo AS resolucao
FROM produtos p
JOIN atributos_eav a_volt 
  ON p.id_produto = a_volt.id_produto 
 AND a_volt.chave_atributo = 'voltagem' 
 AND a_volt.valor_atributo = 'Bivolt'
JOIN atributos_eav a_hdmi 
  ON p.id_produto = a_hdmi.id_produto 
 AND a_hdmi.chave_atributo = 'hdmi' 
 AND a_hdmi.valor_atributo = '4'
JOIN atributos_eav a_res 
  ON p.id_produto = a_res.id_produto 
 AND a_res.chave_atributo = 'resolucao' 
 AND a_res.valor_atributo = '3840 x 2160'
WHERE p.categoria = 'Eletrônicos';

-- ------------------------------------------------------------------------------
-- [PROVOCAÇÃO SOCRÁTICA PARA OS ESTUDANTES - DOR 1]:
-- 1. Quantos auto-JOINs foram necessários para apenas 3 filtros de busca?
-- 2. Se o usuário pudesse filtrar por 8 atributos (marca, cor, hz, bluetooth, hdr...),
--    quantos JOINs seriam gerados dinamicamente na query?
-- 3. Projeção de Escala: Com 8 produtos na base de teste, a query roda em 1ms.
--    Mas se a tabela 'atributos_eav' tiver 120 MILHÕES de linhas e 200.000 clientes
--    estiverem aplicando filtros simultâneos na Black Friday, o que acontece com a CPU
--    e a memória RAM do servidor PostgreSQL? Por que o tempo de busca disparou para 28 segundos?
-- 4. Por que os engenheiros não usaram simplesmente colunas tradicionais na tabela 'produtos'?
--    (Dica: Pense na esparsidade de colunas NULL entre uma Smart TV e uma Camiseta Esportiva).
-- ------------------------------------------------------------------------------


-- ==============================================================================
-- CONSULTA DOR 2: O TRAVAMENTO DO MOTOR DE RECOMENDAÇÃO EM REDE
-- ==============================================================================
-- Desafio de Negócio: O time de Growth Marketing quer exibir na página de produto:
-- "Quem comprou a Smart TV 65 (comprada por Lucas - u001) também comprou estes outros produtos..."
-- (Excluindo o que o próprio Lucas já comprou e ordenando pela força de recomendação).
--
-- Por que dói no Relacional?
-- O RDBMS não possui ponteiros diretos de conexão entre entidades. Ele precisa
-- executar sucessivos auto-JOINs na tabela transacional de pedidos e itens,
-- disparando múltiplos Scans, Sorts e deduplicações (DISTINCT) em tempo de execução.
-- ==============================================================================

.width 15 35 20

SELECT 
    prod_rec.sku,
    prod_rec.nome AS produto_recomendado,
    COUNT(DISTINCT ped_outros.id_cliente) AS forca_recomendacao
FROM pedidos ped_alvo
JOIN pedido_itens item_alvo 
    ON ped_alvo.id_pedido = item_alvo.id_pedido
JOIN pedido_itens item_comum 
    ON item_alvo.id_produto = item_comum.id_produto 
   AND item_alvo.id_pedido <> item_comum.id_pedido
JOIN pedidos ped_outros 
    ON item_comum.id_pedido = ped_outros.id_pedido 
   AND ped_outros.id_cliente <> ped_alvo.id_cliente
JOIN pedido_itens item_rec 
    ON ped_outros.id_pedido = item_rec.id_pedido 
   AND item_rec.id_produto <> item_comum.id_produto
JOIN produtos prod_rec 
    ON item_rec.id_produto = prod_rec.id_produto
WHERE ped_alvo.id_cliente = 'u001'
  AND prod_rec.id_produto NOT IN (
      SELECT sub_item.id_produto 
      FROM pedidos sub_ped 
      JOIN pedido_itens sub_item ON sub_ped.id_pedido = sub_item.id_pedido 
      WHERE sub_ped.id_cliente = 'u001'
  )
GROUP BY prod_rec.id_produto, prod_rec.sku, prod_rec.nome
ORDER BY forca_recomendacao DESC;

-- ------------------------------------------------------------------------------
-- [PROVOCAÇÃO SOCRÁTICA PARA OS ESTUDANTES - DOR 2]:
-- 1. Analise o FROM e os JOINs acima: Quantas vezes as tabelas 'pedidos' e 'pedido_itens'
--    tiveram que ser relidas e cruzadas consigo mesmas para responder a um único salto social?
-- 2. Se quiséssemos expandir a recomendação para 2 ou 3 graus de distância
--    ("Amigos de amigos que compraram"), o que aconteceria com a complexidade do SQL?
-- 3. Projeção de Escala: Na Black Friday, as tabelas 'pedidos' e 'pedido_itens' recebem
--    milhares de INSERTs por segundo do checkout. Quando essa query pesada de recomendação
--    roda concorrentemente, que tipo de lock e contenção (Starvation) ela provoca?
-- 4. Como um banco orientado a grafos (Neo4j) resolve isso através de Index-Free Adjacency?
-- ------------------------------------------------------------------------------


-- ==============================================================================
-- CONSULTA DOR 3: O GARGALO DE I/O EM DISCO DOS CARRINHOS EFÊMEROS
-- ==============================================================================
-- Desafio de Negócio: Mais de 40.000 clientes adicionam e removem itens dos carrinhos.
-- Como foram persistidos em uma tabela relacional tradicional ('carrinhos_disco'),
-- esses dados transitórios exigem escrita imediata em disco rígido (WAL/Flush).
-- Além disso, para expurgar carrinhos abandonados há mais de 2 horas, o DBA é obrigado
-- a agendar um comando DELETE massivo em lote.
-- ==============================================================================

.width 12 12 10 10 22 18 25

-- Passo 3.1: Auditoria dos Carrinhos Gravados no Disco
-- (Simulando o momento da análise às 20:00 do dia 2026-11-27)
SELECT 
    c.id_carrinho,
    c.id_cliente,
    p.sku,
    c.quantidade,
    c.data_criacao,
    ROUND((julianday('2026-11-27 20:00:00') - julianday(c.data_criacao)) * 24, 2) AS horas_ativo,
    CASE 
        WHEN ROUND((julianday('2026-11-27 20:00:00') - julianday(c.data_criacao)) * 24, 2) > 2.0 
        THEN '[EXPIRADO] Lixo em Disco' 
        ELSE '[ATIVO] Sessao Aberta' 
    END AS status_ciclo_vida
FROM carrinhos_disco c
JOIN produtos p ON c.id_produto = p.id_produto;

-- Passo 3.2: O CRON Job Destrutivo (DELETE em Massa de Carrinhos Expirados)
-- Em produção, este script roda de hora em hora travando as páginas do disco:
DELETE FROM carrinhos_disco
WHERE ROUND((julianday('2026-11-27 20:00:00') - julianday(data_criacao)) * 24, 2) > 2.0;

-- Passo 3.3: Verificando o que sobrou após o expurgo forçado
SELECT 
    c.id_carrinho,
    c.id_cliente,
    p.sku,
    c.quantidade,
    c.data_criacao,
    'Remanescente Ativo' AS status
FROM carrinhos_disco c
JOIN produtos p ON c.id_produto = p.id_produto;

-- ------------------------------------------------------------------------------
-- [PROVOCAÇÃO SOCRÁTICA PARA OS ESTUDANTES - DOR 3]:
-- 1. O que acontece com um disco SSD/NVMe quando 200.000 usuários alteram carrinhos
--    a cada segundo, gerando milhões de escritas que serão descartadas logo depois?
-- 2. Em um SGBD relacional corporativo (como PostgreSQL/MySQL), o comando DELETE
--    libera espaço físico no arquivo de dados imediatamente?
--    (Pesquise: "Dead Tuples", "PostgreSQL VACUUM", "Write Amplification").
-- 3. Quando o script de DELETE em massa é disparado contra a tabela 'carrinhos_disco'
--    durante o pico de tráfego, o que acontece com os clientes que estão tentando
--    adicionar itens ao carrinho naquele exato milissegundo? (Pense em Row Locks e Table Locks).
-- 4. Como o Redis elimina completamente o disco, o DELETE manual e os locks,
--    usando apenas memória RAM e expiração atômica por TTL (Time-To-Live)?
-- ==============================================================================

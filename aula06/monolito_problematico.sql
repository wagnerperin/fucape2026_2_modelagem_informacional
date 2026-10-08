-- ==============================================================================
-- O MONOLITO RELACIONAL PROBLEMÁTICO DA OMNIMARKETPLACE (AULA 06)
-- FUCAPE Business School - Disciplina: Modelagem Informacional
-- Prof. Dr. Wagner Perin
-- ==============================================================================
-- Contexto: Banco de dados relacional monolítico (PostgreSQL / SQLite) que entrou
-- em colapso na Black Friday devido à sobrecarga de três cargas de trabalho
-- inadequadas para a 3ª Forma Normal:
--   1. Catálogo heterogêneo modelado em EAV (Entity-Attribute-Value)
--   2. Grafo de recomendação social via auto-JOINs recursivos em pedidos
--   3. Carrinho efêmero de compras gravado diretamente em disco (I/O intensivo)
-- ==============================================================================

-- 1. TABELA DE PRODUTOS BÁSICOS
DROP TABLE IF EXISTS carrinhos_disco;
DROP TABLE IF EXISTS pedido_itens;
DROP TABLE IF EXISTS pedidos;
DROP TABLE IF EXISTS atributos_eav;
DROP TABLE IF EXISTS produtos;
DROP TABLE IF EXISTS clientes;

CREATE TABLE produtos (
    id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    preco REAL NOT NULL,
    categoria TEXT NOT NULL
);

-- 2. TABELA NO ANTIPADRÃO EAV (Entity-Attribute-Value)
-- Criada pelos desenvolvedores para evitar centenas de colunas NULL quando
-- produtos de categorias diferentes exigem especificações técnicas distintas.
CREATE TABLE atributos_eav (
    id_atributo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_produto INTEGER NOT NULL,
    chave_atributo TEXT NOT NULL,
    valor_atributo TEXT NOT NULL,
    FOREIGN KEY (id_produto) REFERENCES produtos(id_produto)
);

-- 3. TABELA DE CLIENTES
CREATE TABLE clientes (
    id_cliente TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    email TEXT NOT NULL
);

-- 4. TABELA DE PEDIDOS HISTÓRICOS (OLTP Transacional)
CREATE TABLE pedidos (
    id_pedido INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente TEXT NOT NULL,
    data_pedido TEXT NOT NULL,
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
);

-- 5. TABELA DE ITENS DO PEDIDO
CREATE TABLE pedido_itens (
    id_item INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pedido INTEGER NOT NULL,
    id_produto INTEGER NOT NULL,
    quantidade INTEGER NOT NULL,
    FOREIGN KEY (id_pedido) REFERENCES pedidos(id_pedido),
    FOREIGN KEY (id_produto) REFERENCES produtos(id_produto)
);

-- 6. TABELA DE CARRINHOS DE COMPRAS GRAVADOS EM DISCO (O Gargalo de I/O)
-- Cada clique de "Adicionar ao Carrinho" gera INSERT/UPDATE no disco rígido sem TTL
CREATE TABLE carrinhos_disco (
    id_carrinho INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente TEXT NOT NULL,
    id_produto INTEGER NOT NULL,
    quantidade INTEGER NOT NULL,
    data_criacao TEXT NOT NULL,
    data_atualizacao TEXT NOT NULL,
    FOREIGN KEY (id_produto) REFERENCES produtos(id_produto)
);

-- ==============================================================================
-- CARGA DE DADOS SINTÉTICOS
-- ==============================================================================

-- Carga de Produtos (Catálogo com categorias radicalmente distintas)
INSERT INTO produtos (id_produto, sku, nome, preco, categoria) VALUES
(1, 'TV-4K-65', 'Smart TV 65 polegadas 4K Ultra HD', 3500.00, 'Eletrônicos'),
(2, 'TV-FHD-50', 'Smart TV 50 polegadas Full HD', 2100.00, 'Eletrônicos'),
(3, 'TV-8K-75', 'Smart TV 75 polegadas 8K QLED Pro', 7999.00, 'Eletrônicos'),
(4, 'CAM-ESP-M', 'Camiseta Esportiva Alta Performance', 89.90, 'Vestuário'),
(5, 'PNEU-205-55', 'Pneu Automotivo Aro 16 205/55', 450.00, 'Autopeças'),
(6, 'SOUNDBAR-90', 'Soundbar 90W Bluetooth Subwoofer', 800.00, 'Eletrônicos'),
(7, 'SMART-PRO-128', 'Smartphone Pro 128GB 5G', 4200.00, 'Eletrônicos'),
(8, 'SUPORTE-TV-ART', 'Suporte Articulado para TV 32 a 75', 150.00, 'Acessórios');

-- Carga do Antipadrão EAV (Atributos heterogêneos sem tipagem estrita)
-- TV-4K-65 (id 1)
INSERT INTO atributos_eav (id_produto, chave_atributo, valor_atributo) VALUES
(1, 'voltagem', 'Bivolt'),
(1, 'hdmi', '4'),
(1, 'resolucao', '3840 x 2160'),
(1, 'taxa_atualizacao', '120Hz');

-- TV-FHD-50 (id 2)
INSERT INTO atributos_eav (id_produto, chave_atributo, valor_atributo) VALUES
(2, 'voltagem', '110V'),
(2, 'hdmi', '3'),
(2, 'resolucao', '1920 x 1080');

-- TV-8K-75 (id 3)
INSERT INTO atributos_eav (id_produto, chave_atributo, valor_atributo) VALUES
(3, 'voltagem', 'Bivolt'),
(3, 'hdmi', '4'),
(3, 'resolucao', '7680 x 4320'),
(3, 'taxa_atualizacao', '144Hz');

-- CAM-ESP-M (id 4)
INSERT INTO atributos_eav (id_produto, chave_atributo, valor_atributo) VALUES
(4, 'tamanho', 'M'),
(4, 'cor', 'Azul'),
(4, 'composicao_textil', '100% Poliéster'),
(4, 'protecao_uv', 'Sim');

-- PNEU-205-55 (id 5)
INSERT INTO atributos_eav (id_produto, chave_atributo, valor_atributo) VALUES
(5, 'aro', '16'),
(5, 'indice_carga', '91'),
(5, 'perfil', '55'),
(5, 'durabilidade', '60000 km');

-- SOUNDBAR-90 (id 6)
INSERT INTO atributos_eav (id_produto, chave_atributo, valor_atributo) VALUES
(6, 'potencia', '90W'),
(6, 'bluetooth', 'Sim'),
(6, 'canais', '2.1');

-- SMART-PRO-128 (id 7)
INSERT INTO atributos_eav (id_produto, chave_atributo, valor_atributo) VALUES
(7, 'armazenamento', '128GB'),
(7, 'ram', '8GB'),
(7, 'conectividade', '5G');

-- SUPORTE-TV-ART (id 8)
INSERT INTO atributos_eav (id_produto, chave_atributo, valor_atributo) VALUES
(8, 'articulacao', '180 graus'),
(8, 'peso_suportado', '50kg');

-- Carga de Clientes
INSERT INTO clientes (id_cliente, nome, email) VALUES
('u001', 'Lucas Silva', 'lucas.silva@aluno.fucape.br'),
('u002', 'Beatriz Santos', 'beatriz.santos@aluno.fucape.br'),
('u003', 'Carlos Eduardo', 'carlos.eduardo@aluno.fucape.br'),
('u004', 'Daniela Rocha', 'daniela.rocha@aluno.fucape.br'),
('u005', 'Eduardo Lima', 'eduardo.lima@aluno.fucape.br');

-- Carga de Pedidos Históricos
INSERT INTO pedidos (id_pedido, id_cliente, data_pedido) VALUES
(101, 'u001', '2026-11-20 14:32:00'),
(102, 'u002', '2026-11-21 09:15:00'),
(103, 'u003', '2026-11-22 18:40:00'),
(104, 'u004', '2026-11-23 11:05:00'),
(105, 'u005', '2026-11-24 16:50:00');

-- Carga de Itens de Pedido (Padrão de compra cruzada para o Grafo de Recomendação)
-- Lucas (u001): Comprou TV 65 (id 1)
INSERT INTO pedido_itens (id_pedido, id_produto, quantidade) VALUES (101, 1, 1);

-- Beatriz (u002): Comprou TV 65 (id 1) e Soundbar 90W (id 6)
INSERT INTO pedido_itens (id_pedido, id_produto, quantidade) VALUES (102, 1, 1);
INSERT INTO pedido_itens (id_pedido, id_produto, quantidade) VALUES (102, 6, 1);

-- Carlos (u003): Comprou Camiseta Esportiva (id 4) e Pneu (id 5)
INSERT INTO pedido_itens (id_pedido, id_produto, quantidade) VALUES (103, 4, 2);
INSERT INTO pedido_itens (id_pedido, id_produto, quantidade) VALUES (103, 5, 4);

-- Daniela (u004): Comprou TV 65 (id 1), Soundbar (id 6) e Suporte TV (id 8)
INSERT INTO pedido_itens (id_pedido, id_produto, quantidade) VALUES (104, 1, 1);
INSERT INTO pedido_itens (id_pedido, id_produto, quantidade) VALUES (104, 6, 1);
INSERT INTO pedido_itens (id_pedido, id_produto, quantidade) VALUES (104, 8, 1);

-- Eduardo (u005): Comprou TV 65 (id 1) e Suporte TV (id 8)
INSERT INTO pedido_itens (id_pedido, id_produto, quantidade) VALUES (105, 1, 1);
INSERT INTO pedido_itens (id_pedido, id_produto, quantidade) VALUES (105, 8, 1);

-- Carga de Carrinhos Gravados no Disco (Mistura de ativos e abandonados)
-- Note as datas: carrinhos com mais de 2 horas deveriam ter sido expurgados,
-- mas ocupam espaço no disco e exigem DELETEs manuais pesados.
INSERT INTO carrinhos_disco (id_carrinho, id_cliente, id_produto, quantidade, data_criacao, data_atualizacao) VALUES
(1, 'u001', 6, 1, '2026-11-27 19:45:00', '2026-11-27 19:50:00'), -- Recente (sessão ativa)
(2, 'u002', 8, 2, '2026-11-27 19:55:00', '2026-11-27 19:55:00'), -- Recente (sessão ativa)
(3, 'u003', 1, 1, '2026-11-27 14:00:00', '2026-11-27 14:10:00'), -- Abandonado há quase 6h
(4, 'u004', 4, 3, '2026-11-27 11:30:00', '2026-11-27 11:35:00'), -- Abandonado há mais de 8h
(5, 'u005', 7, 1, '2026-11-26 22:15:00', '2026-11-26 22:15:00'), -- Abandonado há quase 24h
(6, 'anon_991', 5, 2, '2026-11-25 08:00:00', '2026-11-25 08:02:00'), -- Abandonado há mais de 2 dias
(7, 'anon_992', 1, 1, '2026-11-25 15:20:00', '2026-11-25 15:21:00'); -- Abandonado há mais de 2 dias

// Limpando banco de dados (CUIDADO em produção!)
MATCH (n) DETACH DELETE n;

// 1. Criação de Nós (Clientes, Produtos, Categorias)
CREATE 
  (c1:Cliente {id: 'u001', nome: 'Lucas'}),
  (c2:Cliente {id: 'u002', nome: 'Beatriz'}),
  (c3:Cliente {id: 'u003', nome: 'Carlos'}),
  
  (p1:Produto {sku: 'TV-4K-65', nome: 'Smart TV 65"'}),
  (p2:Produto {sku: 'CAM-ESP-M', nome: 'Camiseta Esportiva'}),
  (p3:Produto {sku: 'SOUNDBAR-90', nome: 'Soundbar 90W'}),
  
  (cat1:Categoria {nome: 'Eletrônicos'});

// 2. Criação de Relacionamentos (Arestas)
CREATE
  (c1)-[:COMPROU {data: '2026-11-27', valor: 3500.00}]->(p1),
  (c2)-[:COMPROU {data: '2026-11-27', valor: 3500.00}]->(p1),
  (c2)-[:COMPROU {data: '2026-11-28', valor: 800.00}]->(p3),
  (c3)-[:COMPROU {data: '2026-11-28', valor: 89.90}]->(p2),
  
  (p1)-[:PERTENCE_A]->(cat1),
  (p3)-[:PERTENCE_A]->(cat1),
  
  (c1)-[:SEGUE]->(c2);

// 3. Consulta de Recomendação Social (Quem comprou X também comprou Y)
// Desafio: "Recomendar produtos para o Lucas (u001), baseando-se em outros clientes que compraram os mesmos produtos que ele, mas recomendando produtos que Lucas ainda não comprou."
MATCH (clienteAlvo:Cliente {id: 'u001'})-[:COMPROU]->(produtoComum:Produto)<-[:COMPROU]-(outroCliente:Cliente)
MATCH (outroCliente)-[:COMPROU]->(recomendacao:Produto)
WHERE NOT (clienteAlvo)-[:COMPROU]->(recomendacao)
RETURN recomendacao.nome AS ProdutoRecomendado, count(outroCliente) AS ForcaRecomendacao
ORDER BY ForcaRecomendacao DESC;

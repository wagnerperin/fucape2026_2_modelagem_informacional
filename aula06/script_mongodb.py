import json

class MockMongoDB:
    def __init__(self):
        self.collections = {}

    def insert_many(self, collection_name, documents):
        if collection_name not in self.collections:
            self.collections[collection_name] = []
        self.collections[collection_name].extend(documents)
        print(f"[{collection_name}] {len(documents)} documentos inseridos com sucesso.")

    def find(self, collection_name, query=None):
        if collection_name not in self.collections:
            return []
        
        results = []
        for doc in self.collections[collection_name]:
            match = True
            if query:
                for key, val in query.items():
                    # Suporte a query em campos aninhados usando notação de ponto
                    keys = key.split('.')
                    target = doc
                    for k in keys:
                        target = target.get(k, {}) if isinstance(target, dict) else None
                    if target != val:
                        match = False
                        break
            if match:
                results.append(doc)
        return results

if __name__ == "__main__":
    db = MockMongoDB()
    
    # Carregando catálogo heterogêneo
    with open("catalogo_produtos.json", "r", encoding="utf-8") as f:
        catalogo = json.load(f)
        
    db.insert_many("produtos", catalogo)
    
    # Query: Buscar TV pela resolução (atributo aninhado, sem JOIN)
    print("\n--- Buscando Smart TVs 4K ---")
    resultados = db.find("produtos", {"especificacoes_tecnicas.resolucao": "3840 x 2160"})
    for r in resultados:
        print(f"Encontrado: {r['nome']} (SKU: {r['sku']}) - {r['especificacoes_tecnicas']}")
        
    # Query: Buscar Pneu pelo aro (atributo aninhado totalmente diferente)
    print("\n--- Buscando Pneus Aro 16 ---")
    resultados_pneu = db.find("produtos", {"especificacoes_tecnicas.aro": 16})
    for r in resultados_pneu:
        print(f"Encontrado: {r['nome']} (SKU: {r['sku']}) - {r['especificacoes_tecnicas']}")

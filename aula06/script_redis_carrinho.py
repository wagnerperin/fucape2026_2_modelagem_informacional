import time

class MockRedis:
    def __init__(self):
        self.store = {}
        self.ttl_store = {}

    def hset(self, key, field, value):
        if key not in self.store:
            self.store[key] = {}
        self.store[key][field] = value
        print(f"[Redis] HSET {key} {field} {value}")

    def hgetall(self, key):
        self._check_ttl(key)
        return self.store.get(key, {})

    def expire(self, key, seconds):
        self.ttl_store[key] = time.time() + seconds
        print(f"[Redis] EXPIRE {key} in {seconds} segundos")

    def _check_ttl(self, key):
        if key in self.ttl_store and time.time() > self.ttl_store[key]:
            if key in self.store:
                del self.store[key]
            del self.ttl_store[key]
            print(f"[Redis] Chave {key} expurgada (TTL expirado).")

if __name__ == "__main__":
    cache = MockRedis()
    
    session_token = "sess_998877"
    cart_key = f"cart:{session_token}"
    
    print("\n--- Adicionando Itens ao Carrinho (Memória) ---")
    cache.hset(cart_key, "TV-4K-65", "1")
    cache.hset(cart_key, "SOUNDBAR-90", "1")
    
    # TTL de 2 horas (7200 segundos). Simulado com 1 segundo para teste rápido.
    cache.expire(cart_key, 1) 
    
    print("\n--- Consultando Carrinho Imediatamente ---")
    print(cache.hgetall(cart_key))
    
    print("\n--- Simulando abandono do carrinho (Aguardando 2 segundos) ---")
    time.sleep(2)
    
    print("\n--- Consultando Carrinho Após Abandono (TTL) ---")
    print(cache.hgetall(cart_key))
    
    # Cálculo de memória
    qtd_carrinhos = 200000
    tamanho_por_carrinho = 500  # bytes
    memoria_total_bytes = qtd_carrinhos * tamanho_por_carrinho
    memoria_total_mb = memoria_total_bytes / (1024 * 1024)
    print(f"\n--- Estimativa de Consumo de RAM na Black Friday ---")
    print(f"200.000 carrinhos * 500 bytes = {memoria_total_mb:.2f} MB de RAM.")

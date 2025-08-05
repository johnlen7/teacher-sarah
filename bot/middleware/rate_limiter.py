from typing import Dict, List
import time

class RateLimiter:
    def __init__(self, max_requests: int = 10, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.users: Dict[int, List[float]] = {}
    
    async def check_limit(self, user_id: int) -> bool:
        """Verifica se usuário excedeu limite"""
        now = time.time()
        
        if user_id not in self.users:
            self.users[user_id] = []
        
        # Limpar requisições antigas
        self.users[user_id] = [
            timestamp for timestamp in self.users[user_id]
            if now - timestamp < self.window
        ]
        
        # Verificar limite
        if len(self.users[user_id]) >= self.max_requests:
            return False
        
        # Adicionar requisição atual
        self.users[user_id].append(now)
        return True

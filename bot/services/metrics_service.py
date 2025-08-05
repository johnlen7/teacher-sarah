import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class Metrics:
    total_messages: int = 0
    total_voice: int = 0
    total_errors: int = 0
    avg_response_time: float = 0
    daily_users: set = field(default_factory=set)
    response_times: List[float] = field(default_factory=list)
    
class MetricsService:
    def __init__(self):
        self.metrics = Metrics()
        self.start_time = time.time()
    
    async def track_message(self, user_id: int, message_type: str, response_time: float):
        """Registra métricas de mensagem"""
        self.metrics.total_messages += 1
        
        if message_type == 'voice':
            self.metrics.total_voice += 1
        
        self.metrics.daily_users.add(user_id)
        self.metrics.response_times.append(response_time)
        
        # Calcular média móvel
        if len(self.metrics.response_times) > 100:
            self.metrics.response_times = self.metrics.response_times[-100:]
        
        self.metrics.avg_response_time = sum(self.metrics.response_times) / len(self.metrics.response_times)
    
    async def get_stats(self) -> Dict:
        """Retorna estatísticas"""
        uptime = time.time() - self.start_time
        
        return {
            "uptime_hours": round(uptime / 3600, 2),
            "total_messages": self.metrics.total_messages,
            "total_voice": self.metrics.total_voice,
            "unique_users_today": len(self.metrics.daily_users),
            "avg_response_time": round(self.metrics.avg_response_time, 2),
            "error_rate": round(self.metrics.total_errors / max(self.metrics.total_messages, 1) * 100, 2)
        }

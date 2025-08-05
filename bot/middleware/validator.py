import re
from typing import Optional

class InputValidator:
    def __init__(self):
        self.max_text_length = 1000
        self.max_audio_size = 20 * 1024 * 1024  # 20MB
        self.blocked_patterns = [
            r'<script',
            r'javascript:',
            r'data:text/html'
        ]
    
    def validate_text(self, text: str) -> Optional[str]:
        """Valida e sanitiza texto"""
        if not text or len(text) > self.max_text_length:
            return None
        
        # Verificar padrões bloqueados
        for pattern in self.blocked_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return None
        
        # Sanitizar
        text = text.strip()
        text = re.sub(r'<[^>]+>', '', text)  # Remove HTML
        
        return text
    
    def validate_audio(self, file_size: int) -> bool:
        """Valida tamanho do áudio"""
        return 0 < file_size <= self.max_audio_size

import aiohttp
import logging
import asyncio
import os
from typing import Optional
import whisper

logger = logging.getLogger(__name__)

class WhisperService:
    def __init__(self):
        self.base_url = "http://whisper-service:5001"
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.local_model = None
        self._load_local_model()
    
    def _load_local_model(self):
        """Carrega modelo Whisper local como fallback"""
        try:
            model_size = os.getenv("WHISPER_MODEL", "base")
            self.local_model = whisper.load_model(model_size)
            logger.info(f"Modelo Whisper local {model_size} carregado")
        except Exception as e:
            logger.warning(f"Erro ao carregar modelo local: {e}")
    
    async def transcribe(self, audio_path: str) -> Optional[str]:
        """Transcreve áudio usando Whisper"""
        try:
            # Tentar serviço remoto primeiro
            result = await self._transcribe_remote(audio_path)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Serviço remoto falhou: {e}")
        
        # Fallback para modelo local
        return await self._transcribe_local(audio_path)
    
    async def _transcribe_remote(self, audio_path: str) -> Optional[str]:
        """Transcreve usando serviço remoto"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                with open(audio_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('audio', f, 
                                 filename='audio.ogg',
                                 content_type='audio/ogg')
                    
                    async with session.post(
                        f"{self.base_url}/transcribe",
                        data=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result.get('text', '').strip()
                        else:
                            logger.error(f"Whisper error: {response.status}")
                            return None
                            
        except Exception as e:
            logger.error(f"Whisper remote error: {e}")
            return None
    
    async def _transcribe_local(self, audio_path: str) -> Optional[str]:
        """Transcreve usando modelo local"""
        if not self.local_model:
            logger.error("Modelo local não disponível")
            return None
            
        try:
            # Executar em thread separada para não bloquear
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.local_model.transcribe(audio_path, language='en')
            )
            return result.get('text', '').strip()
        except Exception as e:
            logger.error(f"Whisper local error: {e}")
            return None

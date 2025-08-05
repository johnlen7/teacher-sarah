import edge_tts
import asyncio
import uuid
import os
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        self.voice = os.getenv("TTS_VOICE", "en-US-JennyNeural")
        self.rate = os.getenv("TTS_RATE", "+0%")
        self.pitch = os.getenv("TTS_PITCH", "+0Hz")
        self.temp_dir = os.path.join(os.getcwd(), "temp")
        
        # Criar diretório temp se não existir
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def generate_speech(self, text: str) -> Optional[str]:
        """Gera áudio a partir do texto usando Edge-TTS"""
        try:
            # Limpar texto de markdown
            clean_text = self._clean_text(text)
            
            if not clean_text.strip():
                return None
            
            # Gerar nome único para o arquivo
            output_file = os.path.join(
                self.temp_dir,
                f"speech_{uuid.uuid4().hex}.mp3"
            )
            
            # Configurar voz
            communicate = edge_tts.Communicate(
                clean_text,
                self.voice,
                rate=self.rate,
                pitch=self.pitch
            )
            
            # Gerar e salvar áudio
            await communicate.save(output_file)
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                logger.info(f"Áudio gerado: {output_file}")
                return output_file
            else:
                logger.error("Falha ao gerar áudio")
                return None
                
        except Exception as e:
            logger.error(f"Erro TTS: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Remove markdown e formatação do texto"""
        import re
        
        # Remove bold markdown
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        
        # Remove italic markdown
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'_(.*?)_', r'\1', text)
        
        # Remove code blocks
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`(.*?)`', r'\1', text)
        
        # Remove headers
        text = re.sub(r'#+\s', '', text)
        
        # Remove links mas mantém o texto
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Remove emojis (opcional)
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        
        return text.strip()
    
    async def list_voices(self) -> List[str]:
        """Lista vozes disponíveis para o idioma"""
        voices = await edge_tts.list_voices()
        english_voices = [
            v["ShortName"] for v in voices 
            if v["Locale"].startswith("en-")
        ]
        return english_voices

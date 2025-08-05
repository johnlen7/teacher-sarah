import os
import asyncio
import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from services import (
    WhisperService,
    DeepSeekService,
    TTSService,
    GrammarChecker
)

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self):
        self.whisper = WhisperService()
        self.deepseek = DeepSeekService()
        self.tts = TTSService()
        self.grammar = GrammarChecker()
        
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagens de texto"""
        try:
            user_message = update.message.text
            user_id = update.effective_user.id
            user_level = context.user_data.get('level', 'B1')
            
            # Mostrar "typing..."
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )
            
            # Verificar gramática
            grammar_errors = self.grammar.check(user_message)
            
            # Gerar resposta com DeepSeek
            response = await self.deepseek.generate_response(
                user_message=user_message,
                user_level=user_level,
                grammar_errors=grammar_errors
            )
            
            # Enviar resposta em texto
            await update.message.reply_text(
                response['text'],
                parse_mode='Markdown'
            )
            
            # Se o modo incluir voz, gerar e enviar áudio
            if context.user_data.get('mode', 'both') in ['voice', 'both']:
                # Gerar áudio apenas da parte em inglês
                english_text = response.get('english_only', response['text'])
                audio_path = await self.tts.generate_speech(english_text)
                
                if audio_path and os.path.exists(audio_path):
                    with open(audio_path, 'rb') as audio_file:
                        await update.message.reply_voice(
                            voice=audio_file,
                            caption="🔊 Listen to the pronunciation"
                        )
                    # Limpar arquivo temporário
                    os.remove(audio_path)
                    
        except Exception as e:
            logger.error(f"Erro ao processar texto: {e}")
            await update.message.reply_text(
                "❌ Sorry, I encountered an error. Please try again."
            )
    
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagens de voz"""
        try:
            # Mostrar "recording..."
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="record_voice"
            )
            
            # Baixar arquivo de voz
            voice_file = await update.message.voice.get_file()
            temp_dir = os.path.join(os.getcwd(), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            voice_path = os.path.join(temp_dir, f"voice_{update.message.message_id}.ogg")
            await voice_file.download_to_drive(voice_path)
            
            # Transcrever com Whisper
            transcription = await self.whisper.transcribe(voice_path)
            
            if not transcription:
                await update.message.reply_text(
                    "❌ I couldn't understand the audio. Please try again with clearer speech."
                )
                return
            
            # Enviar transcrição
            await update.message.reply_text(
                f"📝 **I heard:** {transcription}",
                parse_mode='Markdown'
            )
            
            # Processar como texto
            user_level = context.user_data.get('level', 'B1')
            
            # Verificar gramática
            grammar_errors = self.grammar.check(transcription)
            
            # Gerar resposta
            response = await self.deepseek.generate_response(
                user_message=transcription,
                user_level=user_level,
                grammar_errors=grammar_errors,
                is_voice=True
            )
            
            # Enviar resposta em texto
            await update.message.reply_text(
                response['text'],
                parse_mode='Markdown'
            )
            
            # Gerar e enviar áudio da resposta
            english_text = response.get('english_only', response['text'])
            audio_path = await self.tts.generate_speech(english_text)
            
            if audio_path and os.path.exists(audio_path):
                with open(audio_path, 'rb') as audio_file:
                    await update.message.reply_voice(
                        voice=audio_file,
                        caption="🎯 Practice repeating this!"
                    )
                os.remove(audio_path)
            
            # Limpar arquivo de voz original
            if os.path.exists(voice_path):
                os.remove(voice_path)
                
        except Exception as e:
            logger.error(f"Erro ao processar voz: {e}")
            await update.message.reply_text(
                "❌ Sorry, I couldn't process your voice message. Please try again."
            )

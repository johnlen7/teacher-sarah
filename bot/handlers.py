import os
import asyncio
import logging
import re
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from bot.services import (
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
    
    def _sanitize_markdown(self, text: str) -> str:
        """Sanitiza markdown para evitar erros de parsing"""
        if not text:
            return ""
        
        # Remove caracteres problemáticos para markdown
        # Escape caracteres especiais
        text = text.replace('*', '\\*')
        text = text.replace('_', '\\_')
        text = text.replace('[', '\\[')
        text = text.replace(']', '\\]')
        text = text.replace('(', '\\(')
        text = text.replace(')', '\\)')
        text = text.replace('~', '\\~')
        text = text.replace('`', '\\`')
        text = text.replace('>', '\\>')
        text = text.replace('#', '\\#')
        text = text.replace('+', '\\+')
        text = text.replace('-', '\\-')
        text = text.replace('=', '\\=')
        text = text.replace('|', '\\|')
        text = text.replace('{', '\\{')
        text = text.replace('}', '\\}')
        text = text.replace('.', '\\.')
        text = text.replace('!', '\\!')
        
        return text
        
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagens de texto"""
        try:
            user_message = update.message.text
            chat_id = update.effective_chat.id
            user = update.effective_user
            user_level = context.user_data.get('level', 'B1')
            
            # Verificar se está no meio de um teste de nível
            if 'level_test' in context.user_data:
                await self._handle_level_test_response(update, context, user_message)
                return
            
            # Mostrar "typing..."
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action="typing"
            )
            
            # Verificar gramática
            grammar_errors = self.grammar.check(user_message)
            
            # Gerar resposta com DeepSeek incluindo contexto histórico
            response = await self.deepseek.generate_response(
                user_message=user_message,
                chat_id=chat_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                user_level=user_level,
                grammar_errors=grammar_errors,
                is_voice=False
            )
            
            # Enviar resposta em texto (sem markdown para evitar erros)
            await update.message.reply_text(
                response['text']
            )
            
            # Se o modo incluir voz, gerar e enviar áudio
            if context.user_data.get('mode', 'both') in ['voice', 'both']:
                # Mostrar que está gravando áudio
                await context.bot.send_chat_action(
                    chat_id=chat_id,
                    action="record_voice"
                )
                
                # Enviar mensagem indicando que está gerando áudio
                status_message = await update.message.reply_text("🎤 Recording audio response...")
                
                # Gerar áudio apenas da parte em inglês
                english_text = response.get('english_only', response['text'])
                audio_path = await self.tts.generate_speech(english_text)
                
                # Deletar mensagem de status
                await status_message.delete()
                
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
                f"📝 **I heard:** {transcription}"
            )
            
            # Processar como texto
            chat_id = update.effective_chat.id
            user = update.effective_user
            user_level = context.user_data.get('level', 'B1')
            
            # Verificar gramática
            grammar_errors = self.grammar.check(transcription)
            
            # Gerar resposta com contexto histórico
            response = await self.deepseek.generate_response(
                user_message=transcription,
                chat_id=chat_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                user_level=user_level,
                grammar_errors=grammar_errors,
                is_voice=True
            )
            
            # Enviar resposta em texto
            await update.message.reply_text(
                response['text']
            )
            
            # Gerar e enviar áudio da resposta
            # Mostrar que está gravando áudio
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="record_voice"
            )
            
            # Enviar mensagem indicando que está gerando áudio
            status_message = await update.message.reply_text("🎤 Recording audio response...")
            
            english_text = response.get('english_only', response['text'])
            audio_path = await self.tts.generate_speech(english_text)
            
            # Deletar mensagem de status
            await status_message.delete()
            
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
            await update.message.reply_text("❌ Sorry, I had trouble processing your voice message. Please try again!")
    
    async def _handle_level_test_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str):
        """Handle responses to level test questions"""
        test_data = context.user_data['level_test']
        current_q = test_data['current_question']
        questions = test_data['questions']
        
        # Validate answer format
        answer = user_message.strip().upper()
        if answer not in ['A', 'B', 'C', 'D']:
            await update.message.reply_text("Please reply with just the letter A, B, C, or D! 😊")
            return
        
        # Save answer
        test_data['answers'].append(answer)
        test_data['current_question'] += 1
        
        # Check if more questions
        if test_data['current_question'] < len(questions):
            # Send next question
            next_q = questions[test_data['current_question']]
            question_num = test_data['current_question'] + 1
            
            test_text = f"""📝 **English Level Test** - Question {question_num}/5

{next_q['question']}

{chr(10).join(next_q['options'])}

Reply with just the letter (A, B, C, or D)"""
            
            await update.message.reply_text(test_text)
        else:
            # Test completed - evaluate and save level
            answers = test_data['answers']
            suggested_level = self.deepseek.evaluate_level_test(answers)
            
            # Update user level in database
            chat_id = update.effective_chat.id
            username = update.effective_user.username
            first_name = update.effective_user.first_name
            last_name = update.effective_user.last_name
            
            # Update in context and database
            context.user_data['level'] = suggested_level
            
            # Generate results message
            correct_count = sum(1 for i, answer in enumerate(answers) 
                              if i < len(questions) and answer == questions[i]["correct"])
            
            results_text = f"""🎯 **Test Results!**

You got **{correct_count}/5** questions correct!

🎓 **Your suggested English level: {suggested_level}**

**What this means:**
• **A1**: Beginner - Basic words and phrases
• **A2**: Elementary - Simple conversations
• **B1**: Intermediate - Everyday situations
• **B2**: Upper-Intermediate - Complex topics
• **C1**: Advanced - Sophisticated discussions
• **C2**: Proficient - Near-native level

I'll adjust my teaching style to match your **{suggested_level}** level! Ready to start practicing? Send me any message! 🚀"""
            
            await update.message.reply_text(results_text)
            
            # Clear test data
            del context.user_data['level_test']

import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Import sem usar relative import
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.handlers import MessageHandler as CustomHandler
from bot.services.async_message_queue import message_queue

# Configurar logging para multitarefas
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - Chat:%(chat_id)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_multitask.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente do diretório pai
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

class AsyncCustomHandler:
    """Handler que usa sistema de filas assíncronas para multitarefas"""
    
    def __init__(self):
        self.message_handler = CustomHandler()
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler assíncrono para mensagens de texto"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Log da mensagem recebida
        logger.info(f"Mensagem recebida - Chat: {chat_id}, User: {user_id}, Text: {message_text[:50]}...")
        
        # Adicionar à fila assíncrona
        task_id = await message_queue.add_message(
            chat_id=chat_id,
            user_id=user_id,
            message_type='text',
            content=message_text,
            update=update,
            context=context,
            handler_func=self._process_text_message,
            priority=1  # Alta prioridade para mensagens de texto
        )
        
        logger.info(f"Task criada - Chat: {chat_id}, Task ID: {task_id}")
        # Enviar confirmação imediata (opcional - mostra que recebeu)
        # await update.message.reply_text("✨ Processing your message...")
    
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler assíncrono para mensagens de voz"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Log da mensagem de voz recebida
        logger.info(f"Mensagem de voz recebida - Chat: {chat_id}, User: {user_id}")
        
        # Adicionar à fila assíncrona
        task_id = await message_queue.add_message(
            chat_id=chat_id,
            user_id=user_id,
            message_type='voice',
            content='[voice_message]',
            update=update,
            context=context,
            handler_func=self._process_voice_message,
            priority=2  # Prioridade normal para voz (demora mais)
        )
        
        logger.info(f"Task de voz criada - Chat: {chat_id}, Task ID: {task_id}")
        
        # Mostrar que está processando
        await context.bot.send_chat_action(
            chat_id=chat_id,
            action="typing"
        )
    
    async def _process_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagem de texto usando o handler original"""
        try:
            # Verificar se é resposta de teste de nível
            if 'level_test' in context.user_data:
                await self.message_handler._handle_level_test_response(update, context, update.message.text)
            else:
                await self.message_handler.handle_text(update, context)
        except Exception as e:
            logger.error(f"Erro ao processar mensagem de texto: {e}")
            await update.message.reply_text("❌ Sorry, I encountered an error. Please try again.")
    
    async def _process_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagem de voz usando o handler original"""
        try:
            await self.message_handler.handle_voice(update, context)
        except Exception as e:
            logger.error(f"Erro ao processar mensagem de voz: {e}")
            await update.message.reply_text("❌ Sorry, I had trouble processing your voice message. Please try again!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    from bot.handlers import MessageHandler
    
    # Criar uma instância do handler para acessar o serviço
    handler = MessageHandler()
    
    # Gerar mensagem de boas-vindas personalizada
    welcome_response = await handler.deepseek.generate_welcome_message(
        chat_id=update.effective_chat.id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name
    )
    
    await update.message.reply_text(
        welcome_response['text']
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    help_text = """
🆘 **How to use Sarah English Teacher Bot:**

💬 **Chat Practice**: Send me any message in English and I'll respond naturally while helping you improve!

🎤 **Voice Practice**: Send voice messages to practice pronunciation - I'll give you tips!

📊 **Commands**:
• `/start` - Welcome message and introduction
• `/level` - Take a quick English level test
• `/help` - Show this help message

🎯 **Tips**:
• Just chat with me about anything you like
• Ask me questions about English grammar
• Practice describing your day, hobbies, or dreams
• Don't worry about mistakes - I'm here to help!

Ready to improve your English? Just send me a message! 🚀"""
    
    await update.message.reply_text(help_text)

async def level_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /level para teste de nível"""
    from bot.handlers import MessageHandler
    
    # Criar uma instância do handler para acessar o serviço
    handler = MessageHandler()
    
    # Obter perguntas do teste
    questions = handler.deepseek.get_level_test_questions()
    
    # Enviar primeira pergunta
    if questions:
        question = questions[0]
        test_text = f"""📝 **English Level Test** - Question 1/5

{question['question']}

{chr(10).join(question['options'])}

Reply with just the letter (A, B, C, or D)"""
        
        # Salvar estado do teste no contexto do usuário
        context.user_data['level_test'] = {
            'current_question': 0,
            'answers': [],
            'questions': questions
        }
        
        await update.message.reply_text(test_text)

async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Define o nível do aluno"""
    from bot.handlers import MessageHandler
    
    if context.args:
        level = context.args[0].upper()
        valid_levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        
        if level in valid_levels:
            # Atualizar no contexto local
            context.user_data['level'] = level
            
            # Atualizar no banco de dados
            handler = MessageHandler()
            handler.deepseek.update_user_level(update.effective_chat.id, level)
            
            await update.message.reply_text(
                f"Perfect! ✅ Your English level has been updated to **{level}**. "
                f"I'll adjust my teaching style accordingly! 😊"
            )
        else:
            await update.message.reply_text(
                "Invalid level. Please use one of: **A1, A2, B1, B2, C1, C2**.\n\n"
                "• A1/A2: Beginner\n• B1/B2: Intermediate\n• C1/C2: Advanced"
            )
    else:
        current_level = context.user_data.get('level', 'B1')
        await update.message.reply_text(
            f"Your current level is **{current_level}**.\n\n"
            f"Use `/level [A1-C2]` to change it.\n\n"
            f"**Levels:**\n"
            f"• A1: Beginner\n• A2: Elementary\n• B1: Intermediate\n"
            f"• B2: Upper-Intermediate\n• C1: Advanced\n• C2: Proficient"
        )

async def queue_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para verificar status da fila de processamento"""
    status = message_queue.get_queue_status()
    
    status_text = f"""🔄 **Queue Status**

🎯 **Active Processing:**
• Chats being processed: {status['active_chats']}
• Total queued messages: {status['total_queued_messages']}
• Max concurrent tasks: {status['max_concurrent_tasks']}

📊 **Chat Queues:**"""
    
    if status['chat_queues']:
        for chat_id, queue_size in status['chat_queues'].items():
            status_text += f"\n• Chat {chat_id}: {queue_size} messages"
    else:
        status_text += "\n• All queues empty ✅"
    
    if status['processing_chats']:
        status_text += f"\n\n🔄 **Currently Processing:** {', '.join(map(str, status['processing_chats']))}"
    
    await update.message.reply_text(status_text)

def main():
    """Função principal"""
    # Criar aplicação
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    
    # Instanciar handler assíncrono customizado
    async_handler = AsyncCustomHandler()
    
    # Adicionar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("level", level_test_command))
    application.add_handler(CommandHandler("setlevel", set_level))
    application.add_handler(CommandHandler("status", queue_status))
    
    # Handler para mensagens de texto (usando fila assíncrona)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, async_handler.handle_text)
    )
    
    # Handler para mensagens de voz (usando fila assíncrona)
    application.add_handler(
        MessageHandler(filters.VOICE, async_handler.handle_voice)
    )
    
    # Adicionar handler de shutdown gracioso
    async def shutdown_handler():
        """Encerra o sistema de filas graciosamente"""
        await message_queue.shutdown()
    
    # Registrar shutdown handler
    application.add_handler(CommandHandler("shutdown", shutdown_handler))
    
    # Iniciar bot
    print("🚀 Sarah English Teacher Bot iniciado com sistema multitarefa!")
    print("📊 Processamento assíncrono ativo - múltiplas conversas simultâneas")
    application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

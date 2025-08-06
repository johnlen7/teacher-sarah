import os
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Import sem usar relative import
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.handlers import MessageHandler as CustomHandler

# Carregar variáveis de ambiente do diretório pai
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

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

def main():
    """Função principal"""
    # Criar aplicação
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    
    # Instanciar handler customizado
    custom_handler = CustomHandler()
    
    # Adicionar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("level", level_test_command))
    application.add_handler(CommandHandler("setlevel", set_level))
    
    # Handler para mensagens de texto
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, custom_handler.handle_text)
    )
    
    # Handler para mensagens de voz
    application.add_handler(
        MessageHandler(filters.VOICE, custom_handler.handle_voice)
    )
    
    # Iniciar bot
    print("Bot iniciado! Aguardando mensagens...")
    application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

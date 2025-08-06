import os
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from handlers import MessageHandler as CustomHandler

# Carregar variáveis de ambiente do diretório pai
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    await update.message.reply_text(
        "🎓 Welcome! I'm your English teacher. Send me text or voice messages to practice!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    await update.message.reply_text(
        "Send me a message in English or a voice message. I'll reply in English and explain mistakes in Portuguese if needed. Use /level [A1-C2] to set your level."
    )

async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Define o nível do aluno"""
    from handlers import MessageHandler
    
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
                f"I'll adjust my teaching style accordingly! 😊",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "Invalid level. Please use one of: **A1, A2, B1, B2, C1, C2**.\n\n"
                "• A1/A2: Beginner\n• B1/B2: Intermediate\n• C1/C2: Advanced",
                parse_mode='Markdown'
            )
    else:
        current_level = context.user_data.get('level', 'B1')
        await update.message.reply_text(
            f"Your current level is **{current_level}**.\n\n"
            f"Use `/level [A1-C2]` to change it.\n\n"
            f"**Levels:**\n"
            f"• A1: Beginner\n• A2: Elementary\n• B1: Intermediate\n"
            f"• B2: Upper-Intermediate\n• C1: Advanced\n• C2: Proficient",
            parse_mode='Markdown'
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
    application.add_handler(CommandHandler("level", set_level))
    
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
    main()

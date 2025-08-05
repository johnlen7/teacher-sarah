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
    if context.args:
        level = context.args[0].upper()
        valid_levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        
        if level in valid_levels:
            context.user_data['level'] = level
            await update.message.reply_text(f"Level set to {level}.")
        else:
            await update.message.reply_text("Invalid level. Use one of: A1, A2, B1, B2, C1, C2.")
    else:
        await update.message.reply_text("Use /level [A1-C2] to set your English level.")

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

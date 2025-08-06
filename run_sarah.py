#!/usr/bin/env python3
"""
🚀 SARAH ENGLISH TEACHER BOT - LAUNCHER
Versão atualizada com todas as melhorias implementadas
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Verifica se todas as dependências estão configuradas"""
    
    print("🔍 VERIFICANDO CONFIGURAÇÃO...")
    print("=" * 50)
    
    # Verificar arquivo .env
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ Arquivo .env não encontrado!")
        print("💡 Copie .env.example para .env e configure suas chaves")
        return False
    
    # Carregar .env
    from dotenv import load_dotenv
    load_dotenv()
    
    # Verificar chaves essenciais
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    if not telegram_token:
        print("❌ TELEGRAM_BOT_TOKEN não configurado!")
        return False
    
    if not openrouter_key:
        print("⚠️ OPENROUTER_API_KEY não configurado - usando apenas GPT4All local")
    
    print(f"✅ Telegram Bot Token: {telegram_token[:20]}...")
    print(f"✅ OpenRouter API Key: {openrouter_key[:20] if openrouter_key else 'Não configurado'}...")
    print(f"✅ GPT4All Local: {'Habilitado' if os.getenv('USE_GPT4ALL', 'false').lower() == 'true' else 'Desabilitado'}")
    
    return True

def check_services():
    """Verifica se os serviços externos estão funcionando"""
    
    print(f"\n🔧 VERIFICANDO SERVIÇOS...")
    print("-" * 30)
    
    # Verificar Whisper
    try:
        import requests
        whisper_response = requests.get('http://localhost:5001/health', timeout=3)
        if whisper_response.status_code == 200:
            print("✅ Whisper API: Funcionando")
        else:
            print("⚠️ Whisper API: Não está rodando")
            print("💡 Execute: cd whisper && python app.py")
    except:
        print("⚠️ Whisper API: Não está rodando")
        print("💡 Execute: cd whisper && python app.py")
    
    # Verificar GPT4All (se habilitado)
    use_gpt4all = os.getenv('USE_GPT4ALL', 'false').lower() == 'true'
    if use_gpt4all:
        try:
            import requests
            gpt4all_response = requests.get('http://localhost:4891/v1/models', timeout=3)
            if gpt4all_response.status_code == 200:
                print("✅ GPT4All Local: Funcionando")
            else:
                print("⚠️ GPT4All Local: Não está rodando")
        except:
            print("⚠️ GPT4All Local: Não está rodando")
            print("💡 Inicie o GPT4All Server primeiro")

async def start_bot():
    """Inicia o bot Sarah"""
    
    print(f"\n🤖 INICIANDO SARAH ENGLISH TEACHER BOT...")
    print("=" * 50)
    
    try:
        # Importar e inicializar o bot
        from bot.main import main
        await main()
        
    except KeyboardInterrupt:
        print(f"\n👋 Bot encerrado pelo usuário")
    except Exception as e:
        print(f"❌ Erro ao iniciar o bot: {e}")
        logger.exception("Erro detalhado:")

def show_info():
    """Mostra informações sobre as melhorias"""
    
    print("🎉 SARAH 2.0 - MELHORIAS IMPLEMENTADAS")
    print("=" * 50)
    print("✅ Sarah mais jovem e divertida (28 anos)")
    print("✅ Referências a cultura jovem (Marvel, K-pop, Games)")
    print("✅ Sistema de memória individual por usuário")
    print("✅ Múltiplas APIs com fallback automático")
    print("✅ Indicadores visuais de gravação de áudio")
    print("✅ Modelo DeepSeek R1 atualizado via OpenRouter")
    print("✅ Headers corretos para melhor performance")
    print("✅ Correções mais didáticas e divertidas")
    print("")

if __name__ == "__main__":
    # Banner inicial
    print("🌟" * 20)
    print("  SARAH ENGLISH TEACHER BOT")
    print("     Versão 2.0 Atualizada")
    print("🌟" * 20)
    print("")
    
    # Mostrar melhorias
    show_info()
    
    # Verificar configuração
    if not check_environment():
        sys.exit(1)
    
    # Verificar serviços
    check_services()
    
    # Iniciar bot
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print(f"\n👋 Tchau! Sarah está sempre pronta para ensinar! 🎓✨")

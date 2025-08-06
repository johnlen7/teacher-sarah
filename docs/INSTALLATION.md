# 🚀 Guia de Instalação - Sarah English Teacher Bot

## 📋 Pré-requisitos

### 🐍 Python
- **Versão**: Python 3.11 ou superior
- **Sistema**: Windows, Linux ou macOS

### 🔑 Chaves de API Necessárias

#### 🌐 OpenRouter (Principal - OBRIGATÓRIO)
1. Criar conta em [OpenRouter.ai](https://openrouter.ai/)
2. Obter API Key gratuita
3. Modelo usado: `tngtech/deepseek-r1t2-chimera:free`

#### 🤖 Telegram Bot (OBRIGATÓRIO)
1. Conversar com [@BotFather](https://t.me/botfather) no Telegram
2. Criar novo bot com `/newbot`
3. Obter Bot Token

#### 🧠 GPT4All (Opcional - Fallback)
- Servidor local na porta 4891
- Instalar via [GPT4All Desktop](https://gpt4all.io/)

## 📥 Instalação

### 1. 📂 Clonar Repositório
```bash
git clone https://github.com/johnlen7/teacher-sarah.git
cd teacher-sarah
```

### 2. 🐍 Criar Ambiente Virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. 📦 Instalar Dependências
```bash
pip install -r requirements.txt
```

### 4. ⚙️ Configurar Variáveis de Ambiente
```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar .env com suas chaves
```

#### 📝 Configurar .env
```env
# OBRIGATÓRIO - Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# OBRIGATÓRIO - OpenRouter (Principal)
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=tngtech/deepseek-r1t2-chimera:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=https://github.com/johnlen7/teacher-sarah
OPENROUTER_SITE_NAME=Sarah English Teacher Bot

# OPCIONAL - GPT4All (Fallback local)
GPT4ALL_URL=http://localhost:4891

# OPCIONAL - Whisper (Transcrição de áudio)
WHISPER_MODEL=base
DEVICE=cpu

# CONFIGURAÇÕES DO SISTEMA
LOG_LEVEL=INFO
```

## 🏃‍♂️ Execução

### 🎯 Método 1: Execução Simples
```bash
cd bot
python main.py
```

### 🎯 Método 2: Script Principal
```bash
python run_sarah.py
```

### 🎤 Método 3: Com Whisper (Audio)
```bash
# Terminal 1 - Whisper Server
cd whisper
python app.py

# Terminal 2 - Bot
cd bot
python main.py
```

## ✅ Verificação da Instalação

### 1. 🔧 Testar Configuração
```bash
python tests/test_env.py
```

### 2. 🤖 Testar APIs
```bash
python tests/test_apis_direct.py
```

### 3. 🗄️ Testar Banco de Dados
```bash
python tests/test_optimized_database.py
```

### 4. 🎯 Teste Completo
```bash
python tests/test_final_complete.py
```

## 🔧 Configurações Opcionais

### 🎤 Whisper (Transcrição de Áudio)

#### Instalação
```bash
pip install openai-whisper
```

#### Execução
```bash
cd whisper
python app.py
```

#### Configuração
- **Porta**: 5001 (padrão)
- **Modelo**: base (mais rápido) ou large (mais preciso)
- **Device**: cpu ou cuda (se tiver GPU)

### 🧠 GPT4All (IA Local)

#### Instalação
1. Baixar [GPT4All Desktop](https://gpt4all.io/)
2. Instalar e configurar
3. Ativar API Server na porta 4891

#### Modelos Recomendados
- **Meta-Llama-3-8B-Instruct.Q4_0.gguf** (padrão)
- **Phi-3-mini-4k-instruct.Q4_0.gguf** (mais rápido)

## 📊 Estrutura de Dados

### 🗄️ Sistema de Banco Individual
- **Localização**: `data/chats/`
- **Estrutura**: Cada usuário tem seu diretório
- **Arquivos por usuário**:
  - `profile.db` - Dados pessoais
  - `conversations.db` - Histórico de mensagens
  - `metadata.json` - Estatísticas rápidas

### 🔄 Migração de Dados Antigos
```bash
# Se tinha sistema antigo
python tests/migrate_database.py

# Para começar limpo
python tests/migrate_database.py --clean
```

## 🚨 Troubleshooting

### ❌ Bot não inicia
```bash
# Verificar token
python tests/test_env.py

# Verificar dependências
pip install -r requirements.txt
```

### ❌ IA não responde
```bash
# Testar OpenRouter
python tests/test_openrouter_direct.py

# Verificar .env
echo $OPENROUTER_API_KEY
```

### ❌ Áudio não funciona
```bash
# Verificar Whisper
curl http://localhost:5001/health

# Iniciar Whisper
cd whisper && python app.py
```

### ❌ Dados perdidos
```bash
# Verificar estrutura
ls data/chats/

# Testar banco
python tests/test_optimized_database.py
```

## 🔍 Logs e Debug

### 📋 Localização dos Logs
- **Diretório**: `logs/`
- **Arquivo principal**: `bot.log`
- **Rotação**: Automática por tamanho

### 🐛 Modo Debug
```bash
# Ativar logs detalhados
export LOG_LEVEL=DEBUG

# Executar bot
python bot/main.py
```

## 🚀 Deploy em Produção

### 🌐 Servidor Linux
```bash
# Instalar dependências do sistema
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Seguir instalação normal
git clone <repo>
cd english-teacher-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 🐳 Docker (Opcional)
```bash
# Build da imagem
docker-compose build

# Executar
docker-compose up -d
```

### 🔄 Processo Contínuo (Systemd)
```bash
# Criar service
sudo nano /etc/systemd/system/sarah-bot.service

# Habilitar
sudo systemctl enable sarah-bot
sudo systemctl start sarah-bot
```

## 📈 Monitoramento

### 📊 Métricas Importantes
- **Usuários ativos**: Via logs e banco
- **Mensagens processadas**: Estatísticas por chat
- **Performance das APIs**: Tempo de resposta
- **Uso de espaço**: Tamanho dos bancos individuais

### 🔍 Comandos Úteis
```bash
# Ver usuários ativos
find data/chats/ -name "metadata.json" | wc -l

# Ver logs em tempo real
tail -f logs/bot.log

# Status das APIs
python tests/test_apis_direct.py
```

---

**Status**: ✅ **GUIA COMPLETO DE INSTALAÇÃO**

*Siga este guia passo a passo para ter o Sarah English Teacher Bot funcionando perfeitamente em qualquer ambiente!*

#!/usr/bin/env python3
"""
Script de migração para o novo sistema de banco de dados otimizado
Migra dados do banco único para bancos individuais por chat_id
"""

import os
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
import shutil

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_to_optimized_system():
    """Migra do sistema antigo para o novo sistema otimizado"""
    
    # Caminhos
    old_db_path = Path("bot/data/user_history.db")
    new_base_path = Path("data/chats")
    
    if not old_db_path.exists():
        logger.info("Banco antigo não encontrado. Iniciando sistema limpo.")
        return
    
    logger.info("Iniciando migração dos dados...")
    
    # Criar diretório base
    new_base_path.mkdir(parents=True, exist_ok=True)
    
    # Conectar ao banco antigo
    with sqlite3.connect(old_db_path) as old_conn:
        old_conn.row_factory = sqlite3.Row
        
        # Obter todos os usuários únicos
        users = old_conn.execute("SELECT DISTINCT chat_id FROM users").fetchall()
        
        for user_row in users:
            chat_id = user_row['chat_id']
            logger.info(f"Migrando dados para chat_id: {chat_id}")
            
            # Criar estrutura para este chat
            chat_path = new_base_path / f"chat_{chat_id}"
            chat_path.mkdir(exist_ok=True)
            
            # Migrar dados do usuário
            migrate_user_data(old_conn, chat_id, chat_path)
            
            # Migrar conversas
            migrate_conversations(old_conn, chat_id, chat_path)
            
            # Criar metadata
            create_metadata(old_conn, chat_id, chat_path)
    
    # Fazer backup do banco antigo
    backup_path = old_db_path.parent / f"user_history_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(old_db_path, backup_path)
    logger.info(f"Backup criado em: {backup_path}")
    
    # Remover banco antigo
    old_db_path.unlink()
    logger.info("Migração concluída!")

def migrate_user_data(old_conn, chat_id, chat_path):
    """Migra dados do usuário"""
    profile_db = chat_path / "profile.db"
    
    with sqlite3.connect(profile_db) as new_conn:
        # Criar tabelas
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY,
                chat_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                english_level TEXT DEFAULT 'B1',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_sessions INTEGER DEFAULT 1,
                total_messages INTEGER DEFAULT 0,
                voice_messages INTEGER DEFAULT 0,
                corrected_errors INTEGER DEFAULT 0
            )
        """)
        
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY,
                chat_id INTEGER UNIQUE,
                topics_of_interest TEXT,
                learning_goals TEXT,
                preferred_response_style TEXT DEFAULT 'friendly',
                practice_focus TEXT,
                difficulty_preference TEXT DEFAULT 'adaptive',
                lesson_reminders BOOLEAN DEFAULT TRUE,
                progress_tracking BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (chat_id) REFERENCES user_profile (chat_id)
            )
        """)
        
        # Migrar dados do usuário
        user_data = old_conn.execute(
            "SELECT * FROM users WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        
        if user_data:
            # Calcular estatísticas
            msg_stats = old_conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_voice = 1 THEN 1 ELSE 0 END) as voice,
                    SUM(CASE WHEN has_errors = 1 THEN 1 ELSE 0 END) as errors
                FROM conversations WHERE chat_id = ?
            """, (chat_id,)).fetchone()
            
            total_msgs = msg_stats['total'] if msg_stats else 0
            voice_msgs = msg_stats['voice'] if msg_stats else 0
            error_msgs = msg_stats['errors'] if msg_stats else 0
            
            new_conn.execute("""
                INSERT INTO user_profile 
                (chat_id, username, first_name, last_name, english_level, 
                 created_at, last_active, total_messages, voice_messages, corrected_errors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chat_id, user_data['username'], user_data['first_name'], 
                user_data['last_name'], user_data['english_level'],
                user_data['created_at'], user_data['last_active'],
                total_msgs, voice_msgs, error_msgs
            ))
        
        # Migrar preferências se existirem
        prefs = old_conn.execute(
            "SELECT * FROM user_preferences WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        
        if prefs:
            new_conn.execute("""
                INSERT INTO user_preferences 
                (chat_id, topics_of_interest, learning_goals, preferred_response_style)
                VALUES (?, ?, ?, ?)
            """, (
                chat_id, prefs['topics_of_interest'], 
                prefs['learning_goals'], prefs['preferred_response_style']
            ))
        else:
            new_conn.execute("""
                INSERT INTO user_preferences (chat_id, topics_of_interest)
                VALUES (?, ?)
            """, (chat_id, json.dumps([])))
        
        new_conn.commit()

def migrate_conversations(old_conn, chat_id, chat_path):
    """Migra conversas"""
    conversations_db = chat_path / "conversations.db"
    
    with sqlite3.connect(conversations_db) as new_conn:
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                session_id TEXT,
                message_type TEXT,
                content TEXT,
                original_content TEXT,
                is_voice BOOLEAN DEFAULT FALSE,
                voice_duration REAL,
                has_errors BOOLEAN DEFAULT FALSE,
                grammar_corrections TEXT,
                vocabulary_suggestions TEXT,
                confidence_score REAL DEFAULT 1.0,
                response_time REAL DEFAULT 0.0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_context TEXT
            )
        """)
        
        # Migrar mensagens
        conversations = old_conn.execute("""
            SELECT * FROM conversations 
            WHERE chat_id = ? 
            ORDER BY timestamp ASC
        """, (chat_id,)).fetchall()
        
        current_session = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        for conv in conversations:
            new_conn.execute("""
                INSERT INTO messages 
                (chat_id, session_id, message_type, content, original_content,
                 is_voice, has_errors, grammar_corrections, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chat_id, current_session, conv['message_type'], 
                conv['content'], conv['content'], conv['is_voice'],
                conv['has_errors'], conv['grammar_corrections'], conv['timestamp']
            ))
        
        new_conn.commit()

def create_metadata(old_conn, chat_id, chat_path):
    """Cria arquivo de metadata"""
    metadata_file = chat_path / "metadata.json"
    
    # Calcular estatísticas
    stats = old_conn.execute("""
        SELECT 
            COUNT(*) as total_messages,
            SUM(CASE WHEN is_voice = 1 THEN 1 ELSE 0 END) as voice_messages,
            SUM(CASE WHEN has_errors = 1 THEN 1 ELSE 0 END) as corrections_made
        FROM conversations WHERE chat_id = ?
    """, (chat_id,)).fetchone()
    
    user_data = old_conn.execute(
        "SELECT english_level, created_at FROM users WHERE chat_id = ?", (chat_id,)
    ).fetchone()
    
    metadata = {
        "chat_id": chat_id,
        "created_at": user_data['created_at'] if user_data else datetime.now().isoformat(),
        "last_access": datetime.now().isoformat(),
        "total_sessions": 1,
        "current_level": user_data['english_level'] if user_data else "B1",
        "quick_stats": {
            "total_messages": stats['total_messages'] if stats else 0,
            "voice_messages": stats['voice_messages'] if stats else 0,
            "corrections_made": stats['corrections_made'] if stats else 0,
            "topics_discussed": []
        }
    }
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

def clean_start():
    """Inicia sistema limpo removendo dados antigos"""
    logger.info("Iniciando sistema limpo...")
    
    # Remover banco antigo se existir
    old_paths = [
        Path("bot/data/user_history.db"),
        Path("data/user_history.db")
    ]
    
    for path in old_paths:
        if path.exists():
            backup_name = f"{path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{path.suffix}"
            backup_path = path.parent / backup_name
            shutil.move(path, backup_path)
            logger.info(f"Backup antigo criado: {backup_path}")
    
    # Criar estrutura nova
    new_base_path = Path("data/chats")
    new_base_path.mkdir(parents=True, exist_ok=True)
    
    logger.info("Sistema limpo configurado!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clean":
        clean_start()
    else:
        migrate_to_optimized_system()

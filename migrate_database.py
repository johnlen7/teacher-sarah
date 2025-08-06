#!/usr/bin/env python3
"""
Script de migração do banco de dados unificado para sistema individual por chat_id
Migra de: data/user_history.db (banco único)
Para: data/chats/chat_XXXXX/ (bancos individuais)

Uso: python migrate_database.py
"""

import os
import sqlite3
import json
import shutil
from datetime import datetime
from pathlib import Path

class DatabaseMigrator:
    """Migra dados do sistema antigo para o novo sistema otimizado"""
    
    def __init__(self):
        self.old_db_path = "data/user_history.db"
        self.new_base_path = "data/chats"
        self.backup_path = "data/backup_old_db"
        
    def migrate_all_data(self):
        """Executa migração completa"""
        print("🚀 Iniciando migração do banco de dados...")
        print(f"📄 Origem: {self.old_db_path}")
        print(f"📁 Destino: {self.new_base_path}")
        print("-" * 50)
        
        # Verificar se banco antigo existe
        if not os.path.exists(self.old_db_path):
            print("❌ Banco antigo não encontrado. Migração não necessária.")
            return
        
        # Criar backup do banco antigo
        self._backup_old_database()
        
        # Obter lista de chat_ids únicos
        chat_ids = self._get_unique_chat_ids()
        print(f"👥 Encontrados {len(chat_ids)} usuários únicos")
        
        # Migrar cada usuário
        for i, chat_id in enumerate(chat_ids, 1):
            print(f"📦 Migrando usuário {i}/{len(chat_ids)}: chat_{chat_id}")
            self._migrate_user_data(chat_id)
        
        # Verificar integridade
        self._verify_migration()
        
        print("✅ Migração concluída com sucesso!")
        
    def _backup_old_database(self):
        """Cria backup do banco antigo"""
        print("💾 Criando backup do banco antigo...")
        
        if os.path.exists(self.backup_path):
            # Backup já existe, criar com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.backup_path}_{timestamp}"
        else:
            backup_path = self.backup_path
            
        shutil.copy2(self.old_db_path, backup_path)
        print(f"✅ Backup criado: {backup_path}")
        
    def _get_unique_chat_ids(self):
        """Obtém lista de chat_ids únicos do banco antigo"""
        conn = sqlite3.connect(self.old_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT chat_id FROM messages WHERE chat_id IS NOT NULL")
        chat_ids = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return chat_ids
        
    def _migrate_user_data(self, chat_id):
        """Migra dados de um usuário específico"""
        user_dir = os.path.join(self.new_base_path, f"chat_{chat_id}")
        os.makedirs(user_dir, exist_ok=True)
        
        # Migrar mensagens e sessões
        self._migrate_conversations(chat_id, user_dir)
        
        # Criar perfil básico
        self._create_user_profile(chat_id, user_dir)
        
        # Criar metadata
        self._create_metadata(chat_id, user_dir)
        
    def _migrate_conversations(self, chat_id, user_dir):
        """Migra mensagens e sessões para conversations.db"""
        conversations_db = os.path.join(user_dir, "conversations.db")
        
        # Conectar aos bancos
        old_conn = sqlite3.connect(self.old_db_path)
        new_conn = sqlite3.connect(conversations_db)
        
        # Criar tabelas no novo banco
        self._create_conversations_tables(new_conn)
        
        # Migrar mensagens
        old_cursor = old_conn.cursor()
        new_cursor = new_conn.cursor()
        
        old_cursor.execute("""
            SELECT * FROM messages 
            WHERE chat_id = ? 
            ORDER BY timestamp
        """, (chat_id,))
        
        messages = old_cursor.fetchall()
        
        for message in messages:
            # Adaptar estrutura se necessário
            new_cursor.execute("""
                INSERT INTO messages (
                    chat_id, session_id, message_type, content, original_content,
                    is_voice, voice_duration, has_errors, grammar_corrections,
                    vocabulary_suggestions, confidence_score, response_time,
                    timestamp, message_context
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, message[1:])  # Pular o ID original
        
        new_conn.commit()
        old_conn.close()
        new_conn.close()
        
    def _create_conversations_tables(self, conn):
        """Cria tabelas no banco de conversas"""
        cursor = conn.cursor()
        
        cursor.execute("""
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
                confidence_score REAL,
                response_time REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_context TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                session_id TEXT UNIQUE,
                session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_end TIMESTAMP,
                session_duration REAL,
                messages_count INTEGER DEFAULT 0,
                session_topic TEXT,
                session_quality_score REAL,
                learning_objectives TEXT,
                session_summary TEXT
            )
        """)
        
        conn.commit()
        
    def _create_user_profile(self, chat_id, user_dir):
        """Cria banco de perfil do usuário"""
        profile_db = os.path.join(user_dir, "profile.db")
        conn = sqlite3.connect(profile_db)
        cursor = conn.cursor()
        
        # Criar tabelas de perfil
        cursor.execute("""
            CREATE TABLE user_profile (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                current_level TEXT DEFAULT 'B1',
                preferred_language TEXT DEFAULT 'PT',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP,
                total_messages INTEGER DEFAULT 0,
                study_streak INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE learning_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                skill_type TEXT,
                skill_name TEXT,
                level_before TEXT,
                level_after TEXT,
                practice_count INTEGER DEFAULT 0,
                success_rate REAL,
                last_practiced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                mastery_level REAL DEFAULT 0.0,
                FOREIGN KEY (chat_id) REFERENCES user_profile(chat_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE user_preferences (
                chat_id INTEGER PRIMARY KEY,
                voice_enabled BOOLEAN DEFAULT TRUE,
                explanation_language TEXT DEFAULT 'PT',
                difficulty_preference TEXT DEFAULT 'AUTO',
                feedback_style TEXT DEFAULT 'ENCOURAGING',
                study_reminders BOOLEAN DEFAULT FALSE,
                reminder_frequency INTEGER DEFAULT 24,
                FOREIGN KEY (chat_id) REFERENCES user_profile(chat_id)
            )
        """)
        
        # Inserir dados básicos do usuário
        cursor.execute("""
            INSERT INTO user_profile (chat_id, created_at, last_active)
            VALUES (?, ?, ?)
        """, (chat_id, datetime.now(), datetime.now()))
        
        conn.commit()
        conn.close()
        
    def _create_metadata(self, chat_id, user_dir):
        """Cria arquivo metadata.json"""
        metadata_file = os.path.join(user_dir, "metadata.json")
        
        # Calcular estatísticas básicas
        conversations_db = os.path.join(user_dir, "conversations.db")
        conn = sqlite3.connect(conversations_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM messages WHERE chat_id = ?", (chat_id,))
        total_messages = cursor.fetchone()[0]
        
        conn.close()
        
        metadata = {
            "chat_id": chat_id,
            "last_update": datetime.now().isoformat() + "Z",
            "quick_stats": {
                "total_messages": total_messages,
                "total_sessions": 0,  # Calcular depois
                "current_level": "B1",
                "study_streak": 0,
                "last_active": datetime.now().isoformat() + "Z",
                "favorite_topics": [],
                "improvement_areas": []
            },
            "cache": {
                "recent_corrections": [],
                "vocabulary_learned": [],
                "common_mistakes": []
            },
            "database_info": {
                "profile_db_size": "0KB",
                "conversations_db_size": "0KB", 
                "total_size": "0KB",
                "last_backup": datetime.now().isoformat() + "Z"
            }
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
    def _verify_migration(self):
        """Verifica integridade da migração"""
        print("🔍 Verificando integridade da migração...")
        
        # Contar mensagens no banco antigo
        old_conn = sqlite3.connect(self.old_db_path)
        old_cursor = old_conn.cursor()
        old_cursor.execute("SELECT COUNT(*) FROM messages")
        old_count = old_cursor.fetchone()[0]
        old_conn.close()
        
        # Contar mensagens nos bancos novos
        new_count = 0
        for chat_dir in os.listdir(self.new_base_path):
            if chat_dir.startswith("chat_"):
                conversations_db = os.path.join(self.new_base_path, chat_dir, "conversations.db")
                if os.path.exists(conversations_db):
                    conn = sqlite3.connect(conversations_db)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM messages")
                    new_count += cursor.fetchone()[0]
                    conn.close()
        
        print(f"📊 Mensagens no banco antigo: {old_count}")
        print(f"📊 Mensagens nos bancos novos: {new_count}")
        
        if old_count == new_count:
            print("✅ Integridade verificada: Todos os dados foram migrados")
        else:
            print("⚠️ Possível problema na migração: Contagens não conferem")
            
def main():
    """Função principal"""
    print("📊 Migrador de Banco de Dados - Sarah English Teacher Bot")
    print("=" * 60)
    
    migrator = DatabaseMigrator()
    
    try:
        migrator.migrate_all_data()
    except Exception as e:
        print(f"❌ Erro durante migração: {e}")
        print("💡 Verifique os logs e tente novamente")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
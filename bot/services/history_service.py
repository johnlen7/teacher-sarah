import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class HistoryService:
    def __init__(self, db_path: str = "data/user_history.db"):
        """Inicializa o serviço de histórico com banco SQLite"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Cria as tabelas necessárias no banco"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    english_level TEXT DEFAULT 'B1',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    message_type TEXT,  -- 'user' ou 'sarah'
                    content TEXT,
                    is_voice BOOLEAN DEFAULT FALSE,
                    has_errors BOOLEAN DEFAULT FALSE,
                    grammar_corrections TEXT,  -- JSON string
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES users (chat_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    chat_id INTEGER PRIMARY KEY,
                    topics_of_interest TEXT,  -- JSON array
                    learning_goals TEXT,
                    preferred_response_style TEXT,
                    session_count INTEGER DEFAULT 0,
                    FOREIGN KEY (chat_id) REFERENCES users (chat_id)
                )
            """)
            
            conn.commit()
    
    def get_or_create_user(self, chat_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> Dict:
        """Obtém ou cria um usuário no banco"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Tenta encontrar usuário existente
            user = conn.execute(
                "SELECT * FROM users WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            
            if user:
                # Atualiza último acesso
                conn.execute(
                    "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE chat_id = ?",
                    (chat_id,)
                )
                conn.commit()
                return dict(user)
            else:
                # Cria novo usuário
                conn.execute("""
                    INSERT INTO users (chat_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                """, (chat_id, username, first_name, last_name))
                
                # Cria preferências padrão
                conn.execute("""
                    INSERT INTO user_preferences (chat_id, topics_of_interest, session_count)
                    VALUES (?, ?, 1)
                """, (chat_id, json.dumps([])))
                
                conn.commit()
                
                return {
                    'chat_id': chat_id,
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'english_level': 'B1',
                    'created_at': datetime.now(),
                    'last_active': datetime.now()
                }
    
    def save_message(self, chat_id: int, message_type: str, content: str, 
                    is_voice: bool = False, has_errors: bool = False, 
                    grammar_corrections: List[Dict] = None):
        """Salva uma mensagem na conversa"""
        corrections_json = json.dumps(grammar_corrections) if grammar_corrections else None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO conversations 
                (chat_id, message_type, content, is_voice, has_errors, grammar_corrections)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (chat_id, message_type, content, is_voice, has_errors, corrections_json))
            conn.commit()
    
    def get_conversation_history(self, chat_id: int, limit: int = 10) -> List[Dict]:
        """Obtém o histórico recente de conversas"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            rows = conn.execute("""
                SELECT * FROM conversations 
                WHERE chat_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (chat_id, limit)).fetchall()
            
            history = []
            for row in rows:
                history.append({
                    'message_type': row['message_type'],
                    'content': row['content'],
                    'is_voice': bool(row['is_voice']),
                    'has_errors': bool(row['has_errors']),
                    'grammar_corrections': json.loads(row['grammar_corrections']) if row['grammar_corrections'] else None,
                    'timestamp': row['timestamp']
                })
            
            return list(reversed(history))  # Ordem cronológica
    
    def update_user_level(self, chat_id: int, level: str):
        """Atualiza o nível de inglês do usuário"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE users SET english_level = ? WHERE chat_id = ?",
                (level, chat_id)
            )
            conn.commit()
    
    def get_user_context(self, chat_id: int) -> Dict:
        """Obtém contexto completo do usuário para usar nas respostas"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Dados do usuário
            user = conn.execute(
                "SELECT * FROM users WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            
            if not user:
                return {}
            
            # Preferências
            prefs = conn.execute(
                "SELECT * FROM user_preferences WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            
            # Estatísticas da conversa
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_messages,
                    SUM(CASE WHEN message_type = 'user' THEN 1 ELSE 0 END) as user_messages,
                    SUM(CASE WHEN has_errors = 1 THEN 1 ELSE 0 END) as messages_with_errors,
                    SUM(CASE WHEN is_voice = 1 THEN 1 ELSE 0 END) as voice_messages
                FROM conversations WHERE chat_id = ?
            """, (chat_id,)).fetchone()
            
            # Histórico recente
            recent_history = self.get_conversation_history(chat_id, 6)
            
            return {
                'user': dict(user) if user else {},
                'preferences': dict(prefs) if prefs else {},
                'stats': dict(stats) if stats else {},
                'recent_history': recent_history,
                'user_name': user['first_name'] if user and user['first_name'] else 'there'
            }
    
    def increment_session_count(self, chat_id: int):
        """Incrementa contador de sessões do usuário"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE user_preferences 
                SET session_count = session_count + 1 
                WHERE chat_id = ?
            """, (chat_id,))
            conn.commit()
    
    def add_topic_interest(self, chat_id: int, topic: str):
        """Adiciona um tópico de interesse do usuário"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            prefs = conn.execute(
                "SELECT topics_of_interest FROM user_preferences WHERE chat_id = ?",
                (chat_id,)
            ).fetchone()
            
            if prefs:
                topics = json.loads(prefs['topics_of_interest'] or '[]')
                if topic not in topics:
                    topics.append(topic)
                    conn.execute("""
                        UPDATE user_preferences 
                        SET topics_of_interest = ? 
                        WHERE chat_id = ?
                    """, (json.dumps(topics), chat_id))
                    conn.commit()
    
    def get_conversation_summary(self, chat_id: int) -> str:
        """Gera um resumo da conversa para contexto"""
        context = self.get_user_context(chat_id)
        
        if not context.get('recent_history'):
            return "This is our first conversation!"
        
        user_name = context['user_name']
        level = context.get('user', {}).get('english_level', 'B1')
        total_messages = context.get('stats', {}).get('total_messages', 0)
        
        summary = f"Previous conversation context with {user_name} (Level: {level}):\n"
        
        for msg in context['recent_history'][-4:]:  # Últimas 4 mensagens
            role = "Student" if msg['message_type'] == 'user' else "Sarah"
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            summary += f"- {role}: {content}\n"
        
        if total_messages > 10:
            summary += f"\n(This student has been practicing with me for {total_messages} messages)"
        
        return summary

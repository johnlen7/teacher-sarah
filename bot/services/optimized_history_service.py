import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class OptimizedHistoryService:
    def __init__(self, base_data_path: str = "data/chats"):
        """
        Inicializa o serviço de histórico otimizado com bancos separados por chat_id
        
        Estrutura:
        data/chats/
        ├── chat_123456789/
        │   ├── profile.db      (dados do usuário e preferências)
        │   ├── conversations.db (histórico de conversas)
        │   └── metadata.json   (informações rápidas de acesso)
        """
        self.base_path = Path(base_data_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"OptimizedHistoryService inicializado em: {self.base_path}")
    
    def _get_chat_path(self, chat_id: int) -> Path:
        """Retorna o caminho do diretório específico do chat"""
        return self.base_path / f"chat_{chat_id}"
    
    def _init_chat_database(self, chat_id: int):
        """Inicializa os bancos de dados para um chat específico"""
        chat_path = self._get_chat_path(chat_id)
        chat_path.mkdir(exist_ok=True)
        
        # Banco de perfil do usuário
        profile_db = chat_path / "profile.db"
        with sqlite3.connect(profile_db) as conn:
            conn.execute("""
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
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY,
                    chat_id INTEGER UNIQUE,
                    topics_of_interest TEXT,  -- JSON array
                    learning_goals TEXT,
                    preferred_response_style TEXT DEFAULT 'friendly',
                    practice_focus TEXT,      -- grammar, vocabulary, conversation, etc.
                    difficulty_preference TEXT DEFAULT 'adaptive',
                    lesson_reminders BOOLEAN DEFAULT TRUE,
                    progress_tracking BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (chat_id) REFERENCES user_profile (chat_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    skill_area TEXT,      -- grammar, vocabulary, speaking, etc.
                    level_assessment TEXT, -- A1, A2, B1, B2, C1, C2
                    progress_score REAL DEFAULT 0.0,
                    last_practiced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    strengths TEXT,       -- JSON array
                    weaknesses TEXT,      -- JSON array
                    FOREIGN KEY (chat_id) REFERENCES user_profile (chat_id)
                )
            """)
        
        # Banco de conversas
        conversations_db = chat_path / "conversations.db"
        with sqlite3.connect(conversations_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    session_id TEXT,      -- UUID para agrupar mensagens da mesma sessão
                    message_type TEXT,    -- 'user', 'sarah', 'system'
                    content TEXT,
                    original_content TEXT, -- Para guardar texto original antes de correções
                    is_voice BOOLEAN DEFAULT FALSE,
                    voice_duration REAL,  -- duração em segundos
                    has_errors BOOLEAN DEFAULT FALSE,
                    grammar_corrections TEXT,  -- JSON detalhado
                    vocabulary_suggestions TEXT, -- JSON
                    confidence_score REAL, -- quão confiante a IA está na resposta
                    response_time REAL,   -- tempo que levou para responder
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_context TEXT  -- contexto adicional para a mensagem
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    session_id TEXT UNIQUE,
                    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_end TIMESTAMP,
                    session_duration REAL, -- em minutos
                    messages_count INTEGER DEFAULT 0,
                    session_topic TEXT,
                    session_quality_score REAL, -- avaliação da qualidade da sessão
                    learning_objectives TEXT, -- JSON dos objetivos alcançados
                    session_summary TEXT
                )
            """)
        
        # Arquivo de metadata para acesso rápido
        metadata_file = chat_path / "metadata.json"
        if not metadata_file.exists():
            initial_metadata = {
                "chat_id": chat_id,
                "created_at": datetime.now().isoformat(),
                "last_access": datetime.now().isoformat(),
                "total_sessions": 0,
                "current_level": "B1",
                "quick_stats": {
                    "total_messages": 0,
                    "voice_messages": 0,
                    "corrections_made": 0,
                    "topics_discussed": []
                }
            }
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(initial_metadata, f, indent=2, ensure_ascii=False)
    
    def get_or_create_user(self, chat_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> Dict:
        """Obtém ou cria um usuário com banco próprio"""
        chat_path = self._get_chat_path(chat_id)
        
        # Se não existe o diretório, cria tudo do zero
        if not chat_path.exists():
            logger.info(f"Criando novo banco para chat_id: {chat_id}")
            self._init_chat_database(chat_id)
            
            # Cria o perfil inicial
            profile_db = chat_path / "profile.db"
            with sqlite3.connect(profile_db) as conn:
                conn.execute("""
                    INSERT INTO user_profile (chat_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                """, (chat_id, username, first_name, last_name))
                
                conn.execute("""
                    INSERT INTO user_preferences (chat_id, topics_of_interest)
                    VALUES (?, ?)
                """, (chat_id, json.dumps([])))
                
                conn.commit()
        
        # Carrega o perfil existente
        profile_db = chat_path / "profile.db"
        with sqlite3.connect(profile_db) as conn:
            conn.row_factory = sqlite3.Row
            
            user = conn.execute(
                "SELECT * FROM user_profile WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            
            if user:
                # Atualiza último acesso
                conn.execute(
                    "UPDATE user_profile SET last_active = CURRENT_TIMESTAMP WHERE chat_id = ?",
                    (chat_id,)
                )
                conn.commit()
                
                # Atualiza metadata
                self._update_metadata(chat_id, "last_access", datetime.now().isoformat())
                
                return dict(user)
        
        return {}
    
    def save_message(self, chat_id: int, message_type: str, content: str, 
                    session_id: str = None, is_voice: bool = False, 
                    voice_duration: float = 0.0, has_errors: bool = False, 
                    grammar_corrections: List[Dict] = None,
                    vocabulary_suggestions: List[Dict] = None,
                    confidence_score: float = 1.0,
                    response_time: float = 0.0,
                    original_content: str = None,
                    message_context: str = None):
        """Salva uma mensagem no banco específico do chat"""
        
        # Gera session_id se não fornecido
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        chat_path = self._get_chat_path(chat_id)
        conversations_db = chat_path / "conversations.db"
        
        corrections_json = json.dumps(grammar_corrections, ensure_ascii=False) if grammar_corrections else None
        vocab_json = json.dumps(vocabulary_suggestions, ensure_ascii=False) if vocabulary_suggestions else None
        
        with sqlite3.connect(conversations_db) as conn:
            conn.execute("""
                INSERT INTO messages 
                (chat_id, session_id, message_type, content, original_content, is_voice, 
                 voice_duration, has_errors, grammar_corrections, vocabulary_suggestions,
                 confidence_score, response_time, message_context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (chat_id, session_id, message_type, content, original_content or content,
                  is_voice, voice_duration, has_errors, corrections_json, vocab_json,
                  confidence_score, response_time, message_context))
            conn.commit()
        
        # Atualiza estatísticas no perfil
        self._update_user_stats(chat_id, is_voice, has_errors)
        
        # Atualiza metadata rápida
        metadata = self._get_metadata(chat_id)
        if metadata:
            metadata["quick_stats"]["total_messages"] += 1
            if is_voice:
                metadata["quick_stats"]["voice_messages"] += 1
            if has_errors:
                metadata["quick_stats"]["corrections_made"] += 1
            self._save_metadata(chat_id, metadata)
    
    def get_conversation_history(self, chat_id: int, limit: int = 10, 
                               session_id: str = None) -> List[Dict]:
        """Obtém histórico de conversas do banco específico"""
        chat_path = self._get_chat_path(chat_id)
        conversations_db = chat_path / "conversations.db"
        
        if not conversations_db.exists():
            return []
        
        with sqlite3.connect(conversations_db) as conn:
            conn.row_factory = sqlite3.Row
            
            if session_id:
                query = """
                    SELECT * FROM messages 
                    WHERE chat_id = ? AND session_id = ?
                    ORDER BY timestamp ASC
                """
                params = (chat_id, session_id)
            else:
                query = """
                    SELECT * FROM messages 
                    WHERE chat_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """
                params = (chat_id, limit)
            
            rows = conn.execute(query, params).fetchall()
            
            history = []
            for row in rows:
                history.append({
                    'id': row['id'],
                    'session_id': row['session_id'],
                    'message_type': row['message_type'],
                    'content': row['content'],
                    'original_content': row['original_content'],
                    'is_voice': bool(row['is_voice']),
                    'voice_duration': row['voice_duration'],
                    'has_errors': bool(row['has_errors']),
                    'grammar_corrections': json.loads(row['grammar_corrections']) if row['grammar_corrections'] else None,
                    'vocabulary_suggestions': json.loads(row['vocabulary_suggestions']) if row['vocabulary_suggestions'] else None,
                    'confidence_score': row['confidence_score'],
                    'response_time': row['response_time'],
                    'timestamp': row['timestamp'],
                    'message_context': row['message_context']
                })
            
            if not session_id:
                history.reverse()  # Ordem cronológica para histórico geral
            
            return history
    
    def get_user_context(self, chat_id: int) -> Dict:
        """Obtém contexto completo otimizado do usuário"""
        chat_path = self._get_chat_path(chat_id)
        
        if not chat_path.exists():
            return {}
        
        # Carrega metadata rápida primeiro
        metadata = self._get_metadata(chat_id)
        
        # Carrega perfil completo
        profile_db = chat_path / "profile.db"
        with sqlite3.connect(profile_db) as conn:
            conn.row_factory = sqlite3.Row
            
            user = conn.execute(
                "SELECT * FROM user_profile WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            
            prefs = conn.execute(
                "SELECT * FROM user_preferences WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            
            progress = conn.execute(
                "SELECT * FROM learning_progress WHERE chat_id = ? ORDER BY last_practiced DESC",
                (chat_id,)
            ).fetchall()
        
        # Histórico recente
        recent_history = self.get_conversation_history(chat_id, 8)
        
        # Tópicos recentes da conversa
        recent_topics = self._extract_recent_topics(recent_history)
        
        return {
            'user': dict(user) if user else {},
            'preferences': dict(prefs) if prefs else {},
            'learning_progress': [dict(p) for p in progress] if progress else [],
            'metadata': metadata or {},
            'recent_history': recent_history,
            'recent_topics': recent_topics,
            'user_name': user['first_name'] if user and user['first_name'] else 'there',
            'conversation_summary': self._generate_smart_summary(chat_id, recent_history)
        }
    
    def update_user_level(self, chat_id: int, level: str):
        """Atualiza nível do usuário no banco específico"""
        chat_path = self._get_chat_path(chat_id)
        profile_db = chat_path / "profile.db"
        
        with sqlite3.connect(profile_db) as conn:
            conn.execute(
                "UPDATE user_profile SET english_level = ? WHERE chat_id = ?",
                (level, chat_id)
            )
            conn.commit()
        
        # Atualiza metadata
        self._update_metadata(chat_id, "current_level", level)
    
    def _update_user_stats(self, chat_id: int, is_voice: bool, has_errors: bool):
        """Atualiza estatísticas do usuário"""
        chat_path = self._get_chat_path(chat_id)
        profile_db = chat_path / "profile.db"
        
        with sqlite3.connect(profile_db) as conn:
            conn.execute("""
                UPDATE user_profile SET 
                    total_messages = total_messages + 1,
                    voice_messages = voice_messages + ?,
                    corrected_errors = corrected_errors + ?
                WHERE chat_id = ?
            """, (1 if is_voice else 0, 1 if has_errors else 0, chat_id))
            conn.commit()
    
    def _get_metadata(self, chat_id: int) -> Dict:
        """Carrega metadata rápida"""
        metadata_file = self._get_chat_path(chat_id) / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self, chat_id: int, metadata: Dict):
        """Salva metadata"""
        metadata_file = self._get_chat_path(chat_id) / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def _update_metadata(self, chat_id: int, key: str, value):
        """Atualiza um campo específico da metadata"""
        metadata = self._get_metadata(chat_id)
        metadata[key] = value
        self._save_metadata(chat_id, metadata)
    
    def _extract_recent_topics(self, history: List[Dict]) -> List[str]:
        """Extrai tópicos mencionados recentemente"""
        topics = []
        for msg in history[-5:]:  # Últimas 5 mensagens
            content = msg['content'].lower()
            # Lógica simples para identificar tópicos
            common_topics = ['work', 'family', 'travel', 'food', 'movies', 'music', 
                           'sports', 'books', 'weather', 'hobbies', 'school', 'friends']
            for topic in common_topics:
                if topic in content and topic not in topics:
                    topics.append(topic)
        return topics
    
    def _generate_smart_summary(self, chat_id: int, recent_history: List[Dict]) -> str:
        """Gera resumo inteligente da conversa"""
        if not recent_history:
            return "This is our first conversation!"
        
        metadata = self._get_metadata(chat_id)
        user_context = self.get_or_create_user(chat_id)
        
        user_name = user_context.get('first_name', 'Student')
        level = user_context.get('english_level', 'B1')
        total_messages = metadata.get('quick_stats', {}).get('total_messages', 0)
        
        # Últimas interações relevantes
        recent_user_msgs = [msg for msg in recent_history[-6:] if msg['message_type'] == 'user']
        
        if recent_user_msgs:
            last_topics = ', '.join(self._extract_recent_topics(recent_history))
            summary = f"Continuing conversation with {user_name} (Level: {level}). "
            
            if last_topics:
                summary += f"Recent topics: {last_topics}. "
            
            if total_messages > 20:
                summary += f"Regular student with {total_messages} total messages. "
            
            # Contexto da última mensagem do usuário
            if recent_user_msgs:
                last_msg = recent_user_msgs[-1]['content'][:80] + "..." if len(recent_user_msgs[-1]['content']) > 80 else recent_user_msgs[-1]['content']
                summary += f"Last message: '{last_msg}'"
        else:
            summary = f"Welcoming back {user_name} (Level: {level})"
        
        return summary
    
    def get_chat_statistics(self, chat_id: int) -> Dict:
        """Retorna estatísticas detalhadas do chat"""
        metadata = self._get_metadata(chat_id)
        
        chat_path = self._get_chat_path(chat_id)
        if not chat_path.exists():
            return {}
        
        conversations_db = chat_path / "conversations.db"
        profile_db = chat_path / "profile.db"
        
        stats = {}
        
        # Estatísticas de mensagens
        with sqlite3.connect(conversations_db) as conn:
            conn.row_factory = sqlite3.Row
            
            msg_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN message_type = 'user' THEN 1 ELSE 0 END) as user_messages,
                    SUM(CASE WHEN is_voice = 1 THEN 1 ELSE 0 END) as voice_messages,
                    SUM(CASE WHEN has_errors = 1 THEN 1 ELSE 0 END) as messages_with_errors,
                    AVG(confidence_score) as avg_confidence,
                    AVG(response_time) as avg_response_time
                FROM messages WHERE chat_id = ?
            """, (chat_id,)).fetchone()
            
            stats['messages'] = dict(msg_stats) if msg_stats else {}
        
        # Estatísticas do perfil
        with sqlite3.connect(profile_db) as conn:
            conn.row_factory = sqlite3.Row
            
            profile_stats = conn.execute(
                "SELECT * FROM user_profile WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            
            stats['profile'] = dict(profile_stats) if profile_stats else {}
        
        stats['metadata'] = metadata
        return stats
    
    def cleanup_old_data(self, chat_id: int, days_old: int = 30):
        """Remove dados antigos para otimizar espaço"""
        chat_path = self._get_chat_path(chat_id)
        conversations_db = chat_path / "conversations.db"
        
        if conversations_db.exists():
            with sqlite3.connect(conversations_db) as conn:
                # Remove mensagens antigas, mantendo pelo menos as últimas 100
                conn.execute("""
                    DELETE FROM messages 
                    WHERE chat_id = ? 
                    AND timestamp < datetime('now', '-{} days')
                    AND id NOT IN (
                        SELECT id FROM messages 
                        WHERE chat_id = ? 
                        ORDER BY timestamp DESC 
                        LIMIT 100
                    )
                """.format(days_old), (chat_id, chat_id))
                conn.commit()
    
    def export_user_data(self, chat_id: int) -> Dict:
        """Exporta todos os dados do usuário"""
        return {
            'user_context': self.get_user_context(chat_id),
            'full_history': self.get_conversation_history(chat_id, limit=1000),
            'statistics': self.get_chat_statistics(chat_id)
        }

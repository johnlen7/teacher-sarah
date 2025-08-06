import os
import aiohttp
import logging
from typing import Dict, List, Optional
from .optimized_history_service import OptimizedHistoryService

logger = logging.getLogger(__name__)

class DeepSeekService:
    def __init__(self, api_key: str = None, history_service: OptimizedHistoryService = None):
        """Initializes the DeepSeek service with optimized individual chat databases"""
        
        # API Configuration
        self.openrouter_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        self.use_direct_deepseek = os.getenv("USE_DIRECT_DEEPSEEK", "false").lower() == "true"
        self.use_local_gpt4all = os.getenv("USE_GPT4ALL", "false").lower() == "true"
        
        # URLs and configurations
        self.openrouter_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "tngtech/deepseek-r1t2-chimera:free")
        self.deepseek_url = "https://api.deepseek.com/v1"
        self.gpt4all_url = os.getenv("GPT4ALL_URL", "http://localhost:4891")
        
        # Headers for OpenRouter API
        self.openrouter_headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://github.com/johnlen7/teacher-sarah"),
            "X-Title": os.getenv("OPENROUTER_SITE_NAME", "Sarah English Teacher Bot")
        }
        
        # Headers for DeepSeek Direct API
        self.deepseek_headers = {
            "Authorization": f"Bearer {self.deepseek_key}",
            "Content-Type": "application/json"
        }
        
        # Optimized history service with individual chat databases
        self.history = history_service or OptimizedHistoryService()
        
        # Determine which API to use
        if self.openrouter_key:
            primary_api = "OpenRouter DeepSeek (working!)"
        elif self.use_local_gpt4all:
            primary_api = "GPT4All Local"
        elif self.use_direct_deepseek and self.deepseek_key:
            primary_api = "DeepSeek Direct"
        else:
            primary_api = "No API configured"
            
        logger.info(f"DeepSeek initialized. Primary API: {primary_api}")
        logger.info(f"Available APIs: OpenRouter: {bool(self.openrouter_key)}, GPT4All: {self.use_local_gpt4all}, DeepSeek Direct: {bool(self.deepseek_key)}")
    
    async def generate_response(
        self,
        user_message: str,
        chat_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
        user_level: str = "B1",
        grammar_errors: List[Dict] = None,
        is_voice: bool = False
    ) -> Dict[str, str]:
        """Generate response with user's historical context"""
        
        if not user_message or not user_message.strip():
            return {
                'text': "😊 Hi, I'm here to help you learn English! Please feel free to send a message or audio and we can start practicing. If you're unsure about your level, take the test with /start!",
                'english_only': "Hi, I'm here to help you learn English! Feel free to send a message or audio to start practicing. If you want to check your level, click /start!"
            }
        
        # Ensure user exists in the database
        self.history.get_or_create_user(chat_id, username, first_name, last_name)
        
        # Save user message with proper parameters
        self.history.save_message(
            chat_id=chat_id, 
            message_type='user', 
            content=user_message, 
            is_voice=is_voice, 
            has_errors=bool(grammar_errors),
            grammar_corrections=grammar_errors if grammar_errors else None
        )
        
        # Get user's context from the history
        user_context = self.history.get_user_context(chat_id)
        actual_level = user_context.get('user', {}).get('english_level', user_level)
        
        # Construct system prompt based on the user's context
        system_prompt = self._build_system_prompt(actual_level, is_voice, user_context)
        
        # Build user content message with grammar corrections if necessary
        user_content = self._build_user_content(user_message, grammar_errors)
        
        # Try generating a response using available services
        response_data = await self._generate_response_with_fallback(system_prompt, user_content)
        
        if response_data:
            # Save Sarah's response to history with proper parameters
            self.history.save_message(
                chat_id=chat_id, 
                message_type='sarah', 
                content=response_data['text']
            )
            return response_data
        else:
            # Fallback response in case of failure
            fallback = self._fallback_response(user_message, actual_level, user_context)
            self.history.save_message(
                chat_id=chat_id, 
                message_type='sarah', 
                content=fallback['text']
            )
            return fallback
    
    async def _generate_response_with_fallback(self, system_prompt: str, user_content: str) -> Dict[str, str]:
        """Generate response by trying APIs in order of priority"""
        
        # Try OpenRouter (DeepSeek) -> GPT4All -> DeepSeek Direct
        if self.openrouter_key:
            result = await self._generate_with_openrouter(system_prompt, user_content)
            if result:
                logger.info("Response generated with OpenRouter DeepSeek")
                return result
            logger.warning("OpenRouter failed, trying GPT4All...")
        
        if self.use_local_gpt4all:
            result = await self._generate_with_gpt4all(system_prompt, user_content)
            if result:
                logger.info("Response generated with GPT4All Local")
                return result
            logger.warning("GPT4All failed, trying DeepSeek Direct...")
        
        if self.use_direct_deepseek and self.deepseek_key:
            result = await self._generate_with_deepseek_direct(system_prompt, user_content)
            if result:
                logger.info("Response generated with DeepSeek Direct")
                return result
            logger.error("All APIs failed!")
        
        return None
    
    async def _generate_with_gpt4all(self, system_prompt: str, user_content: str) -> Dict[str, str]:
        """Generate response using GPT4All local"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "Llama-3-8B-Instruct",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 600
                }
                
                async with session.post(
                    f"{self.gpt4all_url}/v1/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_content = data['choices'][0]['message']['content']
                        return self._parse_response(response_content, None)
                    else:
                        logger.error(f"GPT4All error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"GPT4All exception: {e}")
            return None
    
    async def _generate_with_deepseek_direct(self, system_prompt: str, user_content: str) -> Dict[str, str]:
        """Generate response using DeepSeek API"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 600
                }
                
                async with session.post(
                    f"{self.deepseek_url}/chat/completions",
                    headers=self.deepseek_headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_content = data['choices'][0]['message']['content']
                        return self._parse_response(response_content, None)
                    else:
                        logger.error(f"DeepSeek Direct error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"DeepSeek Direct exception: {e}")
            return None
    
    async def _generate_with_openrouter(self, system_prompt: str, user_content: str) -> Dict[str, str]:
        """Generate response using OpenRouter/DeepSeek API"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.openrouter_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 600
                }
                
                async with session.post(
                    f"{self.openrouter_url}/chat/completions",
                    headers=self.openrouter_headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_content = data['choices'][0]['message']['content']
                        return self._parse_response(response_content, None)
                    else:
                        logger.error(f"OpenRouter error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"OpenRouter exception: {e}")
            return None
    
    def _build_system_prompt(self, level: str, is_voice: bool, user_context: Dict = None) -> str:
        """Build the system prompt based on user level and historical context"""
        
        # Levels and explanations
        level_descriptions = {
            "A1": "Use very simple words, short sentences, present tense mainly",
            "A2": "Use simple vocabulary, basic past and future tenses",
            "B1": "Use everyday vocabulary, various tenses, simple idioms",
            "B2": "Use varied vocabulary, complex sentences, common phrasal verbs",
            "C1": "Use sophisticated vocabulary, idioms, nuanced expressions",
            "C2": "Use native-level vocabulary, cultural references, subtle humor"
        }
        
        voice_extra = "The user sent a voice message, so include pronunciation tips if relevant." if is_voice else ""
        
        # User context
        user_name = user_context.get('user_name', 'there') if user_context else 'there'
        conversation_summary = ""
        stats_info = ""
        
        if user_context and user_context.get('recent_history'):
            # Use o resumo já gerado pelo OptimizedHistoryService
            summary = user_context.get('conversation_summary', 'This is our first conversation!')
            conversation_summary = f"\n## CONVERSATION CONTEXT:\n{summary}\n"
            
            # Estatísticas do OptimizedHistoryService
            metadata = user_context.get('metadata', {})
            quick_stats = metadata.get('quick_stats', {})
            total_messages = quick_stats.get('total_messages', 0)
            voice_messages = quick_stats.get('voice_messages', 0)
            corrections = quick_stats.get('corrections_made', 0)
            
            if total_messages > 5:
                stats_info = f"""
## STUDENT PROGRESS:
- Total interactions: {total_messages}
- Voice practice: {voice_messages} messages
- Grammar corrections given: {corrections}
- This student has been practicing with you regularly!
"""

        return f"""# Sarah Collins - Your Cool English Teacher 🌟

## Core Identity
You're **Sarah Collins**, a super fun and energetic English teacher who loves working with young people! You're 28 years old, a social media savvy millennial who knows how to connect with Gen Z. You're here to make English learning feel like chatting with an awesome older sister rather than a boring class.

## IMPORTANT: PERSONALIZATION
- Address the student as "{user_name}" when appropriate  
- Remember previous conversations and refer to them naturally
- Build on topics and corrections from past interactions
- Show genuine interest in their progress and learning journey
- Use their interests and references to make lessons more engaging

## Your Teaching Style:
- **Be friendly**: Engage with the student as a friend. Ask questions about their interests and keep the tone conversational.
- **Encourage and motivate**: Always praise their successes, even the small ones.
- **Correct gently**: Offer corrections in a constructive way to keep the conversation moving smoothly.
- **Make it fun**: Use pop culture references, emojis, and trendy expressions naturally
- **Stay positive**: Create a supportive environment where mistakes are learning opportunities

## Levels of English:
- **A1 (Beginner)**: Focus on basic vocabulary and present tense, with help in Portuguese if necessary.
- **A2 (Elementary)**: Introduce past and future tenses, using simple language.
- **B1 (Intermediate)**: Work on expressions and phrasal verbs, encourage the student to think in English.
- **B2 (Upper-Intermediate)**: Include complex sentences, idioms, and discussions of deeper topics.
- **C1 (Advanced)**: Use nuanced vocabulary and engage in cultural discussions.
- **C2 (Proficient)**: Engage in near-native-level conversations, using advanced vocabulary and humor.

## Welcome Message Guidelines:
When greeting new students or when they use /start, be warm and welcoming:
"Welcome to your English learning journey! 🚀 I'm Sarah, your friendly English teacher! You can send me text or voice messages anytime to practice. If you'd like to take a level test to help me understand your English level better, just let me know and I'll guide you through it!"

{conversation_summary}

{stats_info}

## RESPONSE FORMAT:
1. **Greeting/Reaction**: Start with energy and acknowledgment
2. **Address the content**: Respond to what they said with interest
3. **Teaching moment**: Explain or correct (if needed) in a fun way
4. **Practice/Challenge**: Give them something to try or think about
5. **Personal touch**: Ask a follow-up question about their interests

## Current Student Level: {level_descriptions.get(level, "intermediate")}
{voice_extra}

## CRITICAL RULES:
1. ALWAYS respond in English (except for grammar corrections in Portuguese when needed)
2. Adapt your language to the student's {level} level
3. If the student makes grammar mistakes, add a section in Portuguese explaining the errors
4. Be encouraging and friendly like Sarah Collins
5. Keep responses conversational but educational
6. **REMEMBER and reference previous conversations naturally**
7. Use the student's name ({user_name}) when it feels natural
8. Build on topics and progress from past interactions

Remember: You're not just teaching English - you're building confidence, creating connections, and making learning an adventure! Keep it real, keep it fun, and always celebrate their progress! 🚀✨"""
        
    def _build_user_content(self, message: str, errors: List[Dict]) -> str:
        """Add information about grammar errors if present"""
        if errors:
            error_summary = "\n[Grammar issues detected: " + ", ".join([e['rule'] for e in errors[:3]]) + "]"
            return f"{message}{error_summary}"
        return message
    
    def _parse_response(self, content: str, has_errors: bool) -> Dict[str, str]:
        """Parse response and extract English and Portuguese parts"""
        if "---" in content:
            parts = content.split("---", 1)
            english_part = parts[0].strip()
            portuguese_part = parts[1].strip() if len(parts) > 1 else ""
            
            return {
                'text': content,
                'english_only': english_part,
                'portuguese_corrections': portuguese_part
            }
        else:
            return {
                'text': content,
                'english_only': content
            }
    
    def _fallback_response(self, user_message: str, level: str, user_context: Dict = None) -> Dict[str, str]:
        """Fallback response when API fails"""
        user_name = user_context.get('user_name', 'there') if user_context else 'there'
        
        fallback_responses = {
            "A1": f"Hi {user_name}! 😊 That's interesting! Can you tell me more about that? I want to help you practice English!",
            "A2": f"Hey {user_name}! 🌟 Thanks for sharing that! Let's practice together. Can you describe what you did yesterday?",
            "B1": f"Hello {user_name}! 💫 That's a great topic! I'd love to help you improve your English. What's your favorite hobby?",
            "B2": f"Hi there {user_name}! ✨ I'm here to help you with English! What would you like to practice today?",
            "C1": f"Hello {user_name}! 🚀 I'm excited to continue our English journey together! What's on your mind?",
            "C2": f"Hey {user_name}! 🎯 Great to chat with you again! What fascinating topic shall we explore today?"
        }
        
        fallback = fallback_responses.get(level, fallback_responses["B1"])
        
        return {
            'text': fallback,
            'english_only': fallback
        }
    
    def get_level_test_questions(self) -> List[Dict]:
        """Return level test questions"""
        return [
            {
                "question": "How do you introduce yourself?",
                "options": ["A) I am Sarah", "B) My name is Sarah", "C) I call Sarah", "D) Sarah is me"],
                "correct": "B",
                "level": "A1"
            },
            {
                "question": "What did you do yesterday?",
                "options": ["A) I go to work", "B) I went to work", "C) I am going to work", "D) I will go to work"],
                "correct": "B",
                "level": "A2"
            },
            {
                "question": "Choose the correct sentence:",
                "options": ["A) I have been working here for 5 years", "B) I am working here for 5 years", "C) I work here for 5 years", "D) I was working here for 5 years"],
                "correct": "A",
                "level": "B1"
            },
            {
                "question": "If I _____ you, I would take that job.",
                "options": ["A) am", "B) was", "C) were", "D) will be"],
                "correct": "C",
                "level": "B2"
            },
            {
                "question": "The project was completed _____ schedule despite the challenges.",
                "options": ["A) ahead of", "B) behind", "C) on top of", "D) under"],
                "correct": "A",
                "level": "C1"
            }
        ]
    
    def evaluate_level_test(self, answers: List[str]) -> str:
        """Evaluate test answers and return suggested level"""
        questions = self.get_level_test_questions()
        correct_count = 0
        
        for i, answer in enumerate(answers):
            if i < len(questions) and answer == questions[i]["correct"]:
                correct_count += 1
        
        if correct_count <= 1:
            return "A1"
        elif correct_count == 2:
            return "A2"
        elif correct_count == 3:
            return "B1"
        elif correct_count == 4:
            return "B2"
        else:
            return "C1"
    
    async def generate_welcome_message(self, chat_id: int, username: str = None, first_name: str = None) -> Dict[str, str]:
        """Generate a personalized welcome message"""
        user_name = first_name or username or "there"
        
        welcome_text = f"""🌟 **Welcome to your English learning journey, {user_name}!** 🌟

I'm **Sarah Collins**, your friendly English teacher! I'm here to help you improve your English in a fun and engaging way! 

🚀 **How I can help you:**
• Practice conversations in English
• Correct your grammar gently
• Help with pronunciation (send voice messages!)
• Remember our previous conversations
• Adapt to your English level

📝 **Getting Started:**
• Send me any message in English to start practicing
• Use voice messages for pronunciation practice  
• Type /level to take a quick level test
• Just chat with me about anything you like!

Ready to start this amazing journey together? Send me a message and let's begin! 💫"""

        return {
            'text': welcome_text,
            'english_only': welcome_text
        }

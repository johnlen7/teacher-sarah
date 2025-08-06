"""
Sistema de fila assíncrona para processamento multitarefa de mensagens
Permite que o bot processe múltiplas conversas simultaneamente sem bloqueios
"""

import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

@dataclass
class MessageTask:
    """Representa uma tarefa de processamento de mensagem"""
    task_id: str
    chat_id: int
    user_id: int
    message_type: str  # 'text' ou 'voice'
    content: str
    update: Any  # Update object do Telegram
    context: Any  # Context object do Telegram
    created_at: datetime
    priority: int = 1  # 1 = alta, 2 = normal, 3 = baixa

class AsyncMessageQueue:
    """Sistema de fila assíncrona para processamento de mensagens"""
    
    def __init__(self, max_concurrent_tasks: int = 10):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.chat_queues: Dict[int, asyncio.Queue] = {}  # Uma fila por chat
        self.processing_chats: set = set()  # Chats sendo processados
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        
    async def add_message(self, 
                         chat_id: int, 
                         user_id: int, 
                         message_type: str, 
                         content: str, 
                         update: Any, 
                         context: Any,
                         handler_func: Callable,
                         priority: int = 1) -> str:
        """
        Adiciona uma mensagem à fila para processamento
        Retorna o ID da tarefa
        """
        task_id = str(uuid.uuid4())
        
        # Criar tarefa
        task = MessageTask(
            task_id=task_id,
            chat_id=chat_id,
            user_id=user_id,
            message_type=message_type,
            content=content,
            update=update,
            context=context,
            created_at=datetime.now(),
            priority=priority
        )
        
        # Garantir que existe uma fila para este chat
        if chat_id not in self.chat_queues:
            self.chat_queues[chat_id] = asyncio.Queue()
        
        # Adicionar à fila do chat
        await self.chat_queues[chat_id].put((task, handler_func))
        
        # Se o chat não está sendo processado, iniciar processamento
        if chat_id not in self.processing_chats:
            asyncio.create_task(self._process_chat_queue(chat_id))
        
        logger.info(f"Mensagem adicionada à fila - Chat: {chat_id}, Task: {task_id}")
        return task_id
    
    async def _process_chat_queue(self, chat_id: int):
        """Processa a fila de mensagens de um chat específico"""
        self.processing_chats.add(chat_id)
        
        try:
            queue = self.chat_queues[chat_id]
            
            while not queue.empty():
                # Usar semáforo para limitar tarefas concorrentes
                async with self._semaphore:
                    try:
                        # Pegar próxima tarefa (timeout para evitar bloqueio)
                        task, handler_func = await asyncio.wait_for(
                            queue.get(), timeout=0.1
                        )
                        
                        # Processar a mensagem
                        await self._execute_task(task, handler_func)
                        
                    except asyncio.TimeoutError:
                        # Fila vazia, pode sair
                        break
                    except Exception as e:
                        logger.error(f"Erro ao processar tarefa do chat {chat_id}: {e}")
                        
        finally:
            # Remover chat da lista de processamento
            self.processing_chats.discard(chat_id)
            
            # Se ainda há mensagens na fila, reprocessar
            if chat_id in self.chat_queues and not self.chat_queues[chat_id].empty():
                asyncio.create_task(self._process_chat_queue(chat_id))
    
    async def _execute_task(self, task: MessageTask, handler_func: Callable):
        """Executa uma tarefa de processamento de mensagem"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Iniciando processamento - Chat: {task.chat_id}, Task: {task.task_id}")
            
            # Executar a função de handler
            if task.message_type == 'text':
                await handler_func(task.update, task.context)
            elif task.message_type == 'voice':
                await handler_func(task.update, task.context)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Tarefa concluída - Chat: {task.chat_id}, Task: {task.task_id}, Tempo: {processing_time:.2f}s")
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Erro na tarefa - Chat: {task.chat_id}, Task: {task.task_id}, Tempo: {processing_time:.2f}s, Erro: {e}")
            
            # Tentar enviar mensagem de erro
            try:
                await task.update.message.reply_text(
                    "❌ Sorry, I encountered an error processing your message. Please try again."
                )
            except Exception as reply_error:
                logger.error(f"Erro ao enviar mensagem de erro: {reply_error}")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Retorna status das filas"""
        status = {
            'active_chats': len(self.processing_chats),
            'total_queued_messages': sum(q.qsize() for q in self.chat_queues.values()),
            'chat_queues': {
                chat_id: queue.qsize() 
                for chat_id, queue in self.chat_queues.items()
                if queue.qsize() > 0
            },
            'processing_chats': list(self.processing_chats),
            'max_concurrent_tasks': self.max_concurrent_tasks
        }
        return status
    
    async def clear_chat_queue(self, chat_id: int):
        """Limpa a fila de um chat específico"""
        if chat_id in self.chat_queues:
            queue = self.chat_queues[chat_id]
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            logger.info(f"Fila do chat {chat_id} limpa")
    
    async def shutdown(self):
        """Encerra o sistema de filas graciosamente"""
        logger.info("Encerrando sistema de filas...")
        
        # Aguardar conclusão de todas as tarefas ativas
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
        
        # Limpar todas as filas
        for chat_id in list(self.chat_queues.keys()):
            await self.clear_chat_queue(chat_id)
        
        logger.info("Sistema de filas encerrado")

# Instância global da fila
message_queue = AsyncMessageQueue(max_concurrent_tasks=15)

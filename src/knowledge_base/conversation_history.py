"""Conversation history storage."""
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConversationHistory:
    """In-memory conversation history storage."""
    
    def __init__(self, persist_directory: str = "./data/conversations"):
        """Initialize conversation history.
        
        Args:
            persist_directory: Directory to persist conversations
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a message to conversation history.
        
        Args:
            conversation_id: Unique conversation identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata
        """
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.conversations[conversation_id].append(message)
        logger.info(f"Added {role} message to conversation {conversation_id}")
    
    def get_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get conversation history.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            List of messages in the conversation
        """
        return self.conversations.get(conversation_id, [])
    
    def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent messages from conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            limit: Maximum number of messages to return
            
        Returns:
            List of recent messages
        """
        conversation = self.get_conversation(conversation_id)
        return conversation[-limit:] if conversation else []
    
    def save_conversation(self, conversation_id: str):
        """Save conversation to disk.
        
        Args:
            conversation_id: Unique conversation identifier
        """
        if conversation_id not in self.conversations:
            logger.warning(f"Conversation {conversation_id} not found")
            return
        
        file_path = self.persist_directory / f"{conversation_id}.json"
        
        try:
            with open(file_path, 'w') as f:
                json.dump(self.conversations[conversation_id], f, indent=2)
            logger.info(f"Saved conversation {conversation_id} to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save conversation {conversation_id}: {e}")
    
    def load_conversation(self, conversation_id: str):
        """Load conversation from disk.
        
        Args:
            conversation_id: Unique conversation identifier
        """
        file_path = self.persist_directory / f"{conversation_id}.json"
        
        if not file_path.exists():
            logger.info(f"No saved conversation found for {conversation_id}")
            return
        
        try:
            with open(file_path, 'r') as f:
                self.conversations[conversation_id] = json.load(f)
            logger.info(f"Loaded conversation {conversation_id} from {file_path}")
        except Exception as e:
            logger.error(f"Failed to load conversation {conversation_id}: {e}")
    
    def list_conversations(self) -> List[str]:
        """List all saved conversations.
        
        Returns:
            List of conversation IDs
        """
        return [
            f.stem for f in self.persist_directory.glob("*.json")
        ]
    
    def delete_conversation(self, conversation_id: str):
        """Delete a conversation.
        
        Args:
            conversation_id: Unique conversation identifier
        """
        # Remove from memory
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
        
        # Remove from disk
        file_path = self.persist_directory / f"{conversation_id}.json"
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted conversation {conversation_id}")
    
    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get summary of a conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            Dictionary with conversation summary
        """
        conversation = self.get_conversation(conversation_id)
        
        if not conversation:
            return {"error": "Conversation not found"}
        
        return {
            "conversation_id": conversation_id,
            "message_count": len(conversation),
            "first_message": conversation[0]["timestamp"] if conversation else None,
            "last_message": conversation[-1]["timestamp"] if conversation else None,
            "participants": list(set(msg["role"] for msg in conversation))
        }

"""Thread-safe, per-conversation token usage statistics."""

import threading
from datetime import datetime
from typing import Dict, Optional

from .local_context import LOCAL_USER_ID


class ConversationUsageContext:
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.user_id = LOCAL_USER_ID
        self.total_tokens = 0
        self.request_count = 0
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self._lock = threading.RLock()

    def update_token_usage(self, tokens: int, model: str = "unknown", metadata: Optional[Dict] = None):
        with self._lock:
            self.total_tokens += tokens
            self.request_count += 1
            self.updated_at = datetime.now().isoformat()

    def get_snapshot(self) -> Dict:
        with self._lock:
            return {
                "conversation_id": self.conversation_id,
                "user_id": self.user_id,
                "total_tokens": self.total_tokens,
                "request_count": self.request_count,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }


class ConversationUsageContextManager:
    def __init__(self):
        self._contexts: Dict[str, ConversationUsageContext] = {}
        self._lock = threading.RLock()

    def get_or_create_context(self, conversation_id: str, user_id: str = LOCAL_USER_ID):
        with self._lock:
            if conversation_id not in self._contexts:
                self._contexts[conversation_id] = ConversationUsageContext(conversation_id)
            return self._contexts[conversation_id]

    def get_context(self, conversation_id: str):
        with self._lock:
            return self._contexts.get(conversation_id)

    def list_contexts(self, user_id: Optional[str] = None):
        with self._lock:
            return list(self._contexts.values())

    def get_user_total_usage(self, user_id: str = LOCAL_USER_ID) -> Dict:
        snapshots = [context.get_snapshot() for context in self.list_contexts()]
        return {
            "user_id": LOCAL_USER_ID,
            "total_conversations": len(snapshots),
            "total_tokens": sum(item["total_tokens"] for item in snapshots),
            "total_requests": sum(item["request_count"] for item in snapshots),
            "conversations": snapshots,
        }

    def get_global_total_usage(self) -> Dict:
        stats = self.get_user_total_usage()
        stats.pop("conversations")
        stats.pop("user_id")
        stats["total_users"] = 1
        return stats


_usage_context_manager = ConversationUsageContextManager()


def get_usage_context_manager() -> ConversationUsageContextManager:
    return _usage_context_manager

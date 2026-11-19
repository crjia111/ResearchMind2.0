"""Local token statistics. This module never sends network requests."""

import os
from datetime import datetime

from .usage_context import get_usage_context_manager


class TokenUsageService:
    def __init__(self):
        self.enabled = os.getenv("TOKEN_STATS_ENABLED", "true").lower() == "true"
        self.start_time = datetime.now().isoformat()

    def record_token_usage(self, conversation_id, user_id, tokens, model="unknown", metadata=None,
                           fallback_user_id=None, client_id=None):
        if not self.enabled:
            return {"stats_enabled": False}
        context = get_usage_context_manager().get_or_create_context(conversation_id)
        context.update_token_usage(tokens, model, metadata)
        snapshot = context.get_snapshot()
        return {
            "stats_enabled": True,
            "current_request": {"tokens": tokens, "model": model},
            "conversation_total": {"tokens": snapshot["total_tokens"],
                                   "requests_count": snapshot["request_count"]},
        }

    def record_usage_isolated(self, *args, **kwargs):
        return self.record_token_usage(*args, **kwargs)

    def get_global_stats(self):
        stats = get_usage_context_manager().get_global_total_usage()
        stats.update(total_sessions=stats["total_conversations"], start_time=self.start_time,
                     current_time=datetime.now().isoformat())
        return stats


_usage_service = TokenUsageService()


def get_usage_service():
    return _usage_service

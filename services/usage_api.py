"""Unauthenticated, read-only statistics for the local application."""

from fastapi import APIRouter

from .usage_context import get_usage_context_manager
from .usage_stats import get_usage_service

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/conversation/{conversation_id}")
async def conversation_usage(conversation_id: str):
    context = get_usage_context_manager().get_context(conversation_id)
    return {"success": context is not None, "data": context.get_snapshot() if context else None}


@router.get("/local")
async def local_usage():
    return {"success": True, "data": get_usage_context_manager().get_user_total_usage()}


@router.get("/global")
async def global_usage():
    return {"success": True, "data": get_usage_service().get_global_stats()}

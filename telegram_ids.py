"""Отсечь не-Telegram user_id в БД (например синтетические id ≤ 0) при рассылке в ЛС."""

from __future__ import annotations

from typing import Any


def is_telegram_chat_id(user_id: Any) -> bool:
    """
    True, если user_id можно использовать как chat_id для личного сообщения в Telegram.
    """
    if isinstance(user_id, bool):
        return False
    if isinstance(user_id, int):
        return user_id > 0
    try:
        n = int(user_id)
    except (TypeError, ValueError):
        return False
    return n > 0

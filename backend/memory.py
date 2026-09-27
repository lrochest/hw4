"""Customer memory: logged-in shoppers' chat history in the chat_messages table.

One row per message:
    user_id        whose conversation (FK users.id)
    role           'user' or 'assistant'
    content        the text
    products_json  for assistant rows, the product cards shown (JSON list), else NULL
    created_at     set by SQLite

Guests are never stored.
"""

import json

from catalogue import get_products
from db import connect
from models import ChatMessageOut, ChatTurn, PastProduct, Product

MAX_RECENT_PRODUCTS = 10


def _ids(products_json: str | None) -> list[str]:
    """Product ids from a saved card snapshot (also reads the older seed-data snapshots)."""
    if not products_json:
        return []
    try:
        data = json.loads(products_json)
    except (json.JSONDecodeError, TypeError):
        return []
    return [p["product_id"] for p in data if isinstance(p, dict) and isinstance(p.get("product_id"), str)]


def _rows(user_id: int, limit: int | None) -> list:
    sql = "SELECT role, content, products_json, created_at FROM chat_messages WHERE user_id = ? ORDER BY id DESC"
    params: tuple = (user_id,)
    if limit:
        sql += " LIMIT ?"
        params = (user_id, limit)
    with connect(readonly=True) as conn:
        return list(reversed(conn.execute(sql, params).fetchall()))


def load_turns(user_id: int, limit: int) -> list[ChatTurn]:
    """The last `limit` messages, oldest first, for the agent's message history."""
    return [
        ChatTurn(role=r["role"], content=r["content"], product_ids=_ids(r["products_json"])[:6])
        for r in _rows(user_id, limit)
    ]


def load_for_display(user_id: int) -> list[ChatMessageOut]:
    """The whole conversation for the chat panel. Cards are re-read so prices and stock are current."""
    return [
        ChatMessageOut(role=r["role"], content=r["content"], products=get_products(_ids(r["products_json"])))
        for r in _rows(user_id, None)
    ]


def save_turn(user_id: int, question: str, reply: str, products: list[Product]) -> None:
    snapshot = json.dumps([p.model_dump() for p in products]) if products else None
    with connect() as conn:
        conn.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (user_id, question))
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply, snapshot),
        )


def clear(user_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))


def message_count(user_id: int) -> int:
    with connect(readonly=True) as conn:
        return conn.execute("SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (user_id,)).fetchone()[0]


def recent_products(user_id: int) -> list[PastProduct]:
    """Products shown to this shopper in earlier chats, most recent first, no repeats."""
    seen: dict[str, str] = {}
    with connect(readonly=True) as conn:
        rows = conn.execute(
            "SELECT products_json, created_at FROM chat_messages "
            "WHERE user_id = ? AND products_json IS NOT NULL ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    for r in rows:
        for pid in _ids(r["products_json"]):
            seen.setdefault(pid, r["created_at"])
        if len(seen) >= MAX_RECENT_PRODUCTS:
            break
    ids = list(seen)[:MAX_RECENT_PRODUCTS]
    return [PastProduct(product_id=p.product_id, name=p.name, last_shown=seen[p.product_id]) for p in get_products(ids)]

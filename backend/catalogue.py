"""Read-only catalogue queries, shared by the product routes and the agent's tools."""

import json
import sqlite3

from db import connect
from models import SIZES, Product, ProductDetail, SizeStock

# garment_type wording varies in the database ("hoodie", "pullover hoodie",
# "hooded sweatshirt"...), so group it into a few shopper-facing categories.
# Order matters: the first matching keyword wins.
CATEGORY_RULES = [
    ("quarter-zip", "Quarter-zips"),
    ("full-zip hooded", "Hoodies"),
    ("hood", "Hoodies"),
    ("jacket", "Jackets"),
    ("crewneck", "Crewnecks"),
    ("mockneck", "Crewnecks"),
    ("long-sleeve", "Long sleeves"),
    ("t-shirt", "T-shirts"),
]
CATEGORIES = ["T-shirts", "Long sleeves", "Crewnecks", "Hoodies", "Quarter-zips", "Jackets"]

PRODUCT_SQL = """
    SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock,
           GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS sizes_csv
    FROM catalogue c
    LEFT JOIN inventory i ON i.product_id = c.product_id
"""


def category_for(garment_type: str) -> str:
    lowered = garment_type.lower()
    for keyword, category in CATEGORY_RULES:
        if keyword in lowered:
            return category
    return "Other"


# Three seed rows have a placeholder instead of a description, left over from
# how the catalogue was generated. Never show that text to shoppers.
STUB_MARKER = "filename-based stub"
NO_DESCRIPTION = "No detailed description yet. Ask us in the chat, or email orderdept@campuscustoms.com."


def clean_description(text: str) -> str:
    return NO_DESCRIPTION if STUB_MARKER in text else text


def _to_product(row: sqlite3.Row) -> Product:
    return Product(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        category=category_for(row["garment_type"]),
        description=clean_description(row["description"]),
        colors=json.loads(row["colors"]),
        search_tags=json.loads(row["search_tags"]),
        image_url=f"/media/{row['image_file_path']}",
        price=row["price"],
        total_stock=row["total_stock"],
        sizes_in_stock=sorted((row["sizes_csv"] or "").split(",") if row["sizes_csv"] else [], key=_size_key),
    )


def _size_key(size: str) -> int:
    return SIZES.index(size) if size in SIZES else len(SIZES)


def list_products() -> list[Product]:
    with connect(readonly=True) as conn:
        rows = conn.execute(PRODUCT_SQL + " GROUP BY c.product_id ORDER BY c.name").fetchall()
    return [_to_product(r) for r in rows]


def get_products(product_ids: list[str]) -> list[Product]:
    """Products for these ids, in the same order; unknown ids are skipped."""
    if not product_ids:
        return []
    marks = ",".join("?" * len(product_ids))
    with connect(readonly=True) as conn:
        rows = conn.execute(
            PRODUCT_SQL + f" WHERE c.product_id IN ({marks}) GROUP BY c.product_id", product_ids
        ).fetchall()
    by_id = {r["product_id"]: _to_product(r) for r in rows}
    return [by_id[pid] for pid in product_ids if pid in by_id]


def get_product(product_id: str) -> ProductDetail | None:
    with connect(readonly=True) as conn:
        row = conn.execute(
            PRODUCT_SQL + " WHERE c.product_id = ? GROUP BY c.product_id", (product_id,)
        ).fetchone()
        if row is None:
            return None
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()
    inventory = sorted(
        (SizeStock(size=s["size"], quantity=s["quantity"]) for s in stock), key=lambda s: _size_key(s.size)
    )
    return ProductDetail(**_to_product(row).model_dump(), inventory=inventory)


def stock_by_product() -> dict[str, dict[str, int]]:
    """{product_id: {size: quantity}} for the whole catalogue (612 rows, cheap)."""
    result: dict[str, dict[str, int]] = {}
    with connect(readonly=True) as conn:
        for r in conn.execute("SELECT product_id, size, quantity FROM inventory"):
            result.setdefault(r["product_id"], {})[r["size"]] = r["quantity"]
    return {pid: dict(sorted(sizes.items(), key=lambda kv: _size_key(kv[0]))) for pid, sizes in result.items()}

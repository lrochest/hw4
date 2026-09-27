"""Builds the agent's per-request context (ShopDeps) from the session and the page.

Everything the browser sends is checked here before it reaches the agent:
product ids must exist in the catalogue, and free text is trimmed to one short
line, because it ends up in the agent's instructions.
"""

import re

from auth import User
from catalogue import get_product, get_products
from db import connect
from models import Customer, PageContext, PageInfo, ProductDescription

MAX_VISIBLE = 30  # product names listed in the agent's context for a list page


def customer_for(user: User | None) -> Customer | None:
    if user is None:
        return None
    with connect(readonly=True) as conn:
        row = conn.execute("SELECT created_at FROM users WHERE id = ?", (user.id,)).fetchone()
    return Customer(
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        member_since=row["created_at"] if row else "",
    )


def _one_line(text: str | None, limit: int = 80) -> str | None:
    if not text:
        return None
    text = re.sub(r"[\r\n`#]+", " ", text).strip()
    return text[:limit] or None


def _kind(path: str) -> str:
    if re.fullmatch(r"/products/[^/]+", path):
        return "product"
    if path.startswith("/products"):
        return "results" if "view=chat" in path else "catalogue"
    return {"/": "home", "/about": "about", "/account": "account"}.get(path.split("?")[0], "other")


def page_info_for(page: PageContext | None) -> PageInfo | None:
    if page is None:
        return None
    path = _one_line(page.path, 200) or "/"
    info = PageInfo(path=path, kind=_kind(path), label=_one_line(page.label))

    if page.product_id:
        product = get_product(page.product_id)
        if product:
            info.kind = "product"
            info.product = ProductDescription(
                product_id=product.product_id,
                name=product.name,
                garment_type=product.garment_type,
                category=product.category,
                description=product.description,
                colors=product.colors,
            )

    if page.visible_product_ids:
        # get_products drops unknown ids and keeps the on-screen order.
        shown = get_products(list(dict.fromkeys(page.visible_product_ids)))
        info.visible = [(p.product_id, p.name) for p in shown]
        info.visible_total = max(page.visible_total, len(shown))
    return info


def describe_customer(customer: Customer | None) -> list[str]:
    if customer is None:
        return [
            "- The shopper is a **guest** (not logged in). You don't know their name or email, and this chat "
            "isn't saved. If they want it saved, they can log in or create an account."
        ]
    return [
        f"- Logged in as **{customer.first_name} {customer.last_name}** ({customer.email}), "
        f"customer since {customer.member_since[:10]}.",
        "- Their earlier chats (if any) are loaded above as message history, and this chat is saved.",
        "- Use their first name now and then. Share their email or name only with them; never "
        "anyone else's (you have no one else's).",
    ]


def describe_page(page: PageInfo | None) -> list[str]:
    if page is None:
        return ["- Page: unknown."]
    lines = [f"- Page: `{page.path}` ({page.kind} page)" + (f", \"{page.label}\"" if page.label else "") + "."]
    p = page.product
    if p:
        fabric = p.colors[0] if p.colors else "not listed"
        lines += [
            f"- They are viewing **{p.name}** (product_id `{p.product_id}`), a {p.garment_type}. "
            f"Fabric color: {fabric}. All colors on it: {', '.join(p.colors) or 'not listed'}.",
            "- \"This\", \"it\", \"this one\" mean that product. It is one colorway: if they ask for another "
            "color, say what color it is and search for the color they want.",
            "- For its price or stock, still call get_price / check_stock with that id.",
        ]
    if page.visible:
        names = "; ".join(f"{name} (`{pid}`)" for pid, name in page.visible[:MAX_VISIBLE])
        more = len(page.visible) - MAX_VISIBLE
        lines += [
            f"- Product cards on screen ({page.visible_total}, in order): {names}"
            + (f"; and {more} more." if more > 0 else "."),
            "- \"These\", \"the first one\", \"any of these\" refer to those cards.",
        ]
    return lines

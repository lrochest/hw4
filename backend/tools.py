"""Tools the shop agent can call. Every price and stock number the agent quotes comes from here."""

import re
from typing import Literal

from pydantic_ai import ModelRetry, RunContext

import memory
from catalogue import get_product, list_products, stock_by_product
from models import (
    LOW_STOCK,
    SIZES,
    Alternative,
    AlternativesResult,
    CustomerProfile,
    ProductDescription,
    ProductDetail,
    ProductMatch,
    ProductPrice,
    SearchRecord,
    SearchResults,
    ShopDeps,
    Size,
    SizeAvailability,
    StockReport,
    StockStatus,
)

Category = Literal["T-shirts", "Long sleeves", "Crewnecks", "Hoodies", "Quarter-zips", "Jackets"]

MAX_RESULTS = 12
SNIPPET_CHARS = 140

# Words that appear in almost every question or product and so don't help rank.
STOPWORDS = {
    "a", "an", "and", "any", "are", "do", "for", "have", "i", "in", "is", "it", "me", "my", "of", "on",
    "or", "one", "please", "show", "some", "something", "the", "to", "want", "with", "you", "your",
    "yale", "merch", "shirt", "shirts",
}

# Shopper words -> the wording the catalogue uses.
SYNONYMS = {
    "tee": "t-shirt", "tees": "t-shirt", "tshirt": "t-shirt", "t-shirts": "t-shirt",
    "hoody": "hoodie", "hoodies": "hoodie", "hooded": "hoodie",
    "crew": "crewneck", "crewnecks": "crewneck", "sweatshirts": "sweatshirt",
    "quarterzip": "quarter-zip", "1/4": "quarter-zip",
    "grey": "gray", "mother": "mom", "father": "dad",
    "grandmother": "grandma", "grandfather": "grandpa",
}


def _terms(query: str) -> list[str]:
    words = re.findall(r"[a-z0-9/'-]+", query.lower())
    out = []
    for w in words:
        w = SYNONYMS.get(w, w)
        if w in STOPWORDS or len(w) < 2:
            continue
        # crude plural handling: "jackets" -> "jacket"
        if w.endswith("s") and len(w) > 3 and w not in {"dress", "class", "boss"}:
            w = w[:-1]
        out.append(w)
    return out


def _snippet(text: str) -> str:
    if len(text) <= SNIPPET_CHARS:
        return text
    return text[: text.rfind(" ", 0, SNIPPET_CHARS)].rstrip(",;:") + "…"


def search_products(
    ctx: RunContext[ShopDeps],
    query: str = "",
    category: Category | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size_in_stock: Size | None = None,
    limit: int = 8,
) -> SearchResults:
    """Search the Campus Customs catalogue.

    Use this for any request to find, list or recommend products.

    Args:
        query: Keywords, e.g. "bulldog", "Saybrook", "hockey", "mom", "Harvard game". Leave empty to
            browse with filters only.
        category: Limit to one garment category.
        color: Only products whose fabric is this color, e.g. "gray", "navy", "white". (Matches the
            garment itself, not the print, so "gray" won't return a navy tee with gray letters.)
        max_price: Only products at or under this price in US dollars.
        size_in_stock: Only products with at least one unit in this size.
        limit: How many results to return (1-12).

    Returns a search_id, the total number of matches, and the best `limit` matches with price and
    sizes in stock. total_matches == 0 means nothing in the catalogue matches. To show ALL matches
    on the website as product cards, put search_id in your page_results.
    """
    terms = _terms(query)
    stock = stock_by_product()
    scored: list[tuple[int, ProductMatch]] = []

    for p in list_products():
        if category and p.category != category:
            continue
        # colors[0] is the fabric (true for every product that lists colors); the
        # rest are print colors. Filter on the fabric only.
        if color and not (p.colors and color.lower() in p.colors[0].lower()):
            continue
        if max_price is not None and p.price > max_price:
            continue
        sizes = stock.get(p.product_id, {})
        in_stock = [s for s, q in sizes.items() if q > 0]
        if size_in_stock and size_in_stock not in in_stock:
            continue

        name = p.name.lower()
        tags = " ".join(p.search_tags).lower()
        body = f"{p.garment_type} {p.description} {' '.join(p.colors)}".lower()
        score = 0
        for t in terms:
            # Match at the start of a word, so "hat" finds "hat" and "hats" but not "that".
            word = re.compile(rf"\b{re.escape(t)}")
            if word.search(name):
                score += 3
            elif word.search(tags):
                score += 2
            elif word.search(body):
                score += 1
        if terms and score == 0:
            continue

        scored.append(
            (
                score,
                ProductMatch(
                    product_id=p.product_id,
                    name=p.name,
                    category=p.category,
                    colors=p.colors,
                    price=p.price,
                    sizes_in_stock=in_stock,
                    snippet=_snippet(p.description),
                ),
            )
        )

    scored.sort(key=lambda sp: (-sp[0], sp[1].name))
    everything = [m for _, m in scored]
    top = everything[: max(1, min(limit, MAX_RESULTS))]

    # Remember the full list so the website can show every match, not only the
    # few the model was sent. The index in deps.searches is the search_id.
    filters = {
        k: v
        for k, v in {"query": query, "category": category, "color": color,
                     "max_price": max_price, "size_in_stock": size_in_stock}.items()
        if v not in (None, "")
    }
    ctx.deps.searches.append(SearchRecord(filters=filters, product_ids=[m.product_id for m in everything]))
    ctx.deps.seen_product_ids.update(m.product_id for m in top)
    ctx.deps.quoted_prices.update(m.price for m in top)
    return SearchResults(search_id=len(ctx.deps.searches) - 1, total_matches=len(everything), matches=top)


# --- Lookups for one product ------------------------------------------------

def _lookup(ctx: RunContext[ShopDeps], product_id: str) -> ProductDetail:
    """Load a product or make the model retry with a real id."""
    product = get_product(product_id.strip())
    if product is None:
        raise ModelRetry(f"No product has product_id '{product_id}'. Use search_products to find the right id.")
    ctx.deps.seen_product_ids.add(product.product_id)
    return product


def get_product_description(ctx: RunContext[ShopDeps], product_id: str) -> ProductDescription:
    """What a product is and looks like: garment type, full description and colors.

    Call this when the shopper asks what an item looks like, what it's made of, what's printed on
    it, or which colors it comes in.

    Args:
        product_id: From search_products, or the product page the shopper is viewing.
    """
    p = _lookup(ctx, product_id)
    return ProductDescription(
        product_id=p.product_id,
        name=p.name,
        garment_type=p.garment_type,
        category=p.category,
        description=p.description,
        colors=p.colors,
    )


def get_price(ctx: RunContext[ShopDeps], product_id: str) -> ProductPrice:
    """The catalogue price of one product, in US dollars.

    Call this whenever the shopper asks what a specific item costs. Call it once per product when
    comparing or adding up several items.

    Args:
        product_id: From search_products, or the product page the shopper is viewing.
    """
    p = _lookup(ctx, product_id)
    ctx.deps.quoted_prices.add(p.price)
    return ProductPrice(product_id=p.product_id, name=p.name, price=p.price)


# Shopper wording -> catalogue sizes.
SIZE_WORDS = {
    "xs": "XS", "x-small": "XS", "extra small": "XS", "extra-small": "XS", "xsmall": "XS",
    "s": "S", "sm": "S", "small": "S",
    "m": "M", "med": "M", "medium": "M",
    "l": "L", "lg": "L", "large": "L",
    "xl": "XL", "x-large": "XL", "extra large": "XL", "extra-large": "XL", "xlarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "2x": "XXL", "xx-large": "XXL", "xxlarge": "XXL",
    "double xl": "XXL", "2x-large": "XXL",
}


def normalize_size(size: str) -> str | None:
    """'medium' -> 'M', '2XL' -> 'XXL'. None when it isn't a size we make."""
    return SIZE_WORDS.get(" ".join(size.lower().replace(".", "").split()))


def _status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "sold_out"
    return "low_stock" if quantity <= LOW_STOCK else "in_stock"


def check_stock(ctx: RunContext[ShopDeps], product_id: str, size: str | None = None) -> StockReport:
    """How many units of a product are in stock, size by size.

    Call this for any question about availability: "is it in stock?", "do you have a medium?",
    "what sizes are left?", "how many XLs?". Pass `size` when the shopper names one.

    Args:
        product_id: From search_products, or the product page the shopper is viewing.
        size: Optional size the shopper asked about, in their words ("M", "medium", "2XL" all work).
    """
    p = _lookup(ctx, product_id)
    by_size = {s.size: s.quantity for s in p.inventory}
    sizes = [SizeAvailability(size=sz, quantity=by_size.get(sz, 0), status=_status(by_size.get(sz, 0))) for sz in SIZES]
    in_stock = [s.size for s in sizes if s.status != "sold_out"]
    sold_out = [s.size for s in sizes if s.status == "sold_out"]

    requested: str | None = None
    requested_status = None
    if size:
        requested = normalize_size(size)
        if requested is None:
            requested, requested_status = size.strip(), "not_offered"
        else:
            requested_status = _status(by_size.get(requested, 0))

    # One sentence the model can repeat as-is, so "sold out" is never softened.
    if requested_status == "not_offered":
        summary = f"We don't make the {p.name} in {requested}; sizes are XS to XXL."
    elif requested_status == "sold_out":
        others = ", ".join(in_stock) if in_stock else "no other sizes"
        summary = f"The {p.name} is sold out in {requested}. In stock: {others}."
    elif requested_status is not None:
        n = by_size[requested]
        summary = f"The {p.name} is in stock in {requested}: {n} left."
    elif not in_stock:
        summary = f"The {p.name} is sold out in every size."
    else:
        summary = f"The {p.name} is in stock in {', '.join(in_stock)}" + (
            f"; sold out in {', '.join(sold_out)}." if sold_out else "."
        )

    ctx.deps.stock_counts.update(s.quantity for s in sizes)
    ctx.deps.stock_counts.add(sum(s.quantity for s in sizes))
    return StockReport(
        product_id=p.product_id,
        name=p.name,
        sizes=sizes,
        sizes_in_stock=in_stock,
        sold_out_sizes=sold_out,
        total_in_stock=sum(s.quantity for s in sizes),
        requested_size=requested,
        requested_size_status=requested_status,
        summary=summary,
    )


# --- Alternatives -----------------------------------------------------------

# Themes shoppers care about when they want "something like this". Each maps a
# word in a product's name or tags to (group, specific), e.g. "dad" ->
# ("family", "dad"): a Mom crewneck is a good stand-in for a sold-out Dad one.
THEME_WORDS = {
    **{w: ("family", w) for w in ["mom", "dad", "grandma", "grandpa", "aunt", "uncle", "brother", "sister", "cousin"]},
    **{w: ("sports", w) for w in ["baseball", "basketball", "diving", "fencing", "field hockey", "football", "golf",
                                  "hockey", "lacrosse", "sailing", "soccer", "squash", "swimming", "tennis", "track",
                                  "volleyball"]},
    **{w: ("residential college", w) for w in ["benjamin franklin", "berkeley", "branford", "davenport", "ezra stiles",
                                               "grace hopper", "jonathan edwards", "morse", "pauli murray", "pierson",
                                               "saybrook", "silliman", "timothy dwight", "trumbull"]},
    **{w: ("graduate school", "graduate school") for w in ["school of", "law school", "divinity", "forest school"]},
    "harvard": ("the game", "harvard"), "the game": ("the game", "the game"),
    "bulldog": ("bulldog", "bulldog"), "vintage": ("vintage", "vintage"),
    "left chest": ("left chest logo", "left chest logo"), "crest": ("crest", "crest"),
}


def _label(theme: str) -> str:
    return {"left chest logo": "a left-chest logo", "crest": "a crest", "graduate school": "a graduate school piece",
            "the game": "The Game", "bulldog": "a bulldog", "vintage": "vintage"}.get(theme, theme.title())


def _themes(name: str, tags: list[str]) -> set[tuple[str, str]]:
    text = " ".join([name, *tags]).lower()
    return {theme for word, theme in THEME_WORDS.items() if re.search(rf"\b{re.escape(word)}\b", text)}


def find_alternatives(
    ctx: RunContext[ShopDeps],
    product_id: str,
    size: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    limit: int = 4,
) -> AlternativesResult:
    """Similar products that ARE in stock: the answer to "sold out in my size" or "not in my color".

    Call this when check_stock says the shopper's size is sold out, when they want this item in a
    color it isn't made in, or when they ask for "something similar". Every result is in stock in
    `size` (if given) and has `color` as its fabric (if given).

    Args:
        product_id: The product they wanted.
        size: Their size, in their words ("L", "large", "2XL").
        color: A fabric color they want instead, e.g. "gray".
        max_price: Only alternatives at or under this price.
        limit: How many to return (1-8).
    """
    original = _lookup(ctx, product_id)
    wanted_size = normalize_size(size) if size else None
    if size and wanted_size is None:
        raise ModelRetry(f"'{size}' isn't a size we make (XS to XXL). Ask the shopper or leave size out.")
    base_themes = _themes(original.name, original.search_tags)
    base_fabric = original.colors[0].lower() if original.colors else ""
    stock = stock_by_product()

    scored: list[tuple[float, Alternative]] = []
    for p in list_products():
        if p.product_id == original.product_id:
            continue
        in_stock = [s for s, q in stock.get(p.product_id, {}).items() if q > 0]
        if not in_stock or (wanted_size and wanted_size not in in_stock):
            continue
        fabric = p.colors[0].lower() if p.colors else ""
        if color and color.lower() not in fabric:
            continue
        if max_price is not None and p.price > max_price:
            continue

        themes = _themes(p.name, p.search_tags)
        shared = base_themes & themes
        same_specific = sorted(spec for _, spec in shared)                                  # also Saybrook
        same_group = sorted({g for g, _ in base_themes} & {g for g, _ in themes} - {g for g, _ in shared})  # also family
        same_category = p.category == original.category
        same_fabric = bool(fabric) and fabric == base_fabric
        score = 3 * same_category + 3 * len(same_specific) + 2 * len(same_group) + same_fabric
        if score == 0:
            continue
        reasons = (
            (["same category"] if same_category else [])
            + [f"also {_label(w)}" for w in same_specific[:2]]
            + [f"also a {g} piece" for g in same_group[:1]]
            + ([f"{fabric} like the original"] if same_fabric and not color else [])
        )
        scored.append((score, Alternative(
            product_id=p.product_id, name=p.name, category=p.category, colors=p.colors, price=p.price,
            sizes_in_stock=in_stock, snippet=_snippet(p.description), reason=", ".join(reasons),
        )))

    scored.sort(key=lambda sa: (-sa[0], sa[1].price, sa[1].name))
    alternatives = [a for _, a in scored[: max(1, min(limit, 8))]]
    ctx.deps.seen_product_ids.update(a.product_id for a in alternatives)
    ctx.deps.quoted_prices.update(a.price for a in alternatives)
    return AlternativesResult(
        for_product_id=original.product_id, for_name=original.name,
        size=wanted_size, color=color, alternatives=alternatives,
    )


# --- The shopper ------------------------------------------------------------

def get_customer_profile(ctx: RunContext[ShopDeps]) -> CustomerProfile:
    """Who is chatting: name, email, member since, and products shown to them in earlier chats.

    Call this when the shopper asks about their account ("what email am I using?"), or refers to
    something from a previous conversation ("that hoodie you showed me last week"). Only ever
    returns the current shopper. For a guest, logged_in is false and nothing else is known.
    """
    c = ctx.deps.customer
    if c is None:
        return CustomerProfile(logged_in=False)
    past = memory.recent_products(c.user_id)
    ctx.deps.history_product_ids.update(p.product_id for p in past)
    return CustomerProfile(
        logged_in=True,
        first_name=c.first_name,
        last_name=c.last_name,
        email=c.email,
        member_since=c.member_since[:10],
        saved_messages=memory.message_count(c.user_id),
        recent_products=past,
    )


SHOP_TOOLS = [
    search_products,
    get_product_description,
    get_price,
    check_stock,
    find_alternatives,
    get_customer_profile,
]

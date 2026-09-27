"""Pydantic / PydanticAI types shared by the API, the agent and its tools."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

SIZES = ("XS", "S", "M", "L", "XL", "XXL")
Size = Literal["XS", "S", "M", "L", "XL", "XXL"]


# --- Catalogue -------------------------------------------------------------

class SizeStock(BaseModel):
    size: str
    quantity: int


class Product(BaseModel):
    """One catalogue item as the website shows it (a product card)."""

    product_id: str
    name: str
    garment_type: str
    category: str
    description: str
    colors: list[str]
    search_tags: list[str]
    image_url: str
    price: float
    total_stock: int
    sizes_in_stock: list[str] = Field(default_factory=list, description="Sizes with at least one unit, XS to XXL.")


class ProductDetail(Product):
    """A product plus stock for each size (the single-item page)."""

    inventory: list[SizeStock]


# --- What the agent's tools return ------------------------------------------
# Each lookup returns only what answers its question, with the database's own
# values. Smaller results mean fewer tokens and less for the model to misread.

LOW_STOCK = 3  # 1-3 units left counts as "low stock" (the product page uses the same rule)

StockStatus = Literal["in_stock", "low_stock", "sold_out"]


class ProductMatch(BaseModel):
    """One search_products hit: enough to pick the right product and compare options."""

    product_id: str
    name: str
    category: str
    colors: list[str] = Field(description="Colors on the item (fabric, then print). Not color options.")
    price: float
    sizes_in_stock: list[str] = Field(description="Sizes with at least one unit. Use check_stock for exact counts.")
    snippet: str = Field(description="Start of the description, to judge the match. Use get_product_description for all of it.")


class SearchResults(BaseModel):
    """What search_products returns: an id for this search plus the top matches."""

    search_id: int = Field(
        description="Put this in page_results.search_id to show ALL matches of this search on the website."
    )
    total_matches: int = Field(description="How many products match in total (the page shows all of them).")
    matches: list[ProductMatch] = Field(description="The best matches, up to `limit`.")


class Alternative(ProductMatch):
    reason: str = Field(description="Why it's similar, e.g. 'same category, also Saybrook, navy like the original'.")


class AlternativesResult(BaseModel):
    """find_alternatives: similar products that are in stock."""

    for_product_id: str
    for_name: str
    size: str | None = Field(description="Every alternative has at least one unit in this size (normalized).")
    color: str | None = Field(description="Every alternative's fabric is this color, when given.")
    alternatives: list[Alternative] = Field(description="Most similar first. Empty means nothing similar fits.")


class ProductDescription(BaseModel):
    """get_product_description: what the item is and looks like."""

    product_id: str
    name: str
    garment_type: str = Field(description="The catalogue's wording, e.g. 'pullover hoodie'.")
    category: str
    description: str = Field(description="Full description. If it starts with 'No detailed description yet', we have none on file.")
    colors: list[str] = Field(
        description=(
            "Colors you can see on the item: the fabric first, then the print. Each product is one "
            "colorway; this is NOT a list of color options."
        )
    )


class ProductPrice(BaseModel):
    """get_price: the catalogue price."""

    product_id: str
    name: str
    price: float = Field(description="Price in US dollars, exactly as in the catalogue.")
    currency: Literal["USD"] = "USD"


class SizeAvailability(BaseModel):
    size: Size
    quantity: int = Field(description="Units on hand right now.")
    status: StockStatus


class StockReport(BaseModel):
    """check_stock: units on hand, size by size."""

    product_id: str
    name: str
    sizes: list[SizeAvailability] = Field(description="Every size we make for this product, XS to XXL.")
    sizes_in_stock: list[Size]
    sold_out_sizes: list[Size]
    total_in_stock: int
    requested_size: str | None = Field(
        default=None,
        description="The size the shopper asked about, normalized when we make it (e.g. 'medium' -> 'M').",
    )
    requested_size_status: StockStatus | Literal["not_offered"] | None = Field(
        default=None, description="'not_offered' means we don't make that size at all (only XS-XXL)."
    )
    summary: str = Field(description="One plain sentence stating the answer. Safe to repeat to the shopper.")


class PastProduct(BaseModel):
    product_id: str
    name: str
    last_shown: str = Field(description="When it was last shown in this shopper's chat (UTC).")


class CustomerProfile(BaseModel):
    """get_customer_profile: who is chatting. Only ever the current shopper."""

    logged_in: bool
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    member_since: str | None = Field(default=None, description="Account creation date, YYYY-MM-DD.")
    saved_messages: int = Field(default=0, description="Messages in their saved chat history.")
    recent_products: list[PastProduct] = Field(
        default_factory=list, description="Products shown to them in earlier chats, most recent first (max 10)."
    )


# --- Agent run --------------------------------------------------------------

@dataclass
class Customer:
    """The logged-in shopper, from the users table. Never includes the password hash."""

    user_id: int
    first_name: str
    last_name: str
    email: str
    member_since: str  # users.created_at, "YYYY-MM-DD HH:MM:SS"


@dataclass
class PageInfo:
    """The page the shopper is on, checked against the database by the server."""

    path: str
    kind: str  # "product", "results", "catalogue", "home", "about", "account", "other"
    label: str | None = None  # e.g. "Chat results: Hoodies", "Category: Crewnecks"
    product: "ProductDescription | None" = None  # set on a product page
    visible: list[tuple[str, str]] = field(default_factory=list)  # (product_id, name) on a list page
    visible_total: int = 0


@dataclass
class ShopDeps:
    """Per-request context handed to the agent and its tools."""

    customer: Customer | None = None  # None = guest
    page: PageInfo | None = None
    # What safety.scrub_message() removed from this message, e.g. ["card number"].
    removed_sensitive: list[str] = field(default_factory=list)
    # Every product id a tool returned during this run. The API only turns
    # these into cards, so the model can't show an item it never looked up.
    seen_product_ids: set[str] = field(default_factory=set)
    # Products shown in the replayed chat history. Allowed as cards, so "show me
    # that hoodie again" works in a later session.
    history_product_ids: set[str] = field(default_factory=set)
    # Facts the tools returned this run, for the reply fact-check (agent.py).
    quoted_prices: set[float] = field(default_factory=set)
    stock_counts: set[int] = field(default_factory=set)
    # Dollar amounts the shopper typed ("under $40"), which the reply may repeat.
    shopper_amounts: set[float] = field(default_factory=set)
    fact_check_retries: int = 0
    # Every search_products call this run, in order; the index is its search_id.
    # Holds the FULL ordered match list, not just what the model was shown.
    searches: list["SearchRecord"] = field(default_factory=list)


@dataclass
class SearchRecord:
    """One search_products call: what was asked and every matching id, best first."""

    filters: dict
    product_ids: list[str]


class AgentReply(BaseModel):
    """The agent's structured answer (PydanticAI output_type)."""

    reply: str = Field(
        description="What to say to the shopper. Short, friendly, plain text; **bold** and '- ' bullets are allowed."
    )
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=6,
        description=(
            "product_id values to show as cards under the reply, best match first. Only ids returned by a "
            "tool in this conversation. Empty when no specific product is being suggested."
        ),
    )
    page_results: "PageResultsChoice | None" = Field(
        default=None,
        description=(
            "Set when the shopper is browsing a type of item or collection (e.g. 'what hoodies do you have?'): "
            "the website then shows every match of that search as product cards. Leave null for questions "
            "about one specific product, policies or small talk."
        ),
    )


class PageResultsChoice(BaseModel):
    """Which search to put on the website, and what to call it."""

    search_id: int = Field(description="search_id from a search_products call in THIS message.")
    heading: str = Field(max_length=60, description="Short title for the results, e.g. 'Hoodies' or 'Gray tees under $40'.")


# --- Chat API ---------------------------------------------------------------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)
    # Cards shown with an assistant message, so replayed history says which products it meant.
    product_ids: list[str] = Field(default_factory=list, max_length=6)


class PageContext(BaseModel):
    """What the browser says is on screen. The server checks every id against the catalogue."""

    path: str = Field(default="/", max_length=200)
    product_id: str | None = Field(default=None, max_length=120, description="Set on /products/<id>.")
    visible_product_ids: list[str] = Field(
        default_factory=list, max_length=60, description="Product cards on screen, in order (list pages)."
    )
    visible_total: int = Field(default=0, ge=0, le=500)
    label: str | None = Field(default=None, max_length=80, description="e.g. 'Chat results: Hoodies'.")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    # Only used for guests. Logged-in shoppers' history is read from the database,
    # so it can't be edited by the browser.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    # The page the shopper is looking at, so "do you have this in pink?" works.
    page: PageContext | None = None


class ChatMessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    products: list[Product] = Field(default_factory=list)


class PageResults(BaseModel):
    """Search results for the website to show as product cards (the API contract)."""

    heading: str
    products: list[Product] = Field(description="Every match of the chosen search, best first, read fresh from the database.")
    total: int
    filters: dict = Field(description="The search that produced these results, e.g. {'category': 'Hoodies'}.")


class ChatResponse(BaseModel):
    reply: str
    products: list[Product] = Field(default_factory=list, description="Small cards shown inside the chat reply.")
    page_results: PageResults | None = Field(
        default=None, description="When set, the website shows these products as full cards on the page."
    )
    checks: list[str] = Field(
        default_factory=list,
        description="What was looked up live for this reply, e.g. ['catalogue', 'price', 'stock'] (shown under the reply).",
    )
    saved: bool = Field(description="True when the turn was stored in the shopper's chat history.")


AgentReply.model_rebuild()

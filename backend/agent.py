"""The Campus Customs shop agent: wiring only.

main.py calls :func:`run_chat`. This file builds the PydanticAI agent once
(gpt-6-astra through Portkey, the system prompt from prompts/prompt.md, the
tools from tools.py, the output type from models.py) and turns a finished run
into a ChatResponse with product cards from the database.
"""

import asyncio
import itertools
import logging
import os
import re
import time
import weakref
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, ModelRetry, RunContext, capture_run_messages
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, ToolCallPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import audit
from catalogue import get_products
from context import describe_customer, describe_page
from models import AgentReply, ChatResponse, ChatTurn, PageResults, ShopDeps
from tools import SHOP_TOOLS

TOOL_NAMES = {t.__name__ for t in SHOP_TOOLS}
# PydanticAI's name for the tool the model calls to hand back AgentReply.
OUTPUT_TOOL_NAMES = {"final_result"}

log = logging.getLogger("campus_customs.agent")

HERE = Path(__file__).resolve().parent
PROMPT_PATH = HERE / "prompts" / "prompt.md"

PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
MODEL_NAME = "gpt-6-astra"

# The key can live in hw4/.env or the course folder's .env (one level up).
# load_dotenv never overrides, so the first file that sets it wins.
load_dotenv(HERE.parent / ".env")
load_dotenv(HERE.parent.parent / ".env")

# How many earlier messages the agent sees. Enough for "what about the gray one?"
# without resending a whole semester of chat.
HISTORY_MESSAGES = 12

# A normal answer is 1-3 model requests (search, maybe details, answer). The cap
# stops a confused run from looping; PydanticAI's default would allow 50.
RUN_LIMITS = UsageLimits(request_limit=8, tool_calls_limit=10)

# Azure's content filter (in front of gpt-6-astra) rejects some messages before
# the model sees them, most often jailbreak attempts ("ignore your instructions").
# That isn't an outage, so answer like the prompt's safety rules would.
FILTERED_REPLY = (
    "I can only help with Campus Customs products, sizes, stock and store policies. "
    "Is there something I can help you find?"
)

# Most cards the website shows for one chat search (the whole catalogue is 102).
MAX_PAGE_RESULTS = 60

FALLBACK_REPLY = (
    "Sorry, I'm having trouble answering right now. Please try again in a moment, or reach the "
    "team at orderdept@campuscustoms.com or (475) 301-4205."
)


# One agent per event loop. The OpenAI client's connection pool belongs to the
# loop it first ran on; Uvicorn has a single loop, but tests (and anything that
# starts a new loop) would otherwise reuse a pool whose loop has closed.
_agents: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, Agent[ShopDeps, AgentReply]]" = (
    weakref.WeakKeyDictionary()
)


def build_agent() -> Agent[ShopDeps, AgentReply]:
    """The agent for the running event loop, built once and reused."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # called outside async code, e.g. a quick import check
        return _new_agent()
    if loop not in _agents:
        _agents[loop] = _new_agent()
    return _agents[loop]


def _new_agent() -> Agent[ShopDeps, AgentReply]:
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing. Add it to hw4/.env or the parent folder's .env.")

    provider = OpenAIProvider(openai_client=AsyncOpenAI(api_key=api_key, base_url=PORTKEY_BASE_URL))
    agent = Agent(
        OpenAIResponsesModel(MODEL_NAME, provider=provider),
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        deps_type=ShopDeps,
        output_type=AgentReply,
        tools=SHOP_TOOLS,
        retries=2,
    )

    @agent.output_validator
    def fact_check(ctx: RunContext[ShopDeps], output: AgentReply) -> AgentReply:
        """Check every price and stock count in the reply against this turn's tool results.

        Runs before the shopper sees anything. A mismatch sends the reply back to the model
        (ModelRetry) with what was wrong; after `retries` failed attempts the shopper gets the
        fallback message instead of a wrong number.
        """
        problems = unverified_numbers(output.reply, ctx.deps)
        if problems:
            ctx.deps.fact_check_retries += 1
            log.warning("Fact-check sent the reply back: %s", "; ".join(problems))
            raise ModelRetry(
                "Fact-check failed: " + "; ".join(problems) + ". Every price and stock count must come from a "
                "tool result in THIS message. Call get_price / check_stock for it, or remove the number."
            )
        return output

    @agent.instructions
    def shopper_context(ctx: RunContext[ShopDeps]) -> str:
        """Per-request facts, added after the prompt file: who is chatting and what's on their screen.

        Built by code from ShopDeps (context.py), so the agent knows the customer and the page
        without spending a tool call.
        """
        lines = ["## Who is chatting", *describe_customer(ctx.deps.customer),
                 "", "## What's on their screen", *describe_page(ctx.deps.page)]
        if ctx.deps.removed_sensitive:
            lines += ["", "## Removed from this message",
                      f"- For their safety, code removed a {' and a '.join(ctx.deps.removed_sensitive)} from the "
                      "shopper's message before you saw it. Briefly remind them never to share that in a chat; "
                      "this shop never needs it. Then help with the rest of their question."]
        return "\n".join(lines)

    return agent


# --- Reply fact-check -------------------------------------------------------

MONEY = re.compile(r"\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")
# "2 left", "8 in stock", "5 available", "only 3", "just 2"
COUNT = re.compile(r"\b(?:only|just)\s+(\d{1,4})\b|\b(\d{1,4})\s+(?:left|in stock|available|remaining)\b", re.I)
MAX_ITEMS_IN_TOTAL = 4  # "$136 for both" = a sum of up to this many looked-up prices


def amounts_in(text: str) -> set[float]:
    return {float(m.replace(",", "")) for m in MONEY.findall(text)}


def unverified_numbers(reply: str, deps: ShopDeps) -> list[str]:
    """Prices and stock counts in `reply` that no tool returned this turn (empty list = all good)."""
    problems = []
    prices = sorted(deps.quoted_prices)
    totals = {
        round(sum(combo), 2)
        for k in range(1, MAX_ITEMS_IN_TOTAL + 1)
        for combo in itertools.combinations_with_replacement(prices, k)
    }
    for amount in sorted(amounts_in(reply)):
        if round(amount, 2) not in totals and amount not in deps.shopper_amounts:
            problems.append(f"you wrote ${amount:g} but no tool returned that price")
    for only, before in COUNT.findall(reply):
        n = int(only or before)
        if n not in deps.stock_counts:
            problems.append(f"you wrote a stock count of {n} but check_stock didn't return it")
    return problems


# Tool -> what the "Checked live" note under the reply says.
CHECK_LABELS = {
    "search_products": "catalogue", "find_alternatives": "catalogue", "get_product_description": "description",
    "get_price": "price", "check_stock": "stock", "get_customer_profile": "your account",
}


def _to_messages(history: list[ChatTurn]) -> list[ModelMessage]:
    """Replay earlier chat as plain user/assistant text turns.

    Assistant turns get a note naming the products their cards showed, so "the second one" or
    "that hoodie from before" still resolves in a later session.
    """
    messages: list[ModelMessage] = []
    for turn in history[-HISTORY_MESSAGES:]:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
            continue
        text = turn.content
        if turn.product_ids:
            text += "\n\n[Cards shown: " + ", ".join(f"`{pid}`" for pid in turn.product_ids) + "]"
        messages.append(ModelResponse(parts=[TextPart(content=text)]))
    return messages


async def run_chat(message: str, history: list[ChatTurn], deps: ShopDeps) -> tuple[ChatResponse, bool]:
    """Answer one shopper message and record the run in the audit trail.

    Returns (response, ok). Never raises: a failed run becomes a polite reply
    with ok=False, so the caller can skip saving it to the chat history.
    """
    deps.history_product_ids.update(pid for turn in history for pid in turn.product_ids)
    deps.shopper_amounts = amounts_in(message)
    replay = _to_messages(history)
    started, started_at = time.monotonic(), audit.now()
    result = None

    # capture_run_messages keeps the loop's messages even when the run fails,
    # so failed runs still show their tool calls in the audit trail.
    with capture_run_messages() as captured:
        try:
            result = await build_agent().run(message, message_history=replay, deps=deps, usage_limits=RUN_LIMITS)
            stop = "final_response"
        except ModelHTTPError as exc:
            if "content_filter" in str(exc.body):
                log.warning("Message blocked by the provider's content filter")
                stop, response, ok = "content_filter", ChatResponse(reply=FILTERED_REPLY, saved=False), True
            else:
                log.exception("Agent run failed")
                stop, response, ok = "model_error", ChatResponse(reply=FALLBACK_REPLY, saved=False), False
        except UsageLimitExceeded as exc:
            # The loop hit RUN_LIMITS (too many model requests or tool calls).
            log.warning("Agent run stopped by usage limits: %s", exc)
            stop, response, ok = "usage_limit", ChatResponse(reply=FALLBACK_REPLY, saved=False), False
        except UnexpectedModelBehavior as exc:
            # E.g. the fact-check rejected every attempt: better no answer than a wrong number.
            log.warning("Agent gave up (%s); sent the fallback reply", exc)
            stop = "fact_check_failed" if deps.fact_check_retries else "model_error"
            response, ok = ChatResponse(reply=FALLBACK_REPLY, saved=False), False
        except Exception:
            log.exception("Agent run failed")
            stop, response, ok = "error", ChatResponse(reply=FALLBACK_REPLY, saved=False), False

    if result is not None:
        response, ok = _build_response(result, deps), True
        loop_messages = result.new_messages()
    else:
        loop_messages = captured[len(replay):] if len(captured) >= len(replay) else list(captured)

    _audit(message, deps, loop_messages, result, stop, response.reply, started_at, started)
    return response, ok


def _build_response(result, deps: ShopDeps) -> ChatResponse:
    output: AgentReply = result.output
    # Which lookups backed this answer, e.g. "check_stock(product_id='yale-dad-crewneck', size='L')".
    calls = [
        f"{part.tool_name}({', '.join(f'{k}={v!r}' for k, v in part.args_as_dict().items())})"
        for msg in result.new_messages()
        for part in getattr(msg, "parts", [])
        if isinstance(part, ToolCallPart) and part.tool_name in TOOL_NAMES
    ]
    log.info("Tools used: %s", "; ".join(calls) or "none")
    if deps.fact_check_retries:
        log.info("Fact-check: reply fixed after %d retry(ies)", deps.fact_check_retries)
    used = [part.split("(")[0] for part in calls]
    checks = list(dict.fromkeys(CHECK_LABELS[name] for name in used if name in CHECK_LABELS))
    # Only show cards for products the agent actually saw: returned by a tool this
    # run, on the shopper's screen, or shown earlier in the replayed history. Look
    # them up fresh so the card's price is the database's.
    allowed = deps.seen_product_ids | deps.history_product_ids
    if deps.page:
        allowed |= {pid for pid, _ in deps.page.visible}
        if deps.page.product:
            allowed.add(deps.page.product.product_id)
    ids = list(dict.fromkeys(pid for pid in output.product_ids if pid in allowed))
    dropped = set(output.product_ids) - set(ids)
    if dropped:
        log.warning("Dropped product ids the tools never returned: %s", sorted(dropped))
    return ChatResponse(
        reply=output.reply.strip(),
        products=get_products(ids),
        page_results=_page_results(output, deps),
        checks=checks,
        saved=False,
    )


def _audit(message, deps: ShopDeps, loop_messages, result, stop: str, reply: str, started_at: str, started: float):
    """Append this run to output/audit_trail.json. A logging failure never breaks the chat."""
    try:
        usage = getattr(result, "usage", None)
        if callable(usage):  # a method in older PydanticAI versions, a property in 2.x
            usage = usage()
        audit.append({
            "time": started_at,
            "run_id": getattr(result, "run_id", None),
            "who": f"user {deps.customer.user_id}" if deps.customer else "guest",
            "page": deps.page.path if deps.page else None,
            "message": audit.short(message),
            "steps": audit.steps_from(loop_messages, OUTPUT_TOOL_NAMES),
            "fact_check_retries": deps.fact_check_retries,
            "stop_reason": stop,
            "reply": audit.short(reply),
            "usage": {
                "requests": getattr(usage, "requests", None),
                "tool_calls": getattr(usage, "tool_calls", None),
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
            } if usage else None,
            "duration_ms": round((time.monotonic() - started) * 1000),
        })
    except Exception:
        log.exception("Could not write the audit trail")


def _page_results(output: AgentReply, deps: ShopDeps) -> PageResults | None:
    """Turn the agent's page_results choice into full product cards.

    The agent only names a search_id; the products are the complete, ordered
    match list that search_products recorded, loaded fresh from the database.
    A search_id the agent didn't produce this run is ignored.
    """
    choice = output.page_results
    if choice is None:
        return None
    if not 0 <= choice.search_id < len(deps.searches):
        log.warning("Ignored page_results with unknown search_id %s", choice.search_id)
        return None
    search = deps.searches[choice.search_id]
    if not search.product_ids:
        return None
    products = get_products(search.product_ids[:MAX_PAGE_RESULTS])
    log.info("Page results: %r, %d products from search %s", choice.heading, len(products), search.filters)
    return PageResults(heading=choice.heading.strip(), products=products, total=len(search.product_ids), filters=search.filters)

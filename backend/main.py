"""Campus Customs API: catalogue, product images, accounts and the shop chatbot.

Run from hw4/backend/:
    uvicorn main:app --reload --port 8000

The agent lives next to this file: agent.py (wiring), tools.py, models.py and
prompts/prompt.md (system prompt).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Cookie, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import memory
from agent import run_chat
from auth import router as auth_router
from auth import user_from_token
from catalogue import get_product, list_products
from context import customer_for, page_info_for
from db import DATA_DIR, init_schema
from models import ChatMessageOut, ChatRequest, ChatResponse, Product, ProductDetail, ShopDeps
from safety import scrub_message

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_schema()
    yield


app = FastAPI(title="Campus Customs API", lifespan=lifespan)
app.include_router(auth_router)

FIELD_LABELS = {
    "first_name": "First name",
    "last_name": "Last name",
    "email": "Email",
    "password": "Password",
    "message": "Message",
}


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Turn validation errors into one readable sentence.

    FastAPI's default response echoes the submitted values back, which would
    include the password, so only field names and messages are returned.
    """
    messages = []
    for err in exc.errors():
        field = str(err["loc"][-1]) if err["loc"] else ""
        label = FIELD_LABELS.get(field, field)
        msg = err["msg"].removeprefix("Value error, ")
        if err["type"] == "string_too_short":
            msg = f"must be at least {err['ctx']['min_length']} characters"
        elif err["type"] == "string_too_long":
            msg = f"must be at most {err['ctx']['max_length']} characters"
        elif err["type"] == "missing":
            msg = "is required"
        messages.append(msg if msg[0].isupper() else f"{label} {msg}.")
    return JSONResponse(status_code=422, content={"detail": " ".join(messages)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Product images: catalogue.image_file_path is "products/<file>.jpg" relative
# to data/, so it becomes /media/products/<file>.jpg. Only the products folder
# is mounted; mounting all of data/ would let anyone download the database.
app.mount("/media/products", StaticFiles(directory=DATA_DIR / "products"), name="media")


# --- Catalogue --------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/products", response_model=list[Product])
def products() -> list[Product]:
    return list_products()


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def product(product_id: str) -> ProductDetail:
    found = get_product(product_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return found


# --- Chat -------------------------------------------------------------------

# Earlier messages the agent sees for a logged-in shopper.
HISTORY_LIMIT = 12


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, cc_session: str | None = Cookie(default=None)) -> ChatResponse:
    """One shopper message in, one agent reply (plus product cards) out.

    Logged-in shoppers: history comes from chat_messages (memory.py) and the turn is saved.
    Guests: the browser sends recent history, and nothing is stored.
    Either way the agent gets ShopDeps with the customer (or None) and the checked page context.
    """
    user = user_from_token(cc_session)
    # Card numbers, SSNs and typed passwords never reach the model, the chat
    # history table or the audit trail (safety.py).
    message, removed = scrub_message(body.message.strip())
    if not message:
        raise HTTPException(status_code=422, detail="Message is required.")

    history = memory.load_turns(user.id, HISTORY_LIMIT) if user else body.history
    deps = ShopDeps(customer=customer_for(user), page=page_info_for(body.page), removed_sensitive=removed)
    response, ok = await run_chat(message, history, deps)

    if user and ok:
        memory.save_turn(user.id, message, response.reply, response.products)
        response.saved = True
    return response


def _require_user(cc_session: str | None):
    user = user_from_token(cc_session)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Log in to see your chat history.")
    return user


@app.get("/api/chat/history", response_model=list[ChatMessageOut])
def chat_history(cc_session: str | None = Cookie(default=None)) -> list[ChatMessageOut]:
    return memory.load_for_display(_require_user(cc_session).id)


@app.delete("/api/chat/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_chat_history(cc_session: str | None = Cookie(default=None)) -> None:
    memory.clear(_require_user(cc_session).id)

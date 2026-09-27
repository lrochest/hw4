# Campus Customs: shop website + AI shop assistant

A customer website for **Yale Bulldog Blue by Campus Customs** (officially licensed Yale apparel,
57 Broadway, New Haven). Shoppers can browse the catalogue, create an account, and chat with an
assistant that answers from the real product database: price, stock by size, similar items in
stock, and matching products shown right on the page.

- **Frontend:** React + Vite + TypeScript (`frontend/`)
- **Backend:** Python FastAPI (`backend/main.py`)
- **Agent:** PydanticAI with `gpt-6-astra` through Portkey. It is four files in `backend/`:
  - `prompts/prompt.md`: the system prompt (voice, honesty and safety rules)
  - `agent.py`: agent wiring (model, prompt, tools, output type, fact-check, audit trail)
  - `tools.py`: tools the agent can call (search, description, price, stock, alternatives, customer profile)
  - `models.py`: Pydantic / PydanticAI structured types
- **Docs:** `output/harness.md` explains how the whole system works (database, auth, agent,
  tools, model fields, safety, specs). Also see `output/usability.md`, `output/design.md` and
  `output/app_check.html` (live-site screenshots).

---

## 1. Place the data pack (not in git)

The database and product photos are **not** in this repository. Put them here:

```
hw4/
└── data/
    ├── campus_customs.db     SQLite: catalogue, inventory, users, chat_messages
    └── products/             product images referenced by catalogue.image_file_path
```

If you have the zip, unzip it inside `hw4/` so it creates `data/`:

```bash
cd hw4
unzip data.zip
```

On first start the backend adds a `sessions` table and an index to the database, and it
upgrades seed users' password hashes the first time they log in. It never changes the
catalogue or inventory.

## 2. Add your API key

```bash
cd hw4
cp .env.example .env
```

Edit `.env` and set `PORTKEY_API_KEY`. The backend reads `hw4/.env`, or a `.env` one folder up.
The real `.env` is ignored by git.

## 3. Run the backend (FastAPI, port 8000)

Requires Python 3.11+ (tested with 3.14).

```bash
cd hw4
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd backend
uvicorn main:app --reload --port 8000
```

Run it **from `backend/`**, because the backend uses plain imports (`from agent import …`).
Check it's up: <http://localhost:8000/api/health> → `{"status": "ok"}`.

## 4. Run the frontend (Vite, port 5173)

Requires Node.js 20+ (tested with 24). In a second terminal:

```bash
cd hw4/frontend
npm install
npm run dev
```

Open **<http://localhost:5173>**. Vite proxies `/api` and `/media` to the backend on port 8000,
so both must be running.

## 5. Try it

- **Test account:** `test@campuscustoms.yale.edu` / `password`, or create your own.
- **Ask the chat** (bottom right):
  - "What hoodies do you have?" puts every matching hoodie on the page as product cards.
  - On a product page: "Do you have this in large?" gives the live stock per size. If your size
    is sold out, it suggests similar items that are in stock.
  - "What's your return policy?"
- Logged-in chats are saved and come back next time. Guests can chat too, but nothing is saved.
- Every agent run is appended to `output/audit_trail.json` (never wiped).

## Project layout

```
hw4/
├── AI_prompts.md            prompts used for each problem
├── README.md
├── requirements.txt         backend Python packages
├── .env.example             placeholder settings (copy to .env)
├── .gitignore               keeps data/, .env, .venv, node_modules out of git
├── backend/
│   ├── main.py              FastAPI app: products, images, accounts, chat
│   ├── agent.py             ┐
│   ├── tools.py             │ the agent
│   ├── models.py            │
│   ├── prompts/prompt.md    ┘
│   ├── auth.py, security.py accounts, password hashing, sessions
│   ├── db.py, catalogue.py  SQLite access, read-only catalogue queries
│   ├── memory.py            saved chat history for logged-in shoppers
│   ├── context.py           who is chatting + what's on their screen
│   ├── safety.py            removes card numbers / SSNs / passwords from messages
│   └── audit.py             append-only audit trail
├── frontend/                Vite + React + TypeScript site
│   └── src/                 pages/, components/, api.ts, index.css …
├── docs/store_research.md   notes from yalebulldogblue.com
└── output/
    ├── harness.md           how the system works
    ├── usability.md         Problem 9 improvements
    ├── design.md            Problem 10 design
    ├── app_check.html       Problem 11 live-site check (open in a browser)
    ├── app_check_images/    screenshots for app_check.html
    └── audit_trail.json     agent-loop audit trail (append-only)
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `PORTKEY_API_KEY is missing` | Create `hw4/.env` from `.env.example`. |
| `unable to open database file` | The data pack isn't at `hw4/data/campus_customs.db`. |
| Images don't load | `hw4/data/products/` is missing, or the backend isn't running. |
| `ModuleNotFoundError: agent` | Start Uvicorn from inside `hw4/backend/`. |
| Products page says it can't load | Start the backend on port 8000 before the frontend. |

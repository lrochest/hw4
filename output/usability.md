# Usability improvements (Problem 9)

Four improvements to the working shop: two on the website, two in the agent and backend.
Each one says what was added and why it helps a Campus Customs shopper or the business.

---

## Front end

### 1. Chat starters and "Ask about this item"

**What was added**

- **Suggested questions in the chat panel** that match the page you're on. You click one to
  send it.
  - Product page: "What sizes are in stock?", "Does this come in other colors?", "Show me
    something similar".
  - Products page or chat results: "Which of these are under $50?", "What's in stock in a
    medium?", "Which one would you pick?".
  - Anywhere else: "What hoodies do you have?", "Gift ideas for my dad", "What's your return
    policy?".
  - They show when the chat is empty and after each reply, in a row above the text box.
- **An "Ask about this item" button** on every product page, under the size grid. It opens
  the chat with the cursor in the text box and shows the product-page suggestions. The agent
  already knows which product "this" is from the page context (Problem 8).

**Why it helps**

- An empty chat box is a common reason people never use a chatbot. Starters show what the
  assistant can do (sizes, colors, gifts, policies) without the shopper having to think of a
  question.
- The questions match the page, so a shopper looking at a hoodie is one click away from "is it
  in my size?". That's the question that decides whether they buy.
- For the business: more shoppers try the assistant, and its answers use live stock, so more of
  them find something they can actually buy. On a phone, tapping a suggestion is faster than
  typing.

**Where to see it:** open any product page and click "Ask about this item", or open the chat on
Home, Products or About. Code: `frontend/src/components/ChatWidget.tsx` (`STARTERS`),
`frontend/src/chatEvents.ts`, `frontend/src/pages/ProductDetail.tsx`.

### 2. Stock and sort at a glance

**What was added**

- **A size row on every product card.** All six sizes, XS to XXL, appear under the price;
  sold-out sizes are greyed and struck through. The same cards appear on the Home page, the
  Products page and in chat results.
- **A "Size in stock" filter** on the Products page. Pick M and only products with at least one
  M left are shown.
- **A sort menu**: Featured, Price low to high, Price high to low, Name A–Z.
- Size and sort are saved in the URL (like the other filters), so the back button and shared
  links keep them.

**Why it helps**

- Shoppers shop in one size. Before, they had to open each product to find out it was sold out
  in theirs. Now they see it on the card, or hide those products entirely.
- Sorting by price helps a student on a budget, or someone shopping for a gift at a set price.
- For the business: fewer dead-end clicks on items that can't be bought, and more views of items
  that can. Sold-out sizes are shown honestly rather than hidden until the last step.

**Where to see it:** any product card (Home, Products, chat results); the "Size in stock" and
"Sort" menus on Products. The API now includes `sizes_in_stock` on every product
(`backend/catalogue.py`). Code: `frontend/src/components/ProductCard.tsx`,
`frontend/src/pages/Products.tsx`.

---

## Agent and backend

### 3. `find_alternatives` tool: in-stock look-alikes

**What was added**

- A new agent tool, `find_alternatives(product_id, size?, color?, max_price?, limit?)`. Given a
  product, it ranks the rest of the catalogue by similarity: same category, shared search tags
  (college, sport, family member, The Game…), and same fabric color. It returns only items
  **in stock in the requested size**, each with a short reason ("same category, also Saybrook,
  navy like the original").
- Prompt rules: when `check_stock` says the shopper's size is sold out, or they ask for this
  item in a color it isn't made in, or they ask for "something similar", call
  `find_alternatives` and offer the top one or two.

**Why it helps**

- "Sold out in L" is a dead end. "Sold out in L, but the Yale Dad Hoodie is in L" is a sale.
  This is the moment where a good shop assistant saves the sale, and the tool makes sure the
  suggestion really is in the shopper's size.
- Before, the agent had to improvise with `search_products` and often suggested items without
  checking the size. The tool does the size check in code, so the suggestion is right the first
  time and needs fewer model calls.

**How it ranks:** same category (+3), shared specific theme such as the same sport, college or
family member (+3 each), shared theme group such as "a family piece" or "a residential college
piece" (+2), same fabric color (+1). Garment words ("crewneck", "sweatshirt") are ignored,
because every item in the category shares them and they drowned out the themes in the first
version.

**Where to see it:** on the Yale Dad Crewneck page (sold out in L), ask "I need a large. Anything
like it?". Code: `find_alternatives` in `backend/tools.py`; `Alternative`, `AlternativesResult`
in `backend/models.py`; prompt rules in `backend/prompts/prompt.md`.

### 4. Fact-check on every reply (prices and stock counts)

**What was added**

- **An output validator** on the agent (PydanticAI `@agent.output_validator`). Before a reply
  goes to the shopper, code finds every dollar amount ("$68") and stock count ("2 left", "8 in
  stock") in it and checks each one against the values the tools returned **in this turn**.
  - Prices must match a catalogue price the tools returned, or a total of a few of them
    ("$136 for both"). Amounts the shopper typed ("under $40") are also allowed.
  - Stock counts must match a quantity `check_stock` returned.
  - If anything doesn't match, the reply is sent back to the model with a note
    ("You wrote $70 but no tool returned that price this turn. Call get_price or remove it.")
    to fix before the shopper sees it. If it still can't get it right, the shopper gets the
    polite fallback message, not a wrong number.
- **A "Checked live" note** under each chat reply that used the database, e.g. "✓ Checked live:
  catalogue · price · stock". It lists what was looked up for that answer and appears only when
  a lookup actually ran.

**Why it helps**

- The one thing a shop assistant must never do is quote a wrong price or promise a size that's
  gone. Instructions alone make that unlikely; the validator checks it in code every time.
  Numbers from an earlier chat, or guessed, get caught.
- For the business: a wrong price in the chat is a customer-service problem, and possibly a
  price the store is pressured to honor. This lowers that risk.
- The "Checked live" note tells shoppers they can trust the numbers, which matters more when
  the answer comes from an AI.

**Where to see it:** "✓ Checked live: …" appears in green under chat replies that looked
something up. The fact-check runs on every reply; when it sends one back, the backend log shows
`Fact-check sent the reply back: …`. Code: `fact_check` and `unverified_numbers()` in
`backend/agent.py`; the tools record what they returned in `ShopDeps.quoted_prices` and
`ShopDeps.stock_counts`; `checks` in `ChatResponse`.

---

## Checked in the running app

| Improvement | Test | Result |
|---|---|---|
| 1. Chat starters | Open the chat on a product page, on Products, and on About | ✅ Product, list and general suggestions respectively; they come back after each reply |
| 1. Ask about this item | Click it on the Yale Dad Crewneck page | ✅ Chat opens with the cursor in the box; "What sizes are in stock?" → "In stock in XS, S and XXL. Sold out in M, L and XL." |
| 2. Size row on cards | Products page | ✅ All six sizes on every card; e.g. the Big Yale Tri Blend T Shirt shows XS and L struck through |
| 2. Size filter | Crewnecks + "Size in stock: L" | ✅ 21 cards, matching the API count of crewnecks with L in stock; the Yale Dad Crewneck (sold out in L) is hidden |
| 2. Sort | "Price: high to low" / "low to high" on all 102 | ✅ Starts at $98 / $32 and is in order; saved in the URL (`?sort=price-desc`) |
| 3. find_alternatives | Dad Crewneck page: "I need a large. Anything like it?" | ✅ `check_stock` then `find_alternatives(size='large')`: "Sold out in large… the Yale Brother Crewneck and Yale Cousin Crewneck are in stock in L" (database: L = 2 and 15) |
| 3. find_alternatives | Baseball Left Chest Crewneck page: "I love this but I want it in gray" | ✅ "This one is only made in navy, but the Yale Sports Crewneck Baseball is heather gray…" |
| 3. find_alternatives | Architecture crewneck page: "Can I get this in a small?" | ✅ Sold out in S; offered the School Of Medicine 1/4 Zip, in stock in S |
| 4. Fact-check | Scripted model answers "$75, only 3 left in XL" for the Basic Hoodie | ✅ Sent back ("you wrote $75 but no tool returned that price; … stock count of 3…"); the model called `get_price` and `check_stock`, then answered "$68, and only 2 left in XL" |
| 4. Fact-check | Scripted model that keeps saying "$75" | ✅ After 2 retries the shopper gets the polite fallback, never the wrong price |
| 4. Fact-check | Real agent, guest history containing a wrong "$75" | ✅ The agent called `get_price` itself and corrected it to $68 |
| 4. Checked live note | Any lookup reply | ✅ "✓ Checked live: stock · catalogue" under the reply |


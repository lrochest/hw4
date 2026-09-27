# Design (Problem 10)

Direction: **collegiate heritage**. It should feel like a shop on Broadway with pennants on the
wall and prints pinned behind the counter, not a generic template. Every change below is aimed at
one thing: keeping shoppers browsing long enough to find their piece in their size.

## Fonts

| Change | Why it helps |
|---|---|
| **Fraunces** (editorial serif) for headlines and prices, with italic accents ("Blue that outlasts *the semester.*") | Feels like a Yale publication, not a discount site; a premium look supports $58–$98 prices. |
| **Graduate** (varsity lettering) for small labels: "THIS SEASON", "PICK YOUR SIZE", badges, the ticker | Instantly reads "college athletics"; ties every page to campus. |
| **Open Sans** kept for body text | Same as the real yalebulldogblue.com, and easy to read at small sizes. |

## Color

| Change | Why it helps |
|---|---|
| Yale navy `#00356b` + deep navy `#0b1f3a` on warm cream paper `#fbf8f2` / `#f6f1e7` | Warmer and more "heritage" than stark white; photos pop against cream. |
| Campus Customs orange-red `#f04f36` only for actions (Shop, Send, Ask the shop, the stamp) | One action color, so the next step is always obvious. |
| Gold `#c9a227` for small honors: stars, "Few sizes left", the licence tag | Adds a collegiate accent without competing with the buttons. |

## Hierarchy

- **Hero:** big headline, one orange "Shop the collection" button, a ghost "Ask the shop"
  button, and three trust points (licensed · made to order in 5–8 days · 30-day returns) right
  under it. The shopper knows what we sell, how it's made and how returns work before scrolling.
- **Varsity label → serif heading → muted text** on every section, so pages scan the same way.
- **Product page:** breadcrumbs → category label → name → price → description → colorway →
  size picker → one full-width "Ask about this item" button → store promises → "You might also
  like". It follows the order a shopper decides in.

## Motion (all turned off for "reduce motion" users)

| Motion | Why it helps |
|---|---|
| Rotating announcement bar (licensed · 57 Broadway · 5–8 days · 30-day returns) | Four trust messages in the space of one. |
| Hero headline rises in; three product prints drop in with tape strips; a spinning "Officially licensed · 57 Broadway" stamp | A memorable first second; the licence is the shop's main trust signal. |
| Tilted orange **ticker band** (Boola Boola ✦ The Game ✦ Family weekend…), pauses on hover | Campus energy, and it names the collections. |
| **Scroll reveal:** sections and cards fade up, cards staggered 70 ms apart | Makes scrolling feel rewarding, which keeps people browsing. |
| **Pennants wave** on hover | A playful, on-brand invitation to click a collection. |
| Card hover: lifts, the print straightens and zooms, "View details →" slides up | Clear feedback that the card is clickable, and a closer look at the print. |
| Product photo **zooms where the mouse is** | Lets shoppers inspect the print quality, the thing they're paying for. |
| Chat: panel springs open, messages slide in, typing dots bounce, pulsing green "Checking live stock" dot | The assistant feels alive and trustworthy. |

## Product presentation

- **Photos as gallery prints:** each product photo sits in a white print frame on a cream stage,
  tilted slightly (−1.2° to +1.2°, stable per product). The catalogue mixes black, white and grey
  photo backgrounds; as prints they look deliberate instead of messy.
- **Corner badges** from the collection: THE GAME, FAMILY, RES. COLLEGE, GRAD SCHOOL, VARSITY,
  BULLDOG. Shoppers spot "their" pieces while scrolling.
- **Honest flags:** "Few sizes left" (gold) or "Sold out" (grey), plus the XS–XXL size row with
  sold-out sizes struck through.
- **Product page:** color **swatches** with the fabric marked; a **size picker** that answers
  instantly ("XL is in stock · only 2 left. Made to order…" or "L is sold out. *Find something
  similar in L →*", which asks the chat); "Pairs well with / You might also like" (same
  collection first, in stock only); a shimmer skeleton while loading.
- **Home:** "Fly your colors" pennant collections, and an "Ask it like you'd ask us at the
  counter" band with real example questions that open the chat and send them.
- **About:** big-number fact row (57 · 5–8 · 30 · XS–XXL) and a pull quote.
- **Footer:** "Not sure about a size? *Ask the shop.*" call to action, and a huge outlined
  *Boola Boola* (the Yale fight song) watermark.

## Chat feel

| Change | Why it helps |
|---|---|
| Launcher is an orange pill, **"💬 Ask the shop"**, that pops in after the page loads | It says what it does; "Chat" didn't. |
| One gentle **nudge bubble** after 6 s on the first visit: "Looking for your size? I check live stock." (dismissable, once per session) | Invites the question that leads to a sale, without nagging. |
| Header: crest avatar, "The shop assistant", green **live dot** + "Checking live stock" | Tells shoppers the answers come from real stock, not guesses. |
| Rounded bubbles with a "tail" corner, navy for the shopper and white for the shop; product cards inside replies | Reads like a real conversation, and every suggestion is one tap from its page. |
| Typing dots with "Checking the shelves…" | Makes the few-second wait feel like work being done. |
| Round orange ↑ send button | Familiar messaging pattern. |

## Checked in the running app

Home hero, ticker, pennants (4 across on desktop, 2 on tablet, 1 on phone), ask band (clicking a
bubble sent "Do you have the Mom Hoodie in XXL?" and got "only 2 left" with a card and
"✓ Checked live"), product cards, product page (breadcrumbs, swatches, size picker for in-stock
and sold-out sizes, hover zoom, related products), footer, and the phone layout (375 px, no
sideways scrolling). Build and lint are clean.

## Files

`frontend/src/index.css` (whole design system), `index.html` (fonts), `components/NavBar.tsx`
(crest, rotating bar), `Footer.tsx`, `ProductCard.tsx`, `ChatWidget.tsx`, `pages/Home.tsx`,
`ProductDetail.tsx`, `About.tsx`, and helpers `useReveal.ts`, `swatches.ts`, `badgeFor()` in
`collections.ts`, `openChat({prompt, send})` in `chatEvents.ts`.

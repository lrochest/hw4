import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  clearChatHistory,
  fetchChatHistory,
  formatPrice,
  sendChatMessage,
  type ChatMessage,
  type PageResults,
} from '../api.ts'
import { useAuth } from '../useAuth.ts'
import { CHAT_VIEW, useChatResults } from '../useChatResults.ts'
import { usePageContext } from '../usePageContext.ts'
import { onOpenChat } from '../chatEvents.ts'
import ChatText from './ChatText.tsx'
import { Crest } from './NavBar.tsx'

const GUEST = 'guest'

// Suggested questions for the page the shopper is on.
const STARTERS = {
  product: ['What sizes are in stock?', 'Does this come in other colors?', 'Show me something similar'],
  list: ['Which of these are under $50?', "What's in stock in a medium?", 'Which one would you pick?'],
  general: ['What hoodies do you have?', 'Gift ideas for my dad', "What's your return policy?"],
}
const NO_MESSAGES: ChatMessage[] = []
const NUDGE_KEY = 'cc-chat-nudged'
const NUDGE_AFTER_MS = 6000

export default function ChatWidget() {
  const { user, loading } = useAuth()
  const { show } = useChatResults()
  const navigate = useNavigate()
  const owner = user ? String(user.id) : GUEST

  // Messages are tagged with whose they are, so logging in or out never shows
  // one person's conversation to another.
  const [thread, setThread] = useState<{ owner: string; messages: ChatMessage[] }>({ owner: GUEST, messages: [] })
  const messages = thread.owner === owner ? thread.messages : NO_MESSAGES

  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // What's on screen, so the agent knows what "this" (product page) or "these"
  // (list page) means. Pages report it with useReportPage().
  const { pathname, search } = useLocation()
  const { report } = usePageContext()
  const pageProductId = report.productId ?? null

  // Logged-in shoppers pick up their saved conversation.
  useEffect(() => {
    if (loading || !user) return
    let cancelled = false
    fetchChatHistory().then((saved) => {
      if (!cancelled) setThread({ owner: String(user.id), messages: saved })
    })
    return () => {
      cancelled = true
    }
  }, [user, loading])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [messages, open, sending])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  // "Ask about this item", "Ask the shop" and the example questions on Home.
  // The handler is registered once, so it calls the latest send() via a ref.
  const sendRef = useRef<(text: string) => Promise<void>>(async () => {})
  useEffect(() => {
    sendRef.current = send
  })
  useEffect(
    () =>
      onOpenChat(({ prompt, send: sendNow }) => {
        setOpen(true)
        setNudge(false)
        if (prompt && sendNow) void sendRef.current(prompt)
        else if (prompt) setDraft(prompt)
        // Already open: still move the cursor to the input.
        setTimeout(() => inputRef.current?.focus(), 0)
      }),
    [],
  )

  // A one-time nudge bubble next to the launcher, a few seconds into the first visit.
  const [nudge, setNudge] = useState(false)
  useEffect(() => {
    if (sessionStorage.getItem(NUDGE_KEY)) return
    const id = setTimeout(() => {
      setNudge(true)
      sessionStorage.setItem(NUDGE_KEY, '1')
    }, NUDGE_AFTER_MS)
    return () => clearTimeout(id)
  }, [])

  const starters = pageProductId
    ? STARTERS.product
    : pathname.startsWith('/products') && (report.visibleProductIds?.length ?? 0) > 0
      ? STARTERS.list
      : STARTERS.general
  const lastRole = messages.at(-1)?.role
  const showStarters = !sending && (lastRole === undefined || lastRole === 'assistant')

  const greeting =
    `Hi${user ? ` ${user.first_name}` : ''}! I'm the Campus Customs shop assistant. I check live stock and ` +
    'real prices, so ask me about sizes, colors, or a gift for your college, your team or your family.'

  // Put a chat search on the website: the Products page shows every match as a
  // full product card (see Products.tsx).
  function showOnPage(page: PageResults) {
    show(page)
    navigate(`/products?view=${CHAT_VIEW}`)
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    void send(draft)
  }

  async function send(raw: string) {
    const text = raw.trim()
    if (!text || sending) return

    const before = messages
    const withQuestion: ChatMessage[] = [...before, { role: 'user', content: text }]
    setThread({ owner, messages: withQuestion })
    setDraft('')
    setSending(true)
    try {
      const reply = await sendChatMessage(text, before, {
        path: pathname + search,
        product_id: pageProductId,
        visible_product_ids: (report.visibleProductIds ?? []).slice(0, 60),
        visible_total: report.visibleTotal ?? report.visibleProductIds?.length ?? 0,
        label: report.label ?? null,
      })
      setThread({
        owner,
        messages: [
          ...withQuestion,
          {
            role: 'assistant',
            content: reply.reply,
            products: reply.products,
            pageResults: reply.page_results,
            checks: reply.checks,
          },
        ],
      })
      if (reply.page_results && reply.page_results.products.length > 0) showOnPage(reply.page_results)
    } catch (err) {
      setThread({
        owner,
        messages: [...withQuestion, { role: 'assistant', content: (err as Error).message || 'Something went wrong.' }],
      })
    } finally {
      setSending(false)
    }
  }

  async function handleClear() {
    if (user) await clearChatHistory()
    setThread({ owner, messages: [] })
  }

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label="Shop chat">
          <header className="chat-header">
            <span className="chat-avatar" aria-hidden="true">
              <Crest />
            </span>
            <div className="chat-heading">
              <p className="chat-title">The shop assistant</p>
              <p className="chat-subtitle">
                <span className="chat-live-dot" aria-hidden="true" /> Checking live stock ·{' '}
                {user ? 'saved to your account' : 'log in to save this chat'}
              </p>
            </div>
            <div className="chat-header-actions">
              {messages.length > 0 && (
                <button className="chat-clear" onClick={handleClear} disabled={sending}>
                  Clear
                </button>
              )}
              <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
                ×
              </button>
            </div>
          </header>

          <div className="chat-messages" ref={listRef} aria-live="polite">
            <div className="chat-msg chat-msg-assistant">
              <p>{greeting}</p>
            </div>
            {messages.map((m, i) => (
              <div key={i} className={`chat-msg chat-msg-${m.role}`}>
                {m.role === 'assistant' ? <ChatText text={m.content} /> : <p>{m.content}</p>}
                {m.checks && m.checks.length > 0 && (
                  <p className="chat-checks" title="Looked up in the Campus Customs database for this answer">
                    ✓ Checked live: {m.checks.join(' · ')}
                  </p>
                )}
                {m.pageResults && m.pageResults.products.length > 0 && (
                  <button className="chat-show-page" onClick={() => showOnPage(m.pageResults!)}>
                    Show {m.pageResults.total} {m.pageResults.total === 1 ? 'result' : 'results'} on the page →
                  </button>
                )}
                {m.products && m.products.length > 0 && (
                  <div className="chat-products">
                    {m.products.map((p) => (
                      <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-product">
                        <img src={p.image_url} alt="" />
                        <span>
                          <span className="chat-product-name">{p.name}</span>
                          <span className="chat-product-price">{formatPrice(p.price)}</span>
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {sending && (
              <div className="chat-msg chat-msg-assistant chat-typing" aria-label="Looking that up">
                <span className="typing-dots" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                </span>
                Checking the shelves…
              </div>
            )}
          </div>

          {showStarters && (
            <div className="chat-starters" aria-label="Suggested questions">
              {starters.map((q) => (
                <button key={q} type="button" className="chat-starter" onClick={() => void send(q)}>
                  {q}
                </button>
              ))}
            </div>
          )}

          <form className="chat-form" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={pageProductId ? 'Ask about this item…' : 'Ask about a product…'}
              aria-label="Message"
              maxLength={1000}
            />
            <button type="submit" className="chat-send" disabled={sending || !draft.trim()} aria-label="Send">
              ↑
            </button>
          </form>
        </section>
      )}

      {nudge && !open && (
        <div className="chat-nudge" role="status">
          <button className="chat-nudge-body" onClick={() => { setNudge(false); setOpen(true) }}>
            Looking for your size? I check live stock.
          </button>
          <button className="chat-nudge-close" onClick={() => setNudge(false)} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}

      <button
        className={`chat-launcher ${open ? 'is-open' : ''}`}
        onClick={() => {
          setNudge(false)
          setOpen((o) => !o)
        }}
        aria-expanded={open}
        aria-label={open ? 'Close chat' : 'Open chat'}
      >
        {open ? (
          <span className="chat-launcher-x">×</span>
        ) : (
          <>
            <span className="chat-launcher-icon" aria-hidden="true">💬</span>
            <span className="chat-launcher-label">Ask the shop</span>
          </>
        )}
      </button>
    </div>
  )
}

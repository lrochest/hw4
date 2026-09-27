// Types and calls for the Campus Customs backend (backend/main.py).
// Requests go to /api/... and Vite proxies them to the FastAPI server.

export interface Product {
  product_id: string
  name: string
  garment_type: string
  category: string
  description: string
  colors: string[]
  search_tags: string[]
  image_url: string
  price: number
  total_stock: number
  sizes_in_stock: string[]
}

export const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL'] as const

export interface SizeStock {
  size: string
  quantity: number
}

export interface ProductDetail extends Product {
  inventory: SizeStock[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  products?: Product[]
  pageResults?: PageResults | null
  checks?: string[]
}

// The API contract for "chat search that updates the page": when the agent
// decides the shopper is browsing, /api/chat returns every match of its search.
export interface PageResults {
  heading: string
  products: Product[]
  total: number
  filters: Record<string, string | number>
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(res.status === 404 ? 'Not found' : `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export function fetchProducts(): Promise<Product[]> {
  return getJson<Product[]>('/api/products')
}

export function fetchProduct(productId: string): Promise<ProductDetail> {
  return getJson<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`)
}

export function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`
}

// ---------------------------------------------------------------------------
// Chat. POST /api/chat runs the PydanticAI agent. Logged-in shoppers' history
// is kept on the server; guests send their recent messages with each request.
// ---------------------------------------------------------------------------

export interface ChatReply {
  reply: string
  products: Product[]
  page_results: PageResults | null
  checks: string[]
  saved: boolean
}

// How many earlier guest messages to send; the server caps this too.
const GUEST_HISTORY = 12

// What's on screen, checked by the server against the catalogue (context.py).
export interface PageContextPayload {
  path: string
  product_id: string | null
  visible_product_ids: string[]
  visible_total: number
  label: string | null
}

export async function sendChatMessage(
  message: string,
  history: ChatMessage[],
  page: PageContextPayload,
): Promise<ChatReply> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify({
      message,
      // Guests only; the server uses saved history for logged-in shoppers.
      history: history.slice(-GUEST_HISTORY).map(({ role, content, products }) => ({
        role,
        content,
        product_ids: (products ?? []).slice(0, 6).map((p) => p.product_id),
      })),
      page,
    }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    throw new Error(typeof data?.detail === 'string' ? data.detail : `Chat failed (${res.status})`)
  }
  return res.json() as Promise<ChatReply>
}

export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const res = await fetch('/api/chat/history', { credentials: 'same-origin' })
  return res.ok ? ((await res.json()) as ChatMessage[]) : []
}

export async function clearChatHistory(): Promise<void> {
  await fetch('/api/chat/history', { method: 'DELETE', credentials: 'same-origin' })
}

// ---------------------------------------------------------------------------
// Accounts. The session lives in an HttpOnly cookie set by the backend, so
// this code never sees or stores the token itself.
// ---------------------------------------------------------------------------

export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
}

async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    throw new Error(typeof data?.detail === 'string' ? data.detail : `Request failed (${res.status})`)
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

export async function fetchCurrentUser(): Promise<User | null> {
  const res = await fetch('/api/auth/me', { credentials: 'same-origin' })
  return res.ok ? ((await res.json()) as User) : null
}

export function logIn(email: string, password: string): Promise<User> {
  return postJson<User>('/api/auth/login', { email, password })
}

export function createAccount(
  firstName: string,
  lastName: string,
  email: string,
  password: string,
): Promise<User> {
  return postJson<User>('/api/auth/signup', {
    first_name: firstName,
    last_name: lastName,
    email,
    password,
  })
}

export function logOut(): Promise<void> {
  return postJson<void>('/api/auth/logout')
}

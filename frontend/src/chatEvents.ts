// Lets any page open the chat panel (e.g. "Ask about this item" on a product
// page), optionally with a question, without knowing how the widget works.

const OPEN_CHAT = 'cc:open-chat'

export interface OpenChatOptions {
  prompt?: string // put this question in the box…
  send?: boolean // …and send it right away
}

export function openChat(options: OpenChatOptions = {}) {
  window.dispatchEvent(new CustomEvent<OpenChatOptions>(OPEN_CHAT, { detail: options }))
}

export function onOpenChat(handler: (options: OpenChatOptions) => void): () => void {
  const listener = (e: Event) => handler((e as CustomEvent<OpenChatOptions>).detail ?? {})
  window.addEventListener(OPEN_CHAT, listener)
  return () => window.removeEventListener(OPEN_CHAT, listener)
}

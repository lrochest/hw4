import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SIZES, fetchProducts, type Product } from '../api.ts'
import { COLLECTIONS, inCollection } from '../collections.ts'
import { CHAT_VIEW, useChatResults } from '../useChatResults.ts'
import { useReportPage } from '../usePageContext.ts'
import ProductCard from '../components/ProductCard.tsx'

const SORTS = {
  featured: { label: 'Featured', compare: null },
  'price-asc': { label: 'Price: low to high', compare: (a: Product, b: Product) => a.price - b.price || a.name.localeCompare(b.name) },
  'price-desc': { label: 'Price: high to low', compare: (a: Product, b: Product) => b.price - a.price || a.name.localeCompare(b.name) },
  name: { label: 'Name: A to Z', compare: (a: Product, b: Product) => a.name.localeCompare(b.name) },
} as const
type SortKey = keyof typeof SORTS

const CATEGORY_ORDER = ['T-shirts', 'Long sleeves', 'Crewnecks', 'Hoodies', 'Quarter-zips', 'Jackets', 'Other']

function matches(product: Product, query: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  const haystack = [product.name, product.garment_type, product.description, ...product.search_tags, ...product.colors]
    .join(' ')
    .toLowerCase()
  return q.split(/\s+/).every((word) => haystack.includes(word))
}

export default function Products() {
  const [products, setProducts] = useState<Product[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [params, setParams] = useSearchParams()
  const query = params.get('q') ?? ''
  const category = params.get('category') ?? ''
  const size = params.get('size') ?? ''
  const sortParam = params.get('sort') ?? 'featured'
  const sort: SortKey = sortParam in SORTS ? (sortParam as SortKey) : 'featured'
  const collection = COLLECTIONS.find((c) => c.slug === params.get('collection'))
  const { results: chatResults, clear: clearChatResults } = useChatResults()
  // /products?view=chat shows what the chat assistant found instead of the full catalogue.
  const chatView = params.get('view') === CHAT_VIEW && chatResults !== null

  // New chat results: start at the top so the shopper sees the heading.
  useEffect(() => {
    if (chatView) window.scrollTo(0, 0)
  }, [chatView, chatResults?.id])

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch(() => setError('We could not load products. Is the backend running?'))
  }, [])

  const categories = useMemo(() => {
    const present = new Set(products?.map((p) => p.category))
    return CATEGORY_ORDER.filter((c) => present.has(c))
  }, [products])

  const visible = useMemo(() => {
    const filtered = (products ?? []).filter(
      (p) =>
        (!category || p.category === category) &&
        (!collection || inCollection(p, collection.slug)) &&
        (!size || p.sizes_in_stock.includes(size)) &&
        matches(p, query),
    )
    const compare = SORTS[sort].compare
    return compare ? [...filtered].sort(compare) : filtered
  }, [products, category, collection, size, sort, query])

  // Tell the chat which cards are on screen, so "these" / "the first one" work.
  const onScreen = chatView && chatResults ? chatResults.products : visible
  const label = chatView && chatResults
    ? `Chat results: ${chatResults.heading}`
    : [
        collection && `Collection: ${collection.title}`,
        category && `Category: ${category}`,
        size && `In stock in ${size}`,
        query && `Search: ${query}`,
      ].filter(Boolean).join(', ') || 'All products'
  useReportPage({
    visibleProductIds: onScreen.slice(0, 60).map((p) => p.product_id),
    visibleTotal: chatView && chatResults ? chatResults.total : onScreen.length,
    label,
  })

  function showAll() {
    clearChatResults()
    setParams(new URLSearchParams(), { replace: true })
  }

  function update(key: 'q' | 'category' | 'collection' | 'size' | 'sort', value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  if (chatView && chatResults) {
    const shown = chatResults.products.length
    return (
      <div className="page container">
        <div className="chat-results-banner" role="status">
          <div>
            <p className="eyebrow">From your chat</p>
            <h1>{chatResults.heading}</h1>
            <p className="muted">
              {shown === chatResults.total
                ? `${shown} ${shown === 1 ? 'piece' : 'pieces'} matched your question.`
                : `Showing ${shown} of ${chatResults.total} matches.`}{' '}
              Click any card for photos, sizes and stock.
            </p>
          </div>
          <button className="btn btn-secondary" onClick={showAll}>
            Browse all products
          </button>
        </div>

        <div className="product-grid">
          {chatResults.products.map((p, i) => (
            <ProductCard key={p.product_id} product={p} index={i} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="page container">
      <div className="page-head">
        <h1>{collection ? collection.title : 'Products'}</h1>
        <p className="muted">
          {products ? `${visible.length} of ${products.length} pieces` : 'Loading the shop…'}
        </p>
      </div>

      <div className="filters">
        <div className="filter-row">
          <input
            type="search"
            className="search-input"
            placeholder="Search: bulldog, Saybrook, navy, hockey…"
            value={query}
            onChange={(e) => update('q', e.target.value)}
            aria-label="Search products"
          />
          <label className="select-label">
            Size in stock
            <select value={size} onChange={(e) => update('size', e.target.value)}>
              <option value="">Any size</option>
              {SIZES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label className="select-label">
            Sort
            <select value={sort} onChange={(e) => update('sort', e.target.value === 'featured' ? '' : e.target.value)}>
              {Object.entries(SORTS).map(([key, { label }]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="chips" role="group" aria-label="Filter by category">
          <button className={`chip ${!category ? 'is-active' : ''}`} onClick={() => update('category', '')}>
            All
          </button>
          {categories.map((c) => (
            <button
              key={c}
              className={`chip ${category === c ? 'is-active' : ''}`}
              onClick={() => update('category', category === c ? '' : c)}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {collection && (
        <p className="active-collection">
          Showing the <strong>{collection.title.toLowerCase()}</strong> collection.{' '}
          <button className="text-link link-button" onClick={() => update('collection', '')}>
            Show everything
          </button>
        </p>
      )}

      {error && <p className="notice notice-error">{error}</p>}

      {products && visible.length === 0 && (
        <p className="notice">Nothing matches that yet. Try a different word or clear the filters.</p>
      )}

      <div className="product-grid">
        {visible.map((p, i) => (
          <ProductCard key={p.product_id} product={p} index={i} />
        ))}
      </div>
    </div>
  )
}

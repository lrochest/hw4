import { useEffect, useState, type MouseEvent } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { fetchProduct, fetchProducts, formatPrice, type Product, type ProductDetail as Detail } from '../api.ts'
import { openChat } from '../chatEvents.ts'
import { COLLECTIONS, badgeFor, inCollection } from '../collections.ts'
import ProductCard from '../components/ProductCard.tsx'
import { swatchFor } from '../swatches.ts'
import { CHAT_VIEW } from '../useChatResults.ts'
import { useReportPage } from '../usePageContext.ts'

const LOW_STOCK = 3
const RELATED = 4

function stockLabel(quantity: number): string {
  if (quantity === 0) return 'Sold out'
  if (quantity <= LOW_STOCK) return `Only ${quantity} left`
  return `${quantity} in stock`
}

// Same collection first (another Saybrook piece, another family piece), then
// same category; in-stock items only.
function relatedTo(product: Detail, all: Product[]): Product[] {
  const collection = COLLECTIONS.find((c) => inCollection(product, c.slug))
  const others = all.filter((p) => p.product_id !== product.product_id && p.total_stock > 0)
  const sameCollection = collection ? others.filter((p) => inCollection(p, collection.slug)) : []
  const sameCategory = others.filter((p) => p.category === product.category && !sameCollection.includes(p))
  return [...sameCollection, ...sameCategory].slice(0, RELATED)
}

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const from = (useLocation().state as { from?: string } | null)?.from
  const backTo = from?.startsWith('/products') ? from : '/products'
  const backLabel = from?.includes(`view=${CHAT_VIEW}`) ? 'Chat results' : 'All products'
  // Tag each result with the id it belongs to, so navigating to another
  // product shows "Loading…" instead of the previous item.
  const [loaded, setLoaded] = useState<{ id: string; product?: Detail; error?: string } | null>(null)
  const [all, setAll] = useState<Product[]>([])
  const [picked, setPicked] = useState<{ id: string; size: string } | null>(null)
  const [zoom, setZoom] = useState<{ x: number; y: number } | null>(null)

  useEffect(() => {
    fetchProduct(productId)
      .then((product) => setLoaded({ id: productId, product }))
      .catch((e: Error) =>
        setLoaded({
          id: productId,
          error: e.message === 'Not found' ? "We couldn't find that product." : 'We could not load this product.',
        }),
      )
  }, [productId])

  useEffect(() => {
    fetchProducts()
      .then(setAll)
      .catch(() => setAll([]))
  }, [])

  const current = loaded?.id === productId ? loaded : null
  const product = current?.product
  const error = current?.error
  const size = picked?.id === productId ? picked.size : null

  // Tell the chat which product "this" is.
  useReportPage({ productId: product?.product_id ?? null, label: product?.name ?? null })

  if (error) {
    return (
      <div className="page container">
        <p className="notice notice-error">{error}</p>
        <Link to="/products" className="text-link">
          ← Back to products
        </Link>
      </div>
    )
  }

  if (!product) {
    return (
      <div className="page container">
        <div className="detail detail-skeleton" aria-busy="true">
          <div className="skeleton skeleton-image" />
          <div>
            <div className="skeleton skeleton-line" />
            <div className="skeleton skeleton-title" />
            <div className="skeleton skeleton-line short" />
          </div>
        </div>
      </div>
    )
  }

  const inStock = product.inventory.some((s) => s.quantity > 0)
  const chosen = product.inventory.find((s) => s.size === size)
  const badge = badgeFor(product)
  const related = relatedTo(product, all)

  function track(e: MouseEvent<HTMLDivElement>) {
    const box = e.currentTarget.getBoundingClientRect()
    setZoom({ x: ((e.clientX - box.left) / box.width) * 100, y: ((e.clientY - box.top) / box.height) * 100 })
  }

  return (
    <div className="page container">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to={backTo}>{backLabel}</Link>
        <span aria-hidden="true">/</span>
        <Link to={`/products?category=${encodeURIComponent(product.category)}`}>{product.category}</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{product.name}</span>
      </nav>

      <div className="detail">
        <div className="detail-gallery">
          <div
            className={`detail-image ${zoom ? 'is-zoomed' : ''}`}
            onMouseMove={track}
            onMouseLeave={() => setZoom(null)}
            style={zoom ? { ['--zx' as string]: `${zoom.x}%`, ['--zy' as string]: `${zoom.y}%` } : undefined}
          >
            <img src={product.image_url} alt={product.name} />
            {badge && <span className="card-badge detail-badge">{badge}</span>}
          </div>
          <p className="detail-zoom-hint muted small">Hover the photo to zoom in on the print.</p>
        </div>

        <div className="detail-info">
          <p className="varsity-label">{product.garment_type}</p>
          <h1 className="detail-title">{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>

          <p className="detail-desc">{product.description}</p>

          {product.colors.length > 0 && (
            <div className="detail-colors">
              <span className="detail-label">Colorway</span>
              <ul className="swatches">
                {product.colors.map((c, i) => (
                  <li key={c}>
                    <span className="swatch" style={{ background: swatchFor(c) }} aria-hidden="true" />
                    {c}
                    {i === 0 && <span className="muted small"> (fabric)</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="detail-sizes">
            <span className="detail-label">Pick your size</span>
            {product.inventory.length > 0 ? (
              <div className="size-grid" role="radiogroup" aria-label="Size">
                {product.inventory.map((s) => (
                  <button
                    key={s.size}
                    role="radio"
                    aria-checked={size === s.size}
                    className={`size ${s.quantity === 0 ? 'is-out' : ''} ${
                      s.quantity > 0 && s.quantity <= LOW_STOCK ? 'is-low' : ''
                    } ${size === s.size ? 'is-picked' : ''}`}
                    onClick={() => setPicked({ id: productId, size: s.size })}
                  >
                    <span className="size-name">{s.size}</span>
                    <span className="size-stock">{stockLabel(s.quantity)}</span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="muted">Size information isn't available for this item.</p>
            )}

            {chosen && (
              <p className={`size-answer ${chosen.quantity === 0 ? 'is-out' : ''}`} role="status">
                {chosen.quantity === 0 ? (
                  <>
                    <strong>{chosen.size} is sold out.</strong>{' '}
                    <button
                      className="link-button text-link"
                      onClick={() =>
                        openChat({ prompt: `This is sold out in ${chosen.size}. Anything similar in ${chosen.size}?`, send: true })
                      }
                    >
                      Find something similar in {chosen.size} →
                    </button>
                  </>
                ) : (
                  <>
                    <strong>{chosen.size} is in stock</strong> · {stockLabel(chosen.quantity).toLowerCase()}. Made to order and
                    shipped in about 5–8 business days.
                  </>
                )}
              </p>
            )}
          </div>

          {!inStock && <p className="notice">This piece is sold out in every size right now.</p>}

          <button className="btn btn-primary btn-block ask-item" onClick={() => openChat()}>
            <span aria-hidden="true">💬</span> Ask about this item
          </button>
          <p className="muted small ask-hint">Sizing, colors, or something similar in your size: the shop assistant checks live stock.</p>

          <ul className="detail-promises">
            <li>
              <strong>Officially licensed</strong> Yale merchandise
            </li>
            <li>
              <strong>Made to order</strong> at 57 Broadway, New Haven
            </li>
            <li>
              <strong>30-day returns</strong> on unworn pieces with tags
            </li>
          </ul>
        </div>
      </div>

      {related.length > 0 && (
        <section className="related">
          <div className="section-head">
            <div>
              <p className="varsity-label">Pairs well with</p>
              <h2>You might also like</h2>
            </div>
          </div>
          <div className="product-grid">
            {related.map((p, i) => (
              <ProductCard key={p.product_id} product={p} index={i} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

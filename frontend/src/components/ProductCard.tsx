import type { CSSProperties } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { SIZES, formatPrice, type Product } from '../api.ts'
import { badgeFor } from '../collections.ts'

function shorten(text: string, max = 90): string {
  if (text.length <= max) return text
  return text.slice(0, text.lastIndexOf(' ', max)).replace(/[,.;:]$/, '') + '…'
}

// Each card's photo sits at its own slight angle, like prints pinned to a
// board. Derived from the id so it's stable between renders.
function tiltFor(id: string): number {
  let h = 0
  for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) | 0
  return ((Math.abs(h) % 5) - 2) * 0.6 // -1.2° … 1.2°
}

export default function ProductCard({ product, index = 0 }: { product: Product; index?: number }) {
  // Remember where the card was clicked (e.g. chat results), so the product
  // page's back link returns there.
  const { pathname, search } = useLocation()
  // Older saved chat results may not have this field yet.
  const inStockSizes = product.sizes_in_stock ?? []
  const badge = badgeFor(product)
  const fewSizes = inStockSizes.length > 0 && inStockSizes.length <= 2

  return (
    <Link
      to={`/products/${product.product_id}`}
      state={{ from: pathname + search }}
      className="product-card reveal"
      style={{ '--tilt': `${tiltFor(product.product_id)}deg`, '--delay': `${(index % 4) * 70}ms` } as CSSProperties}
    >
      <div className="product-card-stage">
        <div className="product-card-print">
          <img src={product.image_url} alt={product.name} loading="lazy" />
        </div>
        {badge && <span className="card-badge">{badge}</span>}
        {inStockSizes.length === 0 ? (
          <span className="card-flag card-flag-out">Sold out</span>
        ) : fewSizes ? (
          <span className="card-flag">Few sizes left</span>
        ) : null}
        <span className="card-cta" aria-hidden="true">
          View details →
        </span>
      </div>
      <div className="product-card-body">
        <p className="product-card-cat">{product.category}</p>
        <h3 className="product-card-name">{product.name}</h3>
        <p className="product-card-desc">{shorten(product.description)}</p>
        <div className="product-card-foot">
          <p className="product-card-price">{formatPrice(product.price)}</p>
          {/* Sizes at a glance: sold-out sizes are greyed and struck through. */}
          <ul
            className="card-sizes"
            aria-label={inStockSizes.length ? `In stock: ${inStockSizes.join(', ')}` : 'Sold out in every size'}
          >
            {SIZES.map((size) => (
              <li key={size} className={inStockSizes.includes(size) ? '' : 'is-out'} aria-hidden="true">
                {size}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Link>
  )
}

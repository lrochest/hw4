import { useEffect, useState, type CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, type Product } from '../api.ts'
import { openChat } from '../chatEvents.ts'
import { COLLECTIONS } from '../collections.ts'
import ProductCard from '../components/ProductCard.tsx'
import { useReportPage } from '../usePageContext.ts'

const FEATURED_IDS = [
  '2025-yale-vs-harvard-t-shirt',
  'basic-hoodie-big-yale',
  'benjamin-franklin-1-4-zip',
  'district-vit-crewneck-vintage-bulldog',
]
// The three photos stacked in the hero, back to front.
const HERO_IDS = ['yale-mom-hoodie', 'boola-boola-t-shirt', 'district-vit-crewneck-vintage-bulldog']

const TICKER = [
  'Boola Boola',
  'Fourteen residential colleges',
  'Family weekend',
  'The Game',
  'Printed on Broadway',
  'XS to XXL',
  'Officially licensed',
]

// One pennant color per collection, in COLLECTIONS order.
const PENNANTS = ['#00356b', '#f04f36', '#1f5f4a', '#c9a227']

// Real questions the assistant answers from the live catalogue.
const TRY_ASKING = [
  'Do you have the Mom Hoodie in XXL?',
  'Something for a Saybrook first-year under $60',
  'The Dad Crewneck is sold out in L. Anything similar?',
]

export default function Home() {
  const [all, setAll] = useState<Product[]>([])

  useEffect(() => {
    fetchProducts()
      .then(setAll)
      .catch(() => setAll([]))
  }, [])

  const pick = (ids: string[]) =>
    ids.map((id) => all.find((p) => p.product_id === id)).filter((p): p is Product => !!p)
  const featured = pick(FEATURED_IDS)
  const heroPrints = pick(HERO_IDS)

  useReportPage({ visibleProductIds: featured.map((p) => p.product_id), label: 'Home: featured products' })

  return (
    <>
      <section className="hero">
        <div className="container hero-grid">
          <div className="hero-copy">
            <p className="varsity-label">Est. on Broadway · New Haven</p>
            <h1 className="hero-title">
              Blue that outlasts <em>the semester.</em>
            </h1>
            <p className="hero-lede">
              Officially licensed Yale apparel, printed a few blocks from Old Campus. Soft enough for
              finals week, sturdy enough for your tenth reunion.
            </p>
            <div className="hero-actions">
              <Link to="/products" className="btn btn-accent btn-lg">
                Shop the collection
              </Link>
              <button className="btn btn-ghost btn-lg" onClick={() => openChat()}>
                Ask the shop
              </button>
            </div>
            <ul className="hero-trust">
              <li>Officially licensed</li>
              <li>Made to order in 5–8 days</li>
              <li>30-day returns</li>
            </ul>
          </div>

          <div className="hero-art" aria-hidden="true">
            {heroPrints.map((p, i) => (
              <Link
                key={p.product_id}
                to={`/products/${p.product_id}`}
                className={`hero-print hero-print-${i}`}
                tabIndex={-1}
              >
                <img src={p.image_url} alt="" />
                <span className="hero-print-caption">{p.name}</span>
              </Link>
            ))}
            <svg className="hero-stamp" viewBox="0 0 200 200">
              <defs>
                <path id="stamp-circle" d="M100,100 m-76,0 a76,76 0 1,1 152,0 a76,76 0 1,1 -152,0" />
              </defs>
              <circle cx="100" cy="100" r="96" />
              <text>
                <textPath href="#stamp-circle">OFFICIALLY LICENSED ✦ YALE BULLDOG BLUE ✦ 57 BROADWAY ✦</textPath>
              </text>
              <text x="100" y="116" className="hero-stamp-center" textAnchor="middle">
                CC
              </text>
            </svg>
          </div>
        </div>
      </section>

      <div className="ticker" aria-hidden="true">
        <div className="ticker-track">
          {[...TICKER, ...TICKER].map((t, i) => (
            <span key={i}>
              {t} <span className="ticker-star">✦</span>
            </span>
          ))}
        </div>
      </div>

      <section className="section container">
        <div className="section-head reveal">
          <div>
            <p className="varsity-label">This season</p>
            <h2>Worn most around campus</h2>
          </div>
          <Link to="/products" className="text-link">
            See all 102 pieces →
          </Link>
        </div>
        <div className="product-grid">
          {featured.map((p, i) => (
            <ProductCard key={p.product_id} product={p} index={i} />
          ))}
        </div>
      </section>

      <section className="section section-cream">
        <div className="container">
          <div className="section-head reveal">
            <div>
              <p className="varsity-label">Collections</p>
              <h2>Fly your colors</h2>
            </div>
          </div>
          <div className="pennant-grid">
            {COLLECTIONS.map((c, i) => (
              <Link
                key={c.slug}
                to={`/products?collection=${c.slug}`}
                className="pennant-card reveal"
                style={{ '--pennant': PENNANTS[i % PENNANTS.length], '--delay': `${i * 80}ms` } as CSSProperties}
              >
                <span className="pennant" aria-hidden="true">
                  <span>{c.title.replace(/^Your /, '')}</span>
                </span>
                <span className="pennant-body">
                  <h3>{c.title}</h3>
                  <p>{c.blurb}</p>
                  <span className="text-link">Browse →</span>
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="section container ask-band reveal">
        <div className="ask-band-copy">
          <p className="varsity-label">The shop assistant</p>
          <h2>
            Ask it like you'd ask <em>us at the counter.</em>
          </h2>
          <p className="muted">
            It checks live stock and real prices for every answer, puts matching pieces on the page, and
            remembers your chat when you're logged in.
          </p>
        </div>
        <div className="ask-band-chips">
          {TRY_ASKING.map((q, i) => (
            <button
              key={q}
              className="ask-bubble"
              style={{ '--delay': `${i * 120}ms` } as CSSProperties}
              onClick={() => openChat({ prompt: q, send: true })}
            >
              “{q}”
            </button>
          ))}
        </div>
      </section>

      <section className="section container info-strip">
        {[
          ['Made for you', 'Most orders are printed within 5 to 8 business days, then sent on their way by UPS.', '✂'],
          ['Easy returns', 'Changed your mind? Send unworn pieces with tags back within 30 days of shipping.', '↺'],
          ['Every size, honestly', 'Cards show which sizes are left, and the assistant checks live stock before it answers.', '✓'],
        ].map(([title, text, icon], i) => (
          <div key={title} className="info-item reveal" style={{ '--delay': `${i * 80}ms` } as CSSProperties}>
            <span className="info-icon" aria-hidden="true">
              {icon}
            </span>
            <h3>{title}</h3>
            <p>{text}</p>
          </div>
        ))}
      </section>
    </>
  )
}

import { Link } from 'react-router-dom'
import { openChat } from '../chatEvents.ts'
import { Crest } from './NavBar.tsx'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container footer-cta">
        <p className="footer-cta-text">
          Not sure about a size? <em>Ask the shop.</em> We check live stock.
        </p>
        <button className="btn btn-accent" onClick={() => openChat()}>
          Open the chat
        </button>
      </div>

      <div className="container footer-grid">
        <div className="footer-brand">
          <Crest className="footer-crest" />
          <div>
            <p className="footer-title">Campus Customs</p>
            <p>
              Yale Bulldog Blue
              <br />
              57 Broadway, New Haven, CT 06511
            </p>
            <p className="licensed">Officially Licensed Yale Merchandise</p>
          </div>
        </div>
        <div>
          <p className="footer-title">Shop</p>
          <ul>
            <li><Link to="/products">All products</Link></li>
            <li><Link to="/products?category=Hoodies">Hoodies</Link></li>
            <li><Link to="/products?category=Crewnecks">Crewnecks</Link></li>
            <li><Link to="/products?collection=colleges">Residential colleges</Link></li>
            <li><Link to="/products?collection=family">For the family</Link></li>
          </ul>
        </div>
        <div>
          <p className="footer-title">Help</p>
          <ul>
            <li><Link to="/about#orders">Orders &amp; shipping</Link></li>
            <li><Link to="/about#returns">Returns</Link></li>
            <li><a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a></li>
            <li><a href="tel:+14753014205">(475) 301-4205</a></li>
          </ul>
        </div>
      </div>

      {/* Decorative: the old Yale fight song, set big and quiet behind the footer. */}
      <p className="footer-watermark" aria-hidden="true">Boola Boola</p>

      <div className="container footer-bottom">
        © {new Date().getFullYear()} Campus Customs. Yale marks used under license.
      </div>
    </footer>
  )
}

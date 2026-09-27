import { Link } from 'react-router-dom'

export default function About() {
  return (
    <div className="page container prose">
      <p className="varsity-label">About Us</p>
      <h1 className="about-title">
        We make the sweatshirt you'll still own <em>in twenty years.</em>
      </h1>

      <ul className="fact-row">
        <li className="reveal">
          <strong>57</strong>
          <span>Broadway, New Haven</span>
        </li>
        <li className="reveal" style={{ ['--delay' as string]: '80ms' }}>
          <strong>5–8</strong>
          <span>business days to print</span>
        </li>
        <li className="reveal" style={{ ['--delay' as string]: '160ms' }}>
          <strong>30</strong>
          <span>day returns</span>
        </li>
        <li className="reveal" style={{ ['--delay' as string]: '240ms' }}>
          <strong>XS–XXL</strong>
          <span>in every style</span>
        </li>
      </ul>

      <p className="lede">
        Campus Customs runs Yale Bulldog Blue, an officially licensed Yale apparel shop at
        57 Broadway in New Haven. We keep it simple: good blanks, clean prints, and the
        marks that mean something to you.
      </p>

      <blockquote className="pull-quote reveal">
        Good blanks, clean prints, and the marks that mean something to you.
      </blockquote>

      <h2>What we carry</h2>
      <p>
        Tees, crewnecks, hoodies, quarter-zips and jackets, in sizes XS through XXL. Some pieces
        say YALE across the chest. Others are quieter: a residential college crest, a small team
        mark, the name of your graduate school, or a word like Mom, Dad or Grandpa for the people
        who cheer from the stands.
      </p>

      <h2 id="orders">How orders work</h2>
      <p>
        Most orders are produced within 5 to 8 business days. After that they ship, mostly by UPS
        within the US, and we email you a tracking link when yours leaves the shop. We ship
        worldwide. International customers are responsible for any customs duties or import
        taxes. Weather, holidays and carriers can sometimes add a few days.
      </p>

      <h2 id="returns">Returns</h2>
      <p>
        You have 30 days from the shipping date to send items back, as long as they're unworn and
        still have their original tags. If we made a mistake, we cover return shipping. If you
        changed your mind, return shipping is on you, and we suggest an insured, trackable method.
        Refunds don't include the original shipping cost and can take 2 to 10 business days to
        show up, depending on your bank. Custom-made pieces, like our Custom Alumni items, are
        final sale.
      </p>

      <h2>Say hello</h2>
      <p>
        Email <a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a>, call{' '}
        <a href="tel:+14753014205">(475) 301-4205</a>, or open the chat in the bottom corner of
        any page.
      </p>

      <p>
        <Link to="/products" className="btn">Browse the shop</Link>
      </p>
    </div>
  )
}

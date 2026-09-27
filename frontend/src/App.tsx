import { Route, Routes } from 'react-router-dom'
import ChatWidget from './components/ChatWidget.tsx'
import Footer from './components/Footer.tsx'
import NavBar from './components/NavBar.tsx'
import ScrollToTop from './components/ScrollToTop.tsx'
import About from './pages/About.tsx'
import Account from './pages/Account.tsx'
import Home from './pages/Home.tsx'
import Login from './pages/Login.tsx'
import NotFound from './pages/NotFound.tsx'
import ProductDetail from './pages/ProductDetail.tsx'
import Products from './pages/Products.tsx'
import Signup from './pages/Signup.tsx'
import { useReveal } from './useReveal.ts'

export default function App() {
  useReveal()
  return (
    <div className="app">
      <ScrollToTop />
      <NavBar />
      <main className="main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/account" element={<Account />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
      <ChatWidget />
    </div>
  )
}

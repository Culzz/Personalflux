import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import Discover from "./pages/Discover";
import Home from "./pages/Home";
import Login from "./pages/Login";
import ProductPage from "./pages/ProductPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="topbar">
        <Link to="/" className="brand">
          PersonaFlux<small>ADAPTIVE SHOP</small>
        </Link>
        <div className="links">
          <Link to="/">For you</Link>
          <Link to="/discover">Discover</Link>
          <Link to="/login">Login</Link>
        </div>
      </div>
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/discover" element={<Discover />} />
          <Route path="/products/:id" element={<ProductPage />} />
          <Route path="/login" element={<Login />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

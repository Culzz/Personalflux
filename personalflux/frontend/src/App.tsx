import type { ReactNode } from "react";
import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { RequireAuth } from "./components/RequireAuth";
import { AuthProvider } from "./features/auth/AuthContext";
import { CartProvider } from "./features/cart/CartContext";
import { ConsentProvider } from "./features/consent/ConsentContext";
import { SavedProvider } from "./features/saved/SavedContext";
import { ToastProvider } from "./features/toast/ToastContext";
import { LoginPage, RegisterPage } from "./pages/AuthPages";
import AboutPage from "./pages/AboutPage";
import AdminPage from "./pages/AdminPage";
import BusinessPage from "./pages/BusinessPage";
import CartPage from "./pages/CartPage";
import DiscoverPage from "./pages/DiscoverPage";
import HistoryPage from "./pages/HistoryPage";
import HomePage from "./pages/HomePage";
import MLPage from "./pages/MLPage";
import NotFoundPage from "./pages/NotFoundPage";
import PreferencesPage from "./pages/PreferencesPage";
import ProductPage from "./pages/ProductPage";
import SavedPage from "./pages/SavedPage";
import SettingsPage from "./pages/SettingsPage";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      <ConsentProvider>
        <AuthProvider>
          <SavedProvider>
            <CartProvider>{children}</CartProvider>
          </SavedProvider>
        </AuthProvider>
      </ConsentProvider>
    </ToastProvider>
  );
}

export default function App() {
  return (
    <Providers>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="discover" element={<DiscoverPage />} />
          <Route path="products/:id" element={<ProductPage />} />
          <Route path="cart" element={<CartPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="business" element={<BusinessPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route element={<RequireAuth />}>
            <Route path="ml" element={<MLPage />} />
            <Route path="admin" element={<AdminPage />} />
            <Route path="saved" element={<SavedPage />} />
            <Route path="preferences" element={<PreferencesPage />} />
            <Route path="history" element={<HistoryPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Providers>
  );
}

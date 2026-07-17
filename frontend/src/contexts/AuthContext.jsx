import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../lib/api";

const STORAGE_KEY = "historial0km.session";
const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        setSession(JSON.parse(raw));
      } catch {
        // Sesión corrupta en localStorage: se arranca sin sesión en lugar de romper la app.
      }
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    const data = await api.login(email, password);
    const sess = {
      token: data.access_token,
      concesionariaId: data.concesionaria_id,
      nombre: data.nombre,
      walletAddress: data.wallet_address,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sess));
    setSession(sess);
    return sess;
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setSession(null);
  };

  return (
    <AuthCtx.Provider value={{ session, loading, login, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  return useContext(AuthCtx);
}

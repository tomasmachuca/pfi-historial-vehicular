import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UserX } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";

// Baja de la cuenta a pedido de la concesionaria (derecho de supresión, Ley 25.326).
// Los services ya sellados siguen en el historial de cada vehículo: son de sus dueños.
export default function BajaCuenta() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  const [abierto, setAbierto] = useState(false);
  const [password, setPassword] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");

  const confirmar = async (e) => {
    e.preventDefault();
    setEnviando(true);
    setError("");
    try {
      await api.bajaCuenta(session.token, password);
      logout();
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message);
      setEnviando(false);
    }
  };

  return (
    <div className="card p-5 mt-10">
      <h2 className="font-medium flex items-center gap-2">
        <UserX size={16} /> Baja de la cuenta
      </h2>
      <p className="text-sm text-slate-500 mt-1">
        Revoca la autorización de la concesionaria en el contrato y elimina sus credenciales y datos de
        contacto. Los services ya sellados se conservan en el historial de cada vehículo.
      </p>
      {!abierto ? (
        <button type="button" className="btn-secondary mt-4" onClick={() => setAbierto(true)}>
          Dar de baja la cuenta
        </button>
      ) : (
        <form onSubmit={confirmar} className="mt-4 max-w-sm space-y-3">
          <label className="label" htmlFor="baja-password">
            Confirmá con tu contraseña
          </label>
          <input
            id="baja-password"
            type="password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-2">
            <button type="submit" className="btn-primary" disabled={enviando || !password}>
              {enviando ? "Procesando..." : "Confirmar baja"}
            </button>
            <button type="button" className="btn-secondary" onClick={() => setAbierto(false)} disabled={enviando}>
              Cancelar
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

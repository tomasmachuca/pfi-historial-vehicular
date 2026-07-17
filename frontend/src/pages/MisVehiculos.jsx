import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Car, ExternalLink } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { fmtDate, txUrl } from "../lib/format";

export default function MisVehiculos() {
  const { session } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtro, setFiltro] = useState("");

  useEffect(() => {
    api.misVehiculos(session.token).then(setItems).finally(() => setLoading(false));
  }, [session.token]);

  const filtrados = items.filter((v) => {
    const t = filtro.toLowerCase();
    if (!t) return true;
    return (
      v.vin?.toLowerCase().includes(t) ||
      v.patente?.toLowerCase().includes(t) ||
      v.marca?.toLowerCase().includes(t) ||
      v.modelo?.toLowerCase().includes(t)
    );
  });

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Vehiculos registrados</h1>
          <p className="text-sm text-slate-500 mt-1">{items.length} vehiculos dados de alta por tu concesionaria</p>
        </div>
        <Link to="/vehiculos/nuevo" className="btn-primary">
          <Car size={16} /> Alta 0km
        </Link>
      </div>

      <input
        type="search"
        className="input mb-4 max-w-sm"
        placeholder="Filtrar por VIN, patente o modelo..."
        value={filtro}
        onChange={(e) => setFiltro(e.target.value)}
      />

      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-6 text-sm text-slate-500">Cargando...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
              <tr>
                <th className="text-left px-5 py-2.5 font-medium">VIN</th>
                <th className="text-left px-5 py-2.5 font-medium">Marca / Modelo</th>
                <th className="text-left px-5 py-2.5 font-medium">Año</th>
                <th className="text-left px-5 py-2.5 font-medium">Patente</th>
                <th className="text-left px-5 py-2.5 font-medium">Alta</th>
                <th className="text-left px-5 py-2.5 font-medium">Tx</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map((v) => (
                <tr key={v.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-5 py-3 font-mono text-xs">{v.vin}</td>
                  <td className="px-5 py-3">{v.marca} {v.modelo}</td>
                  <td className="px-5 py-3">{v.anio}</td>
                  <td className="px-5 py-3">{v.patente || <span className="text-slate-400">—</span>}</td>
                  <td className="px-5 py-3 text-slate-600">{fmtDate(v.creado_en)}</td>
                  <td className="px-5 py-3">
                    {v.tx_hash_alta ? (
                      <a
                        href={txUrl(v.tx_hash_alta)}
                        target="_blank"
                        rel="noreferrer"
                        className="text-brand-500 hover:text-brand-600 inline-flex items-center gap-1 text-xs"
                      >
                        ver <ExternalLink size={12} />
                      </a>
                    ) : (
                      <span className="text-slate-400 text-xs">pending</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

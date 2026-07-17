import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Car, Wrench, ArrowRight, Activity } from "lucide-react";
import StatCard from "../components/StatCard";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { fmtNumber, shorten, fmtDate } from "../lib/format";

export default function Dashboard() {
  const { session } = useAuth();
  const [vehiculos, setVehiculos] = useState([]);
  const [red, setRed] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.misVehiculos(session.token), api.estadoRed()])
      .then(([v, r]) => {
        setVehiculos(v);
        setRed(r);
      })
      .finally(() => setLoading(false));
  }, [session.token]);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
      <div className="flex items-end justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold">Hola, {session.nombre}</h1>
          <p className="text-sm text-slate-500 mt-1">
            Wallet autorizada: <span className="font-mono">{shorten(session.walletAddress, 10, 8)}</span>
          </p>
        </div>
        <div className="hidden sm:flex gap-2">
          <Link to="/vehiculos/nuevo" className="btn-secondary">
            <Car size={16} /> Alta 0km
          </Link>
          <Link to="/servicios/nuevo" className="btn-primary">
            <Wrench size={16} /> Cargar service
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        <StatCard
          icon={<Car size={18} />}
          label="Vehiculos dados de alta"
          value={fmtNumber(vehiculos.length)}
          loading={loading}
        />
        <StatCard
          icon={<Activity size={18} />}
          label="Bloque actual"
          value={red ? fmtNumber(red.block_number) : "-"}
          hint={red ? `Chain ID ${red.chain_id}` : ""}
          loading={loading}
        />
        <StatCard
          icon={<Wrench size={18} />}
          label="Contrato"
          value={red ? shorten(red.contract_address, 6, 6) : "-"}
          hint="HistorialCeroKM"
          loading={loading}
        />
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="font-medium">Ultimos vehiculos</h2>
          <Link to="/vehiculos" className="text-sm text-brand-500 hover:text-brand-600 inline-flex items-center gap-1">
            Ver todos <ArrowRight size={14} />
          </Link>
        </div>
        {loading ? (
          <div className="p-6 text-sm text-slate-500">Cargando...</div>
        ) : vehiculos.length === 0 ? (
          <div className="p-6 text-sm text-slate-500">
            Aun no diste de alta vehiculos. <Link to="/vehiculos/nuevo" className="text-brand-500">Crear el primero</Link>.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
              <tr>
                <th className="text-left px-5 py-2.5 font-medium">VIN</th>
                <th className="text-left px-5 py-2.5 font-medium">Marca / Modelo</th>
                <th className="text-left px-5 py-2.5 font-medium">Patente</th>
                <th className="text-left px-5 py-2.5 font-medium">Alta</th>
              </tr>
            </thead>
            <tbody>
              {vehiculos.slice(0, 8).map((v) => (
                <tr key={v.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-5 py-3 font-mono text-xs">{v.vin}</td>
                  <td className="px-5 py-3">{v.marca} {v.modelo} <span className="text-slate-500">({v.anio})</span></td>
                  <td className="px-5 py-3">{v.patente || <span className="text-slate-400">—</span>}</td>
                  <td className="px-5 py-3 text-slate-600">{fmtDate(v.creado_en)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Wrench, CheckCircle2 } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { txUrl, shorten } from "../lib/format";

const TIPOS = [
  { codigo: 1, nombre: "Service 10.000 km" },
  { codigo: 2, nombre: "Service 20.000 km" },
  { codigo: 3, nombre: "Service 30.000 km" },
  { codigo: 4, nombre: "Service 40.000 km" },
  { codigo: 5, nombre: "Service mayor" },
  { codigo: 6, nombre: "Reparacion garantia" },
  { codigo: 7, nombre: "Cambio de aceite" },
  { codigo: 8, nombre: "Cambio de cubiertas" },
  { codigo: 9, nombre: "Inspeccion tecnica" },
];

export default function RegistrarServicio() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    vin: "",
    tipo_servicio: 1,
    kilometraje: 0,
    descripcion: "",
  });
  const [archivo, setArchivo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [resultado, setResultado] = useState(null);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!archivo) {
      setError("Adjunta la orden de trabajo");
      return;
    }
    setError(null);
    setLoading(true);

    const fd = new FormData();
    Object.entries(form).forEach(([k, v]) => fd.append(k, v));
    fd.append("archivo", archivo);

    try {
      const res = await api.registrarServicio(session.token, fd);
      setResultado(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (resultado) {
    return (
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12">
        <div className="card p-8 text-center">
          <CheckCircle2 className="mx-auto text-emerald-500 mb-3" size={42} />
          <h2 className="text-xl font-semibold">Service registrado en cadena</h2>
          <p className="text-sm text-slate-600 mt-2">
            Bloque #{resultado.block_number}
          </p>
          {resultado.tx_hash && (
            <a
              href={txUrl(resultado.tx_hash)}
              target="_blank"
              rel="noreferrer"
              className="inline-block mt-4 text-brand-500 hover:text-brand-600 text-sm font-mono"
            >
              tx: {shorten(resultado.tx_hash, 10, 8)}
            </a>
          )}
          <div className="mt-6 flex justify-center gap-2">
            <button onClick={() => { setResultado(null); setArchivo(null); }} className="btn-secondary">
              Cargar otro
            </button>
            <button onClick={() => navigate("/dashboard")} className="btn-primary">
              Volver al dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
      <div className="flex items-center gap-2 mb-6">
        <Wrench className="text-brand-500" size={22} />
        <h1 className="text-2xl font-semibold">Registrar service oficial</h1>
      </div>

      <form onSubmit={onSubmit} className="card p-6 space-y-4">
        <div>
          <label className="label">VIN o patente del vehiculo</label>
          <input
            className="input font-mono"
            name="vin"
            value={form.vin}
            onChange={onChange}
            placeholder="Ej: VK12345678 o LSH900"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Tipo de service</label>
            <select className="input" name="tipo_servicio" value={form.tipo_servicio} onChange={onChange}>
              {TIPOS.map((t) => (
                <option key={t.codigo} value={t.codigo}>
                  {t.nombre}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Kilometraje</label>
            <input
              className="input"
              name="kilometraje"
              type="number"
              min="0"
              value={form.kilometraje}
              onChange={onChange}
              required
            />
          </div>
        </div>

        <div>
          <label className="label">Descripcion (opcional)</label>
          <textarea
            className="input"
            rows="3"
            name="descripcion"
            value={form.descripcion}
            onChange={onChange}
            placeholder="Detalles del trabajo realizado..."
          />
        </div>

        <div>
          <label className="label">Orden de trabajo (PDF / imagen)</label>
          <input
            type="file"
            accept=".pdf,image/*"
            onChange={(e) => setArchivo(e.target.files?.[0] || null)}
            className="block w-full text-sm text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border file:border-slate-300 file:bg-white file:text-slate-700 hover:file:bg-slate-50"
            required
          />
        </div>

        {error && (
          <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary">
            Cancelar
          </button>
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? "Firmando..." : "Sellar en blockchain"}
          </button>
        </div>
      </form>
    </div>
  );
}

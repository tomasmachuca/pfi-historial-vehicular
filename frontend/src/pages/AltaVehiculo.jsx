import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Car, CheckCircle2 } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { txUrl, shorten } from "../lib/format";

export default function AltaVehiculo() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    vin: "",
    patente: "",
    marca: "",
    modelo: "",
    anio: new Date().getFullYear(),
    color: "",
    km_inicial: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [resultado, setResultado] = useState(null);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const fd = new FormData();
    Object.entries(form).forEach(([k, v]) => fd.append(k, v));

    try {
      const res = await api.altaVehiculo(session.token, fd);
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
          <h2 className="text-xl font-semibold">Vehiculo registrado en cadena</h2>
          <p className="text-sm text-slate-600 mt-2">VIN {resultado.vin}</p>
          {resultado.tx_hash_alta && (
            <a
              href={txUrl(resultado.tx_hash_alta)}
              target="_blank"
              rel="noreferrer"
              className="inline-block mt-4 text-brand-500 hover:text-brand-600 text-sm font-mono"
            >
              tx: {shorten(resultado.tx_hash_alta, 10, 8)}
            </a>
          )}
          <div className="mt-6 flex justify-center gap-2">
            <button onClick={() => setResultado(null)} className="btn-secondary">
              Cargar otro
            </button>
            <button onClick={() => navigate("/vehiculos")} className="btn-primary">
              Ir a la lista
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
      <div className="flex items-center gap-2 mb-6">
        <Car className="text-brand-500" size={22} />
        <h1 className="text-2xl font-semibold">Alta 0km</h1>
      </div>

      <form onSubmit={onSubmit} className="card p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Field label="VIN" name="vin" value={form.vin} onChange={onChange} required />
          <Field label="Patente" name="patente" value={form.patente} onChange={onChange} required />
          <Field label="Marca" name="marca" value={form.marca} onChange={onChange} required />
          <Field label="Modelo" name="modelo" value={form.modelo} onChange={onChange} required />
          <Field label="Año" name="anio" type="number" value={form.anio} onChange={onChange} required />
          <Field label="Color" name="color" value={form.color} onChange={onChange} />
          <Field label="Km inicial" name="km_inicial" type="number" value={form.km_inicial} onChange={onChange} />
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
            {loading ? "Firmando..." : "Registrar en cadena"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({ label, name, value, onChange, type = "text", required }) {
  return (
    <div>
      <label className="label">{label}</label>
      <input
        className="input"
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        required={required}
      />
    </div>
  );
}

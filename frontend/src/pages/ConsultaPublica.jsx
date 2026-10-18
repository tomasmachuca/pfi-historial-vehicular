import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, ShieldCheck, ExternalLink, AlertTriangle, Share2, FileDown } from "lucide-react";
import { api } from "../lib/api";
import { fmtNumber, fmtDate, shorten, txUrl } from "../lib/format";
import KilometrajeChart from "../components/KilometrajeChart";
import ServiciosChart from "../components/ServiciosChart";
import EventoCard from "../components/EventoCard";
import ScoreCard from "../components/ScoreCard";

export default function ConsultaPublica() {
  const [params, setParams] = useSearchParams();
  const [identificador, setIdentificador] = useState(params.get("q") || "");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lento, setLento] = useState(false);
  const [error, setError] = useState(null);

  // Si la consulta tarda, casi siempre es el servidor arrancando: se avisa para
  // que el usuario no la dé por fallida.
  useEffect(() => {
    if (!loading) {
      setLento(false);
      return undefined;
    }
    const t = setTimeout(() => setLento(true), 4000);
    return () => clearTimeout(t);
  }, [loading]);

  const consultar = async (texto) => {
    const ident = texto.trim().toUpperCase();
    setError(null);
    setLoading(true);
    setData(null);
    try {
      const r = await api.consultaPublica(ident);
      setData(r);
      // El identificador queda en la URL para poder compartir el enlace del historial.
      setParams({ q: ident }, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const buscar = (e) => {
    e.preventDefault();
    consultar(identificador);
  };

  // Un enlace compartido (/consulta?q=PATENTE) abre directamente el historial.
  // Solo al montar: las búsquedas posteriores actualizan la URL, no la disparan.
  useEffect(() => {
    const q = params.get("q");
    if (q) consultar(q);
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
      <div className="text-center mb-8">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">Consultar historial</h1>
        <p className="text-slate-600 mt-3 max-w-lg mx-auto">
          Ingresa el VIN o la patente del vehiculo. La consulta es gratuita y no requiere cuenta.
        </p>
      </div>

      <form onSubmit={buscar} className="no-print flex flex-col sm:flex-row gap-2 max-w-xl mx-auto">
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
          />
          <input
            className="input font-mono pl-9 uppercase placeholder:normal-case placeholder:font-sans"
            placeholder="VIN o patente (ej. AB123CD)"
            value={identificador}
            onChange={(e) => setIdentificador(e.target.value)}
            required
          />
        </div>
        <button type="submit" disabled={loading || !identificador.trim()} className="btn-primary">
          <Search size={16} /> {loading ? "Buscando..." : "Buscar"}
        </button>
      </form>

      {error && (
        <div className="max-w-xl mx-auto mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5 text-center">
          {error}
        </div>
      )}

      {loading && (
        <div className="max-w-5xl mx-auto mt-10 space-y-4" aria-busy="true">
          {lento && (
            <p className="text-center text-sm text-slate-500">
              El servidor se está iniciando después de un rato sin uso. La primera consulta puede demorar hasta un
              minuto; las siguientes responden en el acto.
            </p>
          )}
          <div className="skeleton h-40 rounded-xl" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="skeleton h-56 rounded-xl" />
            <div className="skeleton h-56 rounded-xl" />
          </div>
        </div>
      )}

      {!loading && !data && !error && (
        <p className="text-center text-sm text-slate-400 mt-10">
          El historial se reconstruye leyendo los eventos sellados en Polygon.
        </p>
      )}

      {!loading && data && <Resultado data={data} />}
    </div>
  );
}

function Resultado({ data }) {
  const { vehiculo, eventos, cadena } = data;
  const anomalias = eventos.filter((e) => e.km_regresivo);
  const tieneAnomalias = anomalias.length > 0 || (vehiculo.anomalias_count ?? 0) > 0;
  const hayVerificados = eventos.some((e) => e.verificado);
  // El "último km" honesto es el mayor entre los eventos legítimos (no regresivos).
  const kmLegitimos = eventos.filter((e) => !e.km_regresivo).map((e) => e.kilometraje);
  const ultimoKm = kmLegitimos.length ? Math.max(...kmLegitimos) : 0;
  const ultimo = [...eventos].reverse().find((e) => !e.km_regresivo) || eventos[eventos.length - 1];

  return (
    <div className="mt-10 space-y-6 animate-fade-up">
      {tieneAnomalias && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 px-5 py-4 flex items-start gap-3">
          <AlertTriangle className="text-amber-500 shrink-0 mt-0.5" size={22} />
          <div className="text-sm text-amber-800">
            <p className="font-semibold">
              Historial con {anomalias.length === 1 ? "1 anomalía" : `${anomalias.length} anomalías`} de kilometraje
            </p>
            <p className="mt-1">
              Se intentó registrar {anomalias.length === 1 ? "un service" : "services"} con kilometraje menor al ya sellado en
              blockchain. El contrato no {anomalias.length === 1 ? "lo aceptó" : "los aceptó"} como válido y{" "}
              {anomalias.length === 1 ? "lo selló" : "los selló"} como anomalía, que no puede borrarse. Revisá la línea de
              tiempo antes de confiar en este vehículo.
            </p>
          </div>
        </div>
      )}

      <div className="card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              {hayVerificados ? (
                <span className="badge bg-emerald-50 text-emerald-700">
                  <ShieldCheck size={14} /> Verificado on-chain
                </span>
              ) : (
                <span className="badge bg-slate-100 text-slate-600">
                  <ShieldCheck size={14} /> Sin registro en el contrato actual
                </span>
              )}
              {tieneAnomalias && (
                <span className="badge bg-amber-500 text-white gap-1">
                  <AlertTriangle size={12} /> {anomalias.length} anomalía{anomalias.length === 1 ? "" : "s"}
                </span>
              )}
            </div>
            <h2 className="text-2xl font-semibold mt-2">
              {vehiculo.marca} {vehiculo.modelo} <span className="text-slate-500 font-normal">({vehiculo.anio})</span>
            </h2>
            <div className="mt-2 grid grid-cols-2 gap-x-8 gap-y-1 text-sm">
              <div><span className="text-slate-500">VIN:</span> <span className="font-mono">{vehiculo.vin}</span></div>
              <div><span className="text-slate-500">Patente:</span> {vehiculo.patente || "—"}</div>
              <div><span className="text-slate-500">Color:</span> {vehiculo.color || "—"}</div>
              <div><span className="text-slate-500">Alta:</span> {fmtDate(vehiculo.creado_en)}</div>
            </div>
          </div>
          <div className="text-right text-sm">
            <div className="text-slate-500 text-xs">Último kilometraje registrado</div>
            <div className="text-3xl font-semibold">{fmtNumber(ultimoKm)} <span className="text-base text-slate-500">km</span></div>
            <div className="text-xs text-slate-500 mt-1">{fmtDate(ultimo?.chain_timestamp)}</div>
          </div>
        </div>

        <div className="mt-5 pt-5 border-t border-slate-100 flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500">
          <span>Contrato: <span className="font-mono">{shorten(cadena.contrato, 10, 6)}</span></span>
          <span>Chain ID: {cadena.chain_id}</span>
          <span>Eventos en cadena: {cadena.cantidad_eventos_on_chain}</span>
          {cadena.tx_hash_alta && (
            <a href={txUrl(cadena.tx_hash_alta)} target="_blank" rel="noreferrer" className="text-brand-500 hover:text-brand-600 inline-flex items-center gap-1">
              tx alta <ExternalLink size={12} />
            </a>
          )}
        </div>
      </div>

      <Acciones vehiculo={vehiculo} />

      <ScoreCard score={data.score} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <KilometrajeChart eventos={eventos} />
        <ServiciosChart eventos={eventos} />
      </div>

      <div>
        <div className="flex items-baseline justify-between mb-3">
          <h3 className="font-medium text-slate-700">Línea de tiempo verificable</h3>
          <span className="text-xs text-slate-500">
            {eventos.length} {eventos.length === 1 ? "evento" : "eventos"}
          </span>
        </div>
        <div className="space-y-3">
          {eventos.map((e, i) => (
            <EventoCard key={i} evento={e} esAlta={e.tipo_servicio === 0} />
          ))}
        </div>
      </div>
    </div>
  );
}

// Compartir el enlace del historial por mensajería y descargarlo en PDF, como pidió
// el comprador entrevistado. El PDF se genera con la impresión del navegador.
function Acciones({ vehiculo }) {
  const [aviso, setAviso] = useState(null);
  const ident = vehiculo.patente || vehiculo.vin;
  const enlace = `${window.location.origin}/consulta?q=${encodeURIComponent(ident)}`;
  const texto = `Historial de ${vehiculo.marca} ${vehiculo.modelo} (${ident}) en Trazarg`;

  const compartir = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: "Trazarg", text: texto, url: enlace });
      } catch {
        // El usuario cerró el menú de compartir: no hay nada que informar.
      }
      return;
    }
    try {
      await navigator.clipboard.writeText(enlace);
      setAviso("Enlace copiado");
    } catch {
      setAviso(enlace);
    }
  };

  return (
    <div className="no-print flex flex-wrap items-center justify-end gap-2">
      {aviso && <span className="text-xs text-slate-500 mr-auto">{aviso}</span>}
      <a
        href={`https://wa.me/?text=${encodeURIComponent(`${texto}: ${enlace}`)}`}
        target="_blank"
        rel="noreferrer"
        className="btn-secondary"
      >
        <Share2 size={16} /> WhatsApp
      </a>
      <button type="button" onClick={compartir} className="btn-secondary">
        <Share2 size={16} /> Compartir enlace
      </button>
      <button type="button" onClick={() => window.print()} className="btn-secondary">
        <FileDown size={16} /> Descargar PDF
      </button>
    </div>
  );
}

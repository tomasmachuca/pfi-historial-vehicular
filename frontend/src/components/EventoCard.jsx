import { ExternalLink, FileCheck2, AlertTriangle } from "lucide-react";
import { txUrl, shorten, fmtNumber, fmtDate } from "../lib/format";

export default function EventoCard({ evento, esAlta }) {
  const anomalo = evento.km_regresivo;
  const fileteColor = anomalo ? "bg-amber-500" : esAlta ? "bg-emerald-500" : "bg-brand-300";

  return (
    <div className={`card card-hover p-5 relative overflow-hidden ${anomalo ? "ring-1 ring-amber-300 bg-amber-50/40" : ""}`}>
      {/* Filete lateral: alta 0km, service normal o anomalía */}
      <span
        className={`absolute inset-y-0 left-0 w-1 ${fileteColor}`}
        aria-hidden="true"
      />
      <div className="flex items-start justify-between gap-4 pl-2">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`badge ${esAlta ? "bg-emerald-50 text-emerald-700" : anomalo ? "bg-amber-100 text-amber-800" : "bg-brand-50 text-brand-700"}`}>
              {esAlta ? "Alta 0km" : evento.tipo_nombre}
            </span>
            {anomalo && (
              <span className="badge bg-amber-500 text-white gap-1">
                <AlertTriangle size={12} /> Kilometraje regresivo
              </span>
            )}
            <span className="text-xs text-slate-500">
              {anomalo ? "No sellado en cadena" : fmtDate(evento.chain_timestamp)}
            </span>
          </div>
          <div className="mt-1 text-2xl font-semibold">
            {fmtNumber(evento.kilometraje)} <span className="text-base font-normal text-slate-500">km</span>
          </div>
          {anomalo && evento.km_anterior != null && (
            <p className="text-sm text-amber-700 mt-1">
              {fmtNumber(evento.km_anterior - evento.kilometraje)} km por debajo del último kilometraje registrado ({fmtNumber(evento.km_anterior)} km).
            </p>
          )}
          {evento.descripcion && (
            <p className="text-sm text-slate-600 mt-2">{evento.descripcion}</p>
          )}
        </div>
        <div className="text-right text-xs text-slate-500 space-y-1 shrink-0">
          <div>Concesionaria</div>
          <div className={`font-medium ${anomalo ? "text-amber-800" : "text-slate-700"}`}>{evento.concesionaria_nombre}</div>
        </div>
      </div>

      <div className="mt-4 pt-4 pl-2 border-t border-slate-100 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-slate-500">
        <span className="flex items-center gap-1.5" title="Hash SHA-256 de la evidencia">
          <FileCheck2 size={14} />
          <span className="font-mono">{shorten(evento.hash_evidencia, 10, 6)}</span>
        </span>
        {evento.tx_hash ? (
          <a
            href={txUrl(evento.tx_hash)}
            target="_blank"
            rel="noreferrer"
            className="text-brand-500 hover:text-brand-600 inline-flex items-center gap-1"
          >
            Ver transaccion en Polygonscan <ExternalLink size={12} />
          </a>
        ) : anomalo ? (
          <span className="text-amber-700 inline-flex items-center gap-1">
            <AlertTriangle size={12} /> Sin sellado on-chain
          </span>
        ) : null}
        {!anomalo && !evento.verificado && (
          <span className="text-amber-700 inline-flex items-center gap-1" title="La transacción no aparece en el contrato actual (posible registro contra un deploy anterior)">
            <AlertTriangle size={12} /> No confirmado en el contrato actual
          </span>
        )}
        {evento.archivo_url && (
          <a
            href={evento.archivo_url}
            target="_blank"
            rel="noreferrer"
            className="text-slate-600 hover:text-slate-900 inline-flex items-center gap-1"
          >
            Evidencia <ExternalLink size={12} />
          </a>
        )}
      </div>
    </div>
  );
}

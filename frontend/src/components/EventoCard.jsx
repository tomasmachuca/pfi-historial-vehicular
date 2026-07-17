import { ExternalLink, FileCheck2 } from "lucide-react";
import { txUrl, shorten, fmtNumber, fmtDate } from "../lib/format";

export default function EventoCard({ evento, esAlta }) {
  return (
    <div className="card card-hover p-5 relative overflow-hidden">
      {/* Filete lateral: distingue el alta 0km del resto de los services */}
      <span
        className={`absolute inset-y-0 left-0 w-1 ${esAlta ? "bg-emerald-500" : "bg-brand-300"}`}
        aria-hidden="true"
      />
      <div className="flex items-start justify-between gap-4 pl-2">
        <div>
          <div className="flex items-center gap-2">
            <span className={`badge ${esAlta ? "bg-emerald-50 text-emerald-700" : "bg-brand-50 text-brand-700"}`}>
              {esAlta ? "Alta 0km" : evento.tipo_nombre}
            </span>
            <span className="text-xs text-slate-500">
              {fmtDate(evento.chain_timestamp)}
            </span>
          </div>
          <div className="mt-1 text-2xl font-semibold">
            {fmtNumber(evento.kilometraje)} <span className="text-base font-normal text-slate-500">km</span>
          </div>
          {evento.descripcion && (
            <p className="text-sm text-slate-600 mt-2">{evento.descripcion}</p>
          )}
        </div>
        <div className="text-right text-xs text-slate-500 space-y-1 shrink-0">
          <div>Concesionaria</div>
          <div className="font-medium text-slate-700">{evento.concesionaria_nombre}</div>
        </div>
      </div>

      <div className="mt-4 pt-4 pl-2 border-t border-slate-100 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-slate-500">
        <span className="flex items-center gap-1.5" title="Hash SHA-256 de la evidencia sellado en cadena">
          <FileCheck2 size={14} />
          <span className="font-mono">{shorten(evento.hash_evidencia, 10, 6)}</span>
        </span>
        {evento.tx_hash && (
          <a
            href={txUrl(evento.tx_hash)}
            target="_blank"
            rel="noreferrer"
            className="text-brand-500 hover:text-brand-600 inline-flex items-center gap-1"
          >
            Ver transaccion en Polygonscan <ExternalLink size={12} />
          </a>
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

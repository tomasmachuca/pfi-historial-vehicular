import { CheckCircle2, AlertTriangle, Info, Gauge } from "lucide-react";
import { estiloNivel } from "../utils";

const ICONO_RAZON = {
  positivo: <CheckCircle2 size={16} className="text-emerald-500 shrink-0 mt-0.5" />,
  negativo: <AlertTriangle size={16} className="text-amber-500 shrink-0 mt-0.5" />,
  neutro: <Info size={16} className="text-slate-400 shrink-0 mt-0.5" />,
};

/**
 * Puntaje de confiabilidad del historial: el número, su nivel en lenguaje llano,
 * las razones que lo explican y el desglose por insumo.
 */
export default function ScoreCard({ score }) {
  if (!score) return null;
  const estilo = estiloNivel(score.nivel);
  // Anillo: circunferencia de r=42 en un viewBox de 100.
  const circ = 2 * Math.PI * 42;

  return (
    <div className="card p-6">
      <div className="flex items-center gap-2 text-slate-700 font-medium mb-5">
        <Gauge size={18} className="text-brand-500" /> Puntaje de confiabilidad del historial
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[auto_1fr] gap-6 items-start">
        <div className="flex flex-col items-center">
          <div className="relative w-32 h-32">
            <svg viewBox="0 0 100 100" className="w-32 h-32 -rotate-90" aria-hidden="true">
              <circle cx="50" cy="50" r="42" fill="none" stroke="#e2e8f0" strokeWidth="9" />
              <circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                stroke={estilo.anillo}
                strokeWidth="9"
                strokeLinecap="round"
                strokeDasharray={`${(score.puntaje / 100) * circ} ${circ}`}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-4xl font-semibold">{score.puntaje}</span>
              <span className="text-xs text-slate-500">de 100</span>
            </div>
          </div>
          <span className={`badge mt-3 ${estilo.fondo} ${estilo.color}`}>{estilo.etiqueta}</span>
        </div>

        <div>
          <ul className="space-y-2">
            {score.razones.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                {ICONO_RAZON[r.tipo] ?? ICONO_RAZON.neutro}
                <span>{r.texto}</span>
              </li>
            ))}
          </ul>

          <div className="mt-5 pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
            {score.componentes.map((c) => (
              <div key={c.clave}>
                <div className="flex justify-between text-xs text-slate-500">
                  <span>{c.nombre}</span>
                  <span className="font-mono">
                    {Math.round(c.puntos)}/{c.maximo}
                  </span>
                </div>
                <div className="h-1.5 mt-1 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${estilo.barra}`}
                    style={{ width: `${(c.puntos / c.maximo) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

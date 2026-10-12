/**
 * Utilidades de presentación del historial.
 *
 * El puntaje de confiabilidad se calcula en el backend (app/services/scoring.py)
 * para que sea el mismo en cualquier cliente; aquí solo se decide cómo mostrarlo.
 */

const NIVELES = {
  alto: { etiqueta: "Confiabilidad alta", color: "text-emerald-700", fondo: "bg-emerald-50", barra: "bg-emerald-500", anillo: "#10b981" },
  medio: { etiqueta: "Confiabilidad media", color: "text-brand-700", fondo: "bg-brand-50", barra: "bg-brand-500", anillo: "#2f66ad" },
  bajo: { etiqueta: "Confiabilidad baja", color: "text-amber-800", fondo: "bg-amber-50", barra: "bg-amber-500", anillo: "#f59e0b" },
};

/**
 * Estilos y etiqueta de un nivel de confiabilidad ("alto", "medio" o "bajo").
 * Un nivel desconocido se muestra como bajo: ante la duda, no transmitir confianza.
 */
export function estiloNivel(nivel) {
  return NIVELES[nivel] ?? NIVELES.bajo;
}

/** Indica si un hash corresponde a un evento sellado sin comprobante adjunto. */
export function esHashCero(hash) {
  if (!hash) return true;
  return /^(0x)?0+$/.test(hash);
}

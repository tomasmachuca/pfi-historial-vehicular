/**
 * Calcula un puntaje de confiabilidad (0-100) a partir de la cantidad de
 * servicios registrados y la antiguedad del vehiculo en anios.
 * Esqueleto inicial de la logica de scoring del sistema.
 *
 * @param {number} cantidadServicios - Servicios de mantenimiento registrados.
 * @param {number} antiguedadAnios - Antiguedad del vehiculo en anios.
 * @returns {number} Puntaje entre 0 y 100.
 */
export function calcularScore(cantidadServicios, antiguedadAnios) {
  if (antiguedadAnios <= 0) {
    return 100;
  }
  const serviciosEsperados = antiguedadAnios;
  const ratio = cantidadServicios / serviciosEsperados;
  return Math.round(Math.min(1, ratio) * 100);
}

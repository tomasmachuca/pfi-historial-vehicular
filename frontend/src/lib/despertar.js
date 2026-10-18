// El backend corre en un plan que se suspende tras un rato sin pedidos y tarda
// cerca de un minuto en volver. Apenas se abre la aplicación, en cualquier ruta,
// se le manda un pedido liviano para que arranque mientras el usuario navega.
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function despertarServidor(url = API_URL) {
  if (typeof fetch !== "function") return Promise.resolve(false);
  return fetch(`${url}/health`, { cache: "no-store" }).then(
    (res) => res.ok,
    () => false
  );
}

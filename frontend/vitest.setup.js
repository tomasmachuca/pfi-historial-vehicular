// Entorno de pruebas de componentes: jsdom no implementa ResizeObserver, que usa
// el ResponsiveContainer de Recharts, ni matchMedia.
import { afterEach, beforeEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

class ResizeObserverFalso {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverFalso;

// La aplicación despierta al backend con un pedido a /health al montarse: en las
// pruebas ese pedido no debe salir a la red. Las pruebas que necesitan otro
// comportamiento reemplazan este doble por el suyo.
beforeEach(() => {
  globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.clearAllMocks();
});

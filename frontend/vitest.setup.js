// Entorno de pruebas de componentes: jsdom no implementa ResizeObserver, que usa
// el ResponsiveContainer de Recharts, ni matchMedia.
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

class ResizeObserverFalso {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverFalso;

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.clearAllMocks();
});

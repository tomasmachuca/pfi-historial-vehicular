import { describe, it, expect, vi } from "vitest";
import { despertarServidor } from "../lib/despertar";

describe("despertar el servidor", () => {
  it("pide /health sin caché y devuelve si respondió", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true });
    expect(await despertarServidor("https://api.test")).toBe(true);
    expect(fetch).toHaveBeenCalledWith("https://api.test/health", { cache: "no-store" });
  });

  it("no falla si el servidor no responde", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("sin red"));
    expect(await despertarServidor("https://api.test")).toBe(false);
  });

  it("no hace nada si el navegador no tiene fetch", async () => {
    const original = globalThis.fetch;
    delete globalThis.fetch;
    expect(await despertarServidor()).toBe(false);
    globalThis.fetch = original;
  });

  it("usa la URL configurada por defecto", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false });
    expect(await despertarServidor()).toBe(false);
    expect(fetch.mock.calls[0][0]).toMatch(/\/health$/);
  });
});

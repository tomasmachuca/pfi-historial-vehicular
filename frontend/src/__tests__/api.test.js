import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../lib/api";
import { txUrl, shorten, fmtNumber, fmtDate } from "../lib/format";

function respuesta(cuerpo, { status = 200, json = true } = {}) {
  return {
    ok: status < 400,
    status,
    json: json ? () => Promise.resolve(cuerpo) : () => Promise.reject(new Error("no es JSON")),
  };
}

beforeEach(() => {
  globalThis.fetch = vi.fn().mockResolvedValue(respuesta({ ok: true }));
});

describe("cliente de la API", () => {
  it("envía el login como JSON", async () => {
    await api.login("norte@example.com", "clave");
    const [url, opciones] = fetch.mock.calls[0];
    expect(url).toMatch(/\/auth\/login$/);
    expect(opciones.method).toBe("POST");
    expect(JSON.parse(opciones.body)).toEqual({ email: "norte@example.com", password: "clave" });
  });

  it("agrega el token en las rutas privadas", async () => {
    const fd = new FormData();
    await api.me("t");
    await api.misVehiculos("t");
    await api.altaVehiculo("t", fd);
    await api.registrarServicio("t", fd);
    await api.bajaCuenta("t", "clave");
    for (const [, opciones] of fetch.mock.calls) {
      expect(opciones.headers.Authorization).toBe("Bearer t");
    }
    const [urlBaja, baja] = fetch.mock.calls[4];
    expect(urlBaja).toMatch(/\/auth\/cuenta$/);
    expect(baja.method).toBe("DELETE");
  });

  it("consulta las rutas públicas sin token", async () => {
    await api.consultaPublica("AB 123");
    await api.stats();
    await api.estadoRed();
    expect(fetch.mock.calls[0][0]).toMatch(/\/publico\/vehiculo\/AB%20123$/);
    expect(fetch.mock.calls[1][0]).toMatch(/\/publico\/stats$/);
    expect(fetch.mock.calls[2][0]).toMatch(/\/publico\/red$/);
  });

  it("propaga el detalle del error del backend", async () => {
    fetch.mockResolvedValue(respuesta({ detail: "Credenciales invalidas" }, { status: 401 }));
    await expect(api.login("a@b.c", "x")).rejects.toThrow("Credenciales invalidas");
    fetch.mockResolvedValue(respuesta({ error: "otro formato" }, { status: 400 }));
    await expect(api.stats()).rejects.toThrow('{"error":"otro formato"}');
  });

  it("usa un mensaje por defecto si el error no es JSON", async () => {
    fetch.mockResolvedValue(respuesta(null, { status: 502, json: false }));
    await expect(api.stats()).rejects.toThrow("Error de servidor");
  });

  it("devuelve null en una respuesta sin contenido", async () => {
    fetch.mockResolvedValue(respuesta(null, { status: 204 }));
    expect(await api.stats()).toBeNull();
  });
});

describe("formato", () => {
  it("arma enlaces y abrevia direcciones", () => {
    expect(txUrl(null)).toBeNull();
    expect(txUrl("0xabc")).toMatch(/\/tx\/0xabc$/);
    expect(shorten("")).toBe("");
    expect(shorten("0x1234")).toBe("0x1234");
    expect(shorten("0x1234567890abcdef")).toBe("0x1234...cdef");
  });

  it("formatea números y fechas, con guion si faltan", () => {
    expect(fmtNumber(null)).toBe("-");
    expect(fmtNumber(12160)).toBe("12.160");
    expect(fmtDate(null)).toBe("-");
    expect(fmtDate("2026-06-10T10:00:00Z")).toMatch(/2026/);
  });
});

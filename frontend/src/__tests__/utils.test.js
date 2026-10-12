import { describe, it, expect } from "vitest";
import { estiloNivel, esHashCero } from "../utils.js";

describe("estiloNivel", () => {
  it("usa verde para el nivel alto", () => {
    expect(estiloNivel("alto").barra).toBe("bg-emerald-500");
  });

  it("usa ámbar para el nivel bajo", () => {
    expect(estiloNivel("bajo").barra).toBe("bg-amber-500");
  });

  it("trata un nivel desconocido como bajo", () => {
    expect(estiloNivel("otro")).toEqual(estiloNivel("bajo"));
  });
});

describe("esHashCero", () => {
  it("reconoce el hash cero con y sin prefijo", () => {
    expect(esHashCero("0".repeat(64))).toBe(true);
    expect(esHashCero("0x" + "0".repeat(64))).toBe(true);
  });

  it("considera sin comprobante a un hash ausente", () => {
    expect(esHashCero(null)).toBe(true);
  });

  it("no confunde un hash real con el hash cero", () => {
    expect(esHashCero("ab" + "0".repeat(62))).toBe(false);
  });
});
